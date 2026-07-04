"""
Shared dataset + task infrastructure for the evidence-subagent evals (Langfuse port).

This is the Langfuse-runner counterpart of `evals/common.py` (Braintrust). It is
framework-agnostic across judges: it builds the eval cases (one per SOC 2/GDPR category,
mirroring the real workflow's per-category subagent dispatch), runs exactly one evidence
subagent per case (invoking the compiled `evidence_subagent` subgraph directly so execution
STOPS at evidence gathering), and serializes the full message transcript. Both the Budget
Adherence and Evidence Precision judges grade that same transcript, so the subagent runs
once per case and is scored twice.

Differences from the Braintrust version:
  - Dataset items are plain dicts ({"input": ..., "metadata": ...}) consumed by Langfuse's
    `run_experiment`, not `braintrust.EvalCase`s. `build_dataset` returns a concrete list
    (run_experiment expects materialized local data, not an async generator).
  - `task(*, item, **kwargs)` matches the Langfuse experiment-runner task signature and
    attaches a Langfuse `CallbackHandler` so every nested subagent LLM call is traced under
    the experiment's per-item trace.
  - `llm_classify` is a local reimplementation of `autoevals.LLMClassifier`: it renders the
    judge prompt, calls gpt-4o with chain-of-thought + a strict choice enum, and maps the
    chosen label back to a score — returning a Langfuse `Evaluation`.
"""

import asyncio
import json

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import Evaluation
from langfuse.langchain import CallbackHandler
from langfuse.openai import OpenAI

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

# LLM judge model — matches the Braintrust autoevals classifiers (gpt-4o, chain-of-thought).
JUDGE_MODEL = "gpt-4o"

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

_judge_client = None


def _get_judge_client() -> OpenAI:
    """Lazy singleton OpenAI client (langfuse.openai wrapper) for the LLM judges, so judge
    calls are themselves traced in Langfuse under the active experiment trace."""
    global _judge_client
    if _judge_client is None:
        _judge_client = OpenAI()
    return _judge_client


# ---------------------------------------------------------------------------
# Dataset generation: per-category control retrieval -> one item per category
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


async def build_dataset() -> list[dict]:
    """Build the local dataset: one item per category (= one evidence subagent).

    For each repo we fetch the root artifact listing once, then retrieve each category's
    controls and route that whole set to a single evidence subagent — exactly how the real
    workflow dispatches one subagent per category.

    Returns a materialized list of `{"input": ..., "metadata": ...}` dicts. Unlike the
    Braintrust path (an async generator consumed inside the CLI's loop), Langfuse's
    `run_experiment` takes concrete local data, so we build the list up front.
    """
    dataset: list[dict] = []
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

            dataset.append(
                {
                    "input": {
                        "repo_owner": repo["repo_owner"],
                        "repo_name": repo["repo_name"],
                        "framework": framework,
                        "category": category,
                        "controls": controls,
                        "artifact_paths": artifact_paths,
                    },
                    "metadata": {
                        "category": category,
                        "num_controls": len(controls),
                        "framework": framework,
                        "repo": f"{repo['repo_owner']}/{repo['repo_name']}",
                        "tree_budget": TREE_BUDGET,
                        "file_budget": FILE_BUDGET,
                    },
                }
            )
    return dataset


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


async def task(*, item, **kwargs) -> str:
    """Langfuse experiment task: run one evidence subagent for the item's category.

    `item` is a local-dataset dict; its `input` holds the repo/category/controls payload
    built by `build_dataset`. A Langfuse CallbackHandler is attached so every nested
    subagent LLM call is captured under this item's experiment trace.
    """
    data = item["input"]
    sub_input = {
        # The subagent's SubAgentInput / _build_evidence_user_message expect a
        # `cluster_id` field; in the real workflow it holds the category string, so we
        # pass the category here to mirror that exactly.
        "cluster_id": data["category"],
        "controls": data["controls"],
        "artifact_paths": data["artifact_paths"],
        "repo_owner": data["repo_owner"],
        "repo_name": data["repo_name"],
    }
    sub_input["messages"] = [
        SystemMessage(content=EVIDENCE_SUBAGENT_SYSTEM_PROMPT),
        HumanMessage(content=_build_evidence_user_message(sub_input)),
    ]

    # Invoking the compiled subgraph directly stops execution at evidence gathering;
    # the full compliance_agent graph would otherwise continue into validation.
    result = await evidence_subagent.ainvoke(
        sub_input, config={"callbacks": [CallbackHandler()]}
    )
    return serialize_transcript(result["messages"])


# ---------------------------------------------------------------------------
# LLM-judge helper: local reimplementation of autoevals.LLMClassifier
# ---------------------------------------------------------------------------
def llm_classify(
    *, name: str, prompt_template: str, choice_scores: dict, output: str, model: str = JUDGE_MODEL
) -> Evaluation:
    """Grade a transcript with a reference-free LLM choice judge and return an Evaluation.

    Mirrors `autoevals.LLMClassifier(use_cot=True)`: renders the judge prompt (substituting
    the transcript for the `{{output}}` placeholder), asks gpt-4o to reason step by step and
    select exactly one choice label (constrained via a strict JSON-schema enum), then maps
    the chosen label to its numeric score. The reasoning + chosen label are stored on the
    Evaluation's comment; the raw label and full choice set go in metadata.
    """
    choices = list(choice_scores.keys())
    rendered = prompt_template.replace("{{output}}", output or "")
    schema = {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Step-by-step justification for the chosen label.",
            },
            "choice": {"type": "string", "enum": choices},
        },
        "required": ["reasoning", "choice"],
        "additionalProperties": False,
    }

    response = _get_judge_client().chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator. Reason step by step about the transcript, "
                    "then select exactly ONE choice label from the allowed set."
                ),
            },
            {"role": "user", "content": rendered},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "classification", "strict": True, "schema": schema},
        },
    )

    parsed = json.loads(response.choices[0].message.content)
    choice = parsed["choice"]
    score = choice_scores.get(choice)
    return Evaluation(
        name=name,
        value=score,
        comment=f"[{choice}] {parsed['reasoning']}",
        metadata={"choice": choice, "choice_scores": choice_scores},
    )
