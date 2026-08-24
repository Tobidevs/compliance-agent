import json
import os
from typing import Annotated

import braintrust

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from langgraph.prebuilt import InjectedState

from .budget import BudgetLedger
from .resilience import (
    DESERIALIZATION_ERRORS,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    degraded_evidence_result,
    format_error,
)
from .tools import conclude_evidence, finished_gathering_evidence, think

from .state import EvidenceResult, SubAgentInput
from .utils.github_mcp import GitHubMCPManager

load_dotenv()

github_mcp_manager = GitHubMCPManager()


@tool("get_file_content")
async def get_file_content(
    owner: str, repo: str, path: str, state: Annotated[dict, InjectedState]
) -> str:
    """Retrieve the content of a file from a GitHub repository.

    If path is a folder, returns the list of paths it contains instead.
    """
    ledger = state.get("budget")
    refusal = ledger.spend("fetch") if ledger is not None else None
    # Refused calls never reach the MCP client, so the budget is a hard cost ceiling.
    if refusal:
        return refusal
    return await github_mcp_manager.get_file_content(owner=owner, repo=repo, path=path)


@tool("get_repository_tree")
async def get_repository_tree(
    owner: str,
    repo: str,
    state: Annotated[dict, InjectedState],
    tree_sha: str | None = None,
    recursive: bool = False,
    path_filter: str | None = None,
):
    """Retrieve the repository tree for a ref or tree SHA."""
    ledger = state.get("budget")
    refusal = ledger.spend("tree") if ledger is not None else None
    # Refused calls never reach the MCP client, so the budget is a hard cost ceiling.
    if refusal:
        return refusal
    return await github_mcp_manager.get_repository_tree(
        owner=owner,
        repo=repo,
        tree_sha=tree_sha,
        recursive=recursive,
        path_filter=path_filter,
    )


# Single source of truth for the subagent's tools: bound to the model and run by ToolNode.
EVIDENCE_TOOLS = [
    get_file_content,
    get_repository_tree,
    conclude_evidence,
    finished_gathering_evidence,
    think,
]

# Swap providers via env, e.g. EVIDENCE_SUBAGENT_MODEL="openai:gpt-5.4-mini".
evidence_model = init_chat_model(
    model=os.getenv("EVIDENCE_SUBAGENT_MODEL", "anthropic:claude-haiku-4-5"),
    max_retries=LLM_MAX_RETRIES,
    timeout=LLM_TIMEOUT_SECONDS,
)
llm = evidence_model.bind_tools(EVIDENCE_TOOLS)


def _parse_tool_content(content):
    if isinstance(content, str):
        # Tool content is model-adjacent text; non-JSON must not kill the subagent.
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    return content


def _coerce_evidence_result(raw_result) -> EvidenceResult | None:
    """Build an EvidenceResult, degrading to a placeholder rather than raising."""
    if isinstance(raw_result, EvidenceResult):
        return raw_result
    if not isinstance(raw_result, dict):
        return None
    try:
        return EvidenceResult(**raw_result)
    except DESERIALIZATION_ERRORS as error:
        # Keep the control visible downstream whenever the id survived the malformed payload.
        if not str(raw_result.get("regulation_id") or "").strip():
            return None
        return degraded_evidence_result(raw_result, format_error(error))


def _find_matching_tool_call_args(state: SubAgentInput, tool_message) -> dict | None:
    tool_call_id = getattr(tool_message, "tool_call_id", None)

    for message in reversed(state["messages"][:-1]):
        tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in tool_calls:
            if tool_call.get("id") != tool_call_id:
                continue
            if tool_call.get("name") != "conclude_evidence":
                continue
            return tool_call.get("args", {})

    return None


def _extract_concluded_evidence_result(state: SubAgentInput) -> list[EvidenceResult]:
    if not state["messages"]:
        return []

    last_message = state["messages"][-1]
    if last_message.type != "tool" or last_message.name != "conclude_evidence":
        return []

    conclusion = _find_matching_tool_call_args(state, last_message)
    if conclusion is None:
        conclusion = _parse_tool_content(last_message.content)

    if isinstance(conclusion, dict):
        raw_result = conclusion.get("evidence_result", conclusion)
    else:
        raw_result = conclusion

    evidence_result = _coerce_evidence_result(raw_result)
    return [evidence_result] if evidence_result else []


def _extract_pending_concluded_evidence_results(
    state: SubAgentInput,
) -> list[EvidenceResult]:
    evidence_results = []

    for index, message in enumerate(state["messages"]):
        if message.type != "tool" or message.name != "conclude_evidence":
            continue

        next_messages = state["messages"][index + 1 :]
        was_followed_by_model_turn = any(
            next_message.type == "ai" for next_message in next_messages
        )
        if was_followed_by_model_turn:
            continue

        evidence_results.extend(
            _extract_concluded_evidence_result(
                {
                    **state,
                    "messages": state["messages"][: index + 1],
                }
            )
        )

    return evidence_results


@braintrust.traced(name="gather_evidence")
async def gather_evidence_node(state: SubAgentInput):
    writer = get_stream_writer()

    evidence_results = _extract_concluded_evidence_result(state)

    # Self-heal for callers that invoke the subgraph directly (evals) without a ledger.
    ledger = state.get("budget") or BudgetLedger.for_controls(state.get("controls", []))
    # Runs before every tool batch, so the per-control counters track the current control.
    ledger.sync_progress(state["messages"])

    response = await llm.ainvoke(state["messages"])

    # search_paths = ", ".join(
    #     f"/{tool_call['args'].get('path', '')}"
    #     for tool_call in response.tool_calls
    # )

    # writer({
    #     "type": "status",
    #     "message": f"Searching {search_paths}",
    # })

    result = {"messages": [response], "budget": ledger}
    if evidence_results:
        result["evidence_results"] = evidence_results
    return result


def is_finished(state: SubAgentInput):
    # ToolNode emits one ToolMessage per parallel tool call, so the terminate signal
    # is not necessarily last: scan the whole trailing run of ToolMessages.
    for message in reversed(state["messages"]):
        if getattr(message, "type", None) != "tool":
            break
        if getattr(message, "name", None) == "finished_gathering_evidence":
            return "process_evidence"

    return "gather_evidence"


@braintrust.traced(name="process_evidence")
def process_evidence_node(state: SubAgentInput):
    writer = get_stream_writer()

    writer(
        {
            "type": "status",
            "message": "Processing evidence and concluding results...",
        }
    )

    evidence_results = _extract_pending_concluded_evidence_results(state)
    if evidence_results:
        return {"evidence_results": evidence_results}
    return {}
