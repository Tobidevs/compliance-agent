"""
Shared dataset + task infrastructure for the evidence-subagent evals.

This module is framework-agnostic across judges: it builds the eval cases (one per
SOC 2/GDPR category, mirroring the real workflow's per-category subagent dispatch), runs
exactly one evidence subagent per case (invoking the compiled `evidence_subagent` subgraph
directly so execution STOPS at evidence gathering), and serializes the full message
transcript. Both the Budget Adherence and Evidence Precision judges grade that same
transcript, so the subagent runs once per case and is scored twice.

The retrieval, control shape, system message, and MCP scope here are deliberately the ones
`agent/nodes.py` uses in production rather than lookalikes: an eval that measures a
differently-configured system measures nothing. Control construction goes through
production's own `group_controls_into_clusters`, so a field cannot silently drop out of the
eval's prompt the way `points_of_focus` once did.
"""

import asyncio
from functools import cache

from braintrust import EvalCase
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from agent.budget import FETCHES_PER_CONTROL, TREES_PER_CONTROL, BudgetLedger
from agent.clusters import group_controls_into_clusters
from agent.prompts import EVIDENCE_SUBAGENT_SYSTEM_PROMPT, cacheable_system_message
from agent.subagent_nodes import EVIDENCE_MODEL_ID
from agent.subagents import evidence_subagent
from agent.utils.agent_utils import _build_evidence_user_message
from agent.utils.regulation_rag_service import RegulationRAGService, REGULATION_NAMESPACE
from agent.utils.github_mcp import DirListing, get_github_mcp_manager

load_dotenv()

# Per-subagent budgets, enforced at the tool boundary by agent/budget.py (not by the
# prompt). These are PER CONTROL; a cluster's total is the cap times its control count.
TREE_BUDGET = TREES_PER_CONTROL  # get_repository_tree calls per control
FILE_BUDGET = FETCHES_PER_CONTROL  # get_file_content calls per control

# Hardcoded eval cases. Each repo declares the SOC 2 categories (control families) to
# scan, mirroring `source_code_categories` in the real workflow. Every category is
# expanded into one experiment row (= one evidence subagent). Extend to broaden coverage.
EVAL_REPOS = [
    {
        "repo_owner": "ixartz",
        "repo_name": "SaaS-Boilerplate",
        "framework": "SOC2&GDPR",
        "source_code_categories": [
            "Logical and Physical Access Controls",
        ],
    },
]


@cache
def get_regulation_service() -> RegulationRAGService:
    """Lazy: at module scope this read Pinecone credentials just to import the module."""
    return RegulationRAGService(index="compliance-frameworks")


# ---------------------------------------------------------------------------
# Dataset generation: exhaustive per-category retrieval -> one EvalCase per cluster
# ---------------------------------------------------------------------------
async def _clusters_for_repo(categories: list[str]) -> dict[str, list[dict]]:
    """Retrieve and group controls exactly as `artifact_extractor_node` does.

    Production selects controls by exhaustive metadata filter, not by free-text top_k, so
    the eval saw a reranked subset of each category — a different, smaller cluster than the
    one the agent actually gets.
    """
    regulations = await asyncio.to_thread(
        get_regulation_service().get_controls_for_categories,
        categories=categories,
        namespace=REGULATION_NAMESPACE,
    )
    return group_controls_into_clusters([reg.fields for reg in regulations])


