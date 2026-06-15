import json
import braintrust

from langchain.chat_models import init_chat_model
from langgraph.config import get_stream_writer

from .tools import conclude_evidence, finished_gathering_evidence, think

from .state import EvidenceResult, SubAgentInput
from .utils.github_mcp import GitHubMCPManager

github_mcp_manager = GitHubMCPManager()

haiku_model = init_chat_model(model="anthropic:claude-haiku-4-5")
llm = haiku_model.bind_tools(
    [
        github_mcp_manager.get_file_content,
        github_mcp_manager.get_repository_tree,
        conclude_evidence,
        finished_gathering_evidence,
        think,
    ]
)


def _parse_tool_content(content):
    if isinstance(content, str):
        return json.loads(content)
    return content


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

    raw_result = conclusion.get("evidence_result", conclusion)

    if isinstance(raw_result, EvidenceResult):
        return [raw_result]

    return [EvidenceResult(**raw_result)]


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
def gather_evidence_node(state: SubAgentInput):
    writer = get_stream_writer()

    evidence_results = _extract_concluded_evidence_result(state)
    response = llm.invoke(state["messages"])

    # search_paths = ", ".join(
    #     f"/{tool_call['args'].get('path', '')}"
    #     for tool_call in response.tool_calls
    # )

    # writer({
    #     "type": "status",
    #     "message": f"Searching {search_paths}",
    # })

    result = {"messages": [response]}
    if evidence_results:
        result["evidence_results"] = evidence_results
    return result


def is_finished(state: SubAgentInput):

    last_message = state["messages"][
        -1
    ]  # todo reactor to check the entire tool call list

    # ToolNode returns ToolMessages
    if last_message.type == "tool":
        if last_message.name == "finished_gathering_evidence":
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
