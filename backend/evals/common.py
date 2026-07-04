"""
Shared dataset + task infrastructure for the evidence-subagent evals.

This module is framework-agnostic across judges: it builds the eval cases (one per
SOC 2/GDPR category, mirroring the real workflow's per-category subagent dispatch), runs
exactly one evidence subagent per case (invoking the compiled `evidence_subagent` subgraph
directly so execution STOPS at evidence gathering), and serializes the full message
transcript. Both the Budget Adherence and Evidence Precision judges grade that same
transcript, so the subagent runs once per case and is scored twice.
"""

import asyncio

from braintrust import EvalCase
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import EVIDENCE_SUBAGENT_SYSTEM_PROMPT
from agent.subagents import evidence_subagent
from agent.utils.agent_utils import _build_evidence_user_message
from agent.utils.regulation_rag_service import RegulationRAGService, REGULATION_NAMESPACE
from agent.utils.github_mcp import GitHubMCPManager

load_dotenv()

# Per-subagent budgets enforced by EVIDENCE_SUBAGENT_SYSTEM_PROMPT.
TREE_BUDGET = 5  # get_repository_tree calls across all controls
FILE_BUDGET = 8  # get_file_content calls across all controls

# How many controls to retrieve per category from the vector DB (the actual workflow's
# artifact_extractor_node uses top_k=10 with rerank_top_k=4).
CONTROL_TOP_K = 10
CONTROL_RERANK_TOP_K = 4

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

regulation_service = RegulationRAGService(index="compliance-frameworks")
github_mcp_manager = GitHubMCPManager()


# ---------------------------------------------------------------------------
# Dataset generation: per-category control retrieval -> one EvalCase per category
# ---------------------------------------------------------------------------
def _controls_from_regulations(regulations) -> list[dict]:
    """Map retrieved regulation records to the control shape the subagent consumes."""
    return [
        {
            "regulation_id": reg.fields["control_id"],
            "title": reg.fields["title"],
            "requirement": reg.fields["criterion_text"],
        }
        for reg in regulations
    ]


async def _retrieve_controls_for_category(framework, category):
    """Pull the n controls for one category from the vector DB (specified-category
    grouping — the queried category defines the group, matching the real workflow)."""
    regulations = await asyncio.to_thread(
        regulation_service.query_regulations,
        query=f"Retrieve {framework} control requirements for category {category}. ",
        top_k=CONTROL_TOP_K,
        rerank_top_k=CONTROL_RERANK_TOP_K,
        namespace=REGULATION_NAMESPACE,
        category=category,
    )
    return _controls_from_regulations(regulations)


async def build_dataset():
    """Async generator yielding one EvalCase per category (= one evidence subagent).

    For each repo we fetch the root artifact listing once, then retrieve each
    category's controls and route that whole set to a single evidence subagent —
    exactly how the real workflow dispatches one subagent per category.

    Implemented as an async generator (not a coroutine returning a list) because the
    Braintrust CLI imports and runs the eval inside its own event loop and consumes
    `data` via `inspect.isasyncgen`.
    """
    for repo in EVAL_REPOS:
        framework = repo["framework"]
        # Root file listing — fetched once per repo, shared across that repo's categories.
        artifact_paths = await github_mcp_manager.get_file_content(
            owner=repo["repo_owner"], repo=repo["repo_name"], path=""
        )

        for category in repo["source_code_categories"]:
            controls = await _retrieve_controls_for_category(framework, category)
            if not controls:
                continue

            yield EvalCase(
                input={
                    "repo_owner": repo["repo_owner"],
                    "repo_name": repo["repo_name"],
                    "framework": framework,
                    "category": category,
                    "controls": controls,
                    "artifact_paths": artifact_paths,
                },
                metadata={
                    "category": category,
                    "num_controls": len(controls),
                    "framework": framework,
                    "repo": f"{repo['repo_owner']}/{repo['repo_name']}",
                    "tree_budget": TREE_BUDGET,
                    "file_budget": FILE_BUDGET,
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
    sub_input["messages"] = [
        SystemMessage(content=EVIDENCE_SUBAGENT_SYSTEM_PROMPT),
        HumanMessage(content=_build_evidence_user_message(sub_input)),
    ]

    # Invoking the compiled subgraph directly stops execution at evidence gathering;
    # the full compliance_agent graph would otherwise continue into validation.
    result = await evidence_subagent.ainvoke(sub_input)
    return serialize_transcript(result["messages"])