async def build_dataset():
    """Async generator yielding one EvalCase per cluster (= one evidence subagent).

    For each repo we fetch the root artifact listing once, then retrieve every control in
    the requested categories and route each category's whole set to a single evidence
    subagent — exactly how the real workflow dispatches one subagent per cluster.

    Implemented as an async generator (not a coroutine returning a list) because the
    Braintrust CLI imports and runs the eval inside its own event loop and consumes
    `data` via `inspect.isasyncgen`.
    """
    for repo in EVAL_REPOS:
        framework = repo["framework"]
        # Root file listing — fetched once per repo, shared across that repo's categories.
        root_listing = await get_github_mcp_manager().fetch_path(
            owner=repo["repo_owner"], repo=repo["repo_name"], path=""
        )
        artifact_paths = (
            root_listing.entries
            if isinstance(root_listing, DirListing)
            else [root_listing.path]
        )

        clusters = await _clusters_for_repo(repo["source_code_categories"])
        for cluster_id, controls in clusters.items():
            if not controls:
                continue

            yield EvalCase(
                input={
                    "repo_owner": repo["repo_owner"],
                    "repo_name": repo["repo_name"],
                    "framework": framework,
                    "category": cluster_id,
                    "controls": controls,
                    "artifact_paths": artifact_paths,
                },
                metadata={
                    "category": cluster_id,
                    "num_controls": len(controls),
                    "framework": framework,
                    "repo": f"{repo['repo_owner']}/{repo['repo_name']}",
                    "tree_budget_per_control": TREE_BUDGET,
                    "file_budget_per_control": FILE_BUDGET,
                    "tree_budget_total": TREE_BUDGET * len(controls),
                    "file_budget_total": FILE_BUDGET * len(controls),
                },
            )


# ---------------------------------------------------------------------------
# Task: run ONE evidence subagent for the category, then stop
# ---------------------------------------------------------------------------
def _serialize_tool_calls(tool_calls) -> str:
    lines = []
    for call in tool_calls or []:
        name = call.get("name", "<unknown>")
        args = call.get("args", {})
        lines.append(f"    -> tool_call: {name}({args})")
    return "\n".join(lines)


def serialize_transcript(messages) -> str:
    """Render the full LangChain message list into an auditable, ordered transcript.

    Every get_repository_tree / get_file_content call (with its path argument),
    every think()/conclude_evidence/finished_gathering_evidence call, and every tool
    result is preserved so each judge can count calls, check protocol ordering, and
    inspect which files were fetched and what they contained.
    """
    blocks = []
    for index, message in enumerate(messages):
        role = getattr(message, "type", "unknown")
        content = getattr(message, "content", "")
        header = f"[turn {index}] {role.upper()}"

        body_parts = []
        if content:
            body_parts.append(str(content).strip())

        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            body_parts.append(_serialize_tool_calls(tool_calls))

        if role == "tool":
            tool_name = getattr(message, "name", "<unknown>")
            header = f"[turn {index}] TOOL_RESULT <{tool_name}>"

        body = "\n".join(p for p in body_parts if p)
        blocks.append(f"{header}\n{body}".rstrip())

    return "\n\n".join(blocks)


async def task(input) -> str:
    sub_input = {
        # The subagent's SubAgentInput / _build_evidence_user_message expect a
        # `cluster_id` field; in the real workflow it holds the category string, so we
        # pass the category here to mirror that exactly.
        "cluster_id": input["category"],
        "controls": input["controls"],
        "artifact_paths": input["artifact_paths"],
        "repo_owner": input["repo_owner"],
        "repo_name": input["repo_name"],
    }
    # Same ledger production dispatch builds, so the eval measures the enforced system.
    sub_input["budget"] = BudgetLedger.for_controls(sub_input["controls"])
    sub_input["messages"] = [
        # Cache breakpoint included: production sends this, and it changes the request shape.
        cacheable_system_message(EVIDENCE_SUBAGENT_SYSTEM_PROMPT, EVIDENCE_MODEL_ID),
        HumanMessage(content=_build_evidence_user_message(sub_input)),
    ]

    # Invoking the compiled subgraph directly stops execution at evidence gathering;
    # the full compliance_agent graph would otherwise continue into validation.
    # cluster_scope mirrors invoke_evidence_subagent: without it there is no file cache, so
    # the eval would grade an agent that pays budget for repeat fetches production serves free.
    async with get_github_mcp_manager().cluster_scope():
        result = await evidence_subagent.ainvoke(
            sub_input, config={"recursion_limit": sub_input["budget"].recursion_limit()}
        )
    return serialize_transcript(result["messages"])
