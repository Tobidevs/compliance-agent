"""
Budget Adherence Rate evaluation for the compliance pipeline's evidence subagent.

This eval is scoped to the EVIDENCE-GATHERING stage only. For each case it:
  1. Fetches the repo root file listing and retrieves the controls for one SOC 2
     category from the vector DB (grouped by the specified category).
  2. Emits one experiment row per category, mirroring the real workflow's dispatch
     of one evidence subagent per category.
  3. Runs exactly one evidence subagent for that category's control set (invoking the
     compiled evidence_subagent subgraph directly so execution STOPS at evidence
     gathering and never proceeds to compliance validation).
  4. Grades the subagent's full message transcript with a single LLM-judge choice
     scorer (`BudgetAdherence`) that emits one of 0.0 / 0.3 / 0.5 / 0.7 / 1.0.

The budgets/protocol rules graded here are exactly those enforced by
EVIDENCE_SUBAGENT_SYSTEM_PROMPT in agent/prompts.py.

Run from the `backend/` directory:

    braintrust eval evals/budget_adherence_eval.py
"""

import asyncio

from braintrust import Eval, EvalCase
from autoevals import LLMClassifier
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
        "repo_owner": "acmuta",
        "repo_name": "mavresume",
        "framework": "SOC2&GDPR",
        "source_code_categories": [
            "Identity & Access Management",
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
    result is preserved so the judge can count calls and check protocol ordering.
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


# ---------------------------------------------------------------------------
# Scorer: cohesive Budget Adherence LLM judge with choice scores
# ---------------------------------------------------------------------------
CHOICE_SCORES = {
    "fully_adherent": 1.0,
    "minor_waste": 0.7,
    "moderate_waste": 0.5,
    "major_violation": 0.3,
    "severe_violation": 0.0,
}

BUDGET_ADHERENCE_PROMPT = """
You are a strict auditor of TOOL-CALL BUDGET DISCIPLINE for one evidence-extraction
subagent inside a SOC 2 compliance pipeline. You judge ONLY how well the agent stayed
within its tool budgets and followed its operating protocol. You do NOT judge whether
the gathered evidence is correct, complete, or compliant.

The transcript below is the agent's COMPLETE message list, turn by turn. It begins with
the system prompt (the rules) and the human message (the assigned controls and the repo
root file listing), followed by the agent's turns. Each agent turn may contain a
`think(...)` call and one or more search calls. Tool calls appear as
`-> tool_call: name({args})` and tool results appear as `TOOL_RESULT <name>`.

## Constraints the agent must obey (per this single subagent)

HARD LIMITS (breaching any of these is a severe violation):
- At most 5 `get_repository_tree` calls total, across all controls.
- At most 8 `get_file_content` calls total, across all controls.
- NEVER call `get_repository_tree` on the repository root: a path argument of "", "/",
  ".", or a path_filter that targets the root listing is forbidden. The root listing is
  already provided in the human message.
- Per control: at most 2 `get_repository_tree` calls and at most 3 `get_file_content` calls.
- Exactly one `conclude_evidence` call per assigned control (no control skipped, none
  concluded twice).
- Exactly one `finished_gathering_evidence` call, and only after every control has been
  concluded.

PROTOCOL (slips here are minor-to-moderate, not hard breaches):
- After the first turn, every search turn must include a `think(...)` call together with
  1-3 search tools in the SAME turn. `think()` is required every turn after the first.
- No more than 3 tool calls in a single turn.
- Controls are processed one at a time, in order. The agent should not interleave
  searches for multiple controls.

EFFICIENCY (waste, even when within limits):
- No duplicate or redundant fetches (re-fetching the same path, re-listing the same tree).
- Stop early when fetched files are clearly irrelevant; do not keep searching to prove
  absence after the per-control budget is reached.
- Do not exhaust the global budget on a single control.

## Rubric — choose exactly ONE label

- `fully_adherent` (1.0): All hard limits respected, full protocol compliance (think()
  every turn after the first, 1-3 tools/turn, one conclude per control, one finished
  call), and no wasted or redundant calls.
- `minor_waste` (0.7): Within ALL hard limits, but with at most one minor protocol slip
  OR one small redundant/unnecessary call. Essentially disciplined.
- `moderate_waste` (0.5): No hard limit breached, but the run is clearly wasteful or has
  multiple protocol slips (e.g., several missing think() turns, repeated redundant fetches,
  interleaving controls).
- `major_violation` (0.3): A per-control sub-cap was exceeded (>2 tree or >3 file on one
  control), OR there are repeated/serious protocol violations, OR the agent came right up
  against the global budget through wasteful behavior.
- `severe_violation` (0.0): Any HARD LIMIT was breached — global tree budget (>5) or file
  budget (>8) exceeded, `get_repository_tree` called on the root, a control left without
  exactly one `conclude_evidence`, or `finished_gathering_evidence` missing/duplicated/
  called before all controls concluded.

Count the calls carefully before deciding. When multiple labels could apply, pick the
WORST (lowest-scoring) one that is justified by the transcript.

## Transcript to evaluate

{{output}}
""".strip()

budget_adherence = LLMClassifier(
    name="BudgetAdherence",
    prompt_template=BUDGET_ADHERENCE_PROMPT,
    choice_scores=CHOICE_SCORES,
    model="gpt-4o",
    use_cot=True,
)


# ---------------------------------------------------------------------------
# Eval declaration
# ---------------------------------------------------------------------------
Eval(
    "Compliance Agent",
    data=build_dataset,
    task=task,
    scores=[budget_adherence],
    # Each evidence subagent makes many haiku calls over large transcripts. Run cases
    # serially to stay under the org's per-minute token rate limit; raise if your tier allows.
    max_concurrency=1,
)
