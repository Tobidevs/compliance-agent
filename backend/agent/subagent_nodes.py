import json

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from .tools import conclude_evidence, think

from .state import EvidenceItem, EvidenceResult, SubAgentInput
from .utils.github_mcp import GitHubMCPManager

github_mcp_manager = GitHubMCPManager()

model = init_chat_model(model="anthropic:claude-haiku-4-5")
llm = model.bind_tools(
    [
        github_mcp_manager.get_file_content,
        github_mcp_manager.get_repository_tree,
        conclude_evidence,
        think,
    ]
)


def gather_evidence_node(state: SubAgentInput):
    writer = get_stream_writer()

    response = llm.invoke(state["messages"])

    # search_paths = ", ".join(
    #     f"/{tool_call['args'].get('path', '')}"
    #     for tool_call in response.tool_calls
    # )

    # writer({
    #     "type": "status",
    #     "message": f"Searching {search_paths}",
    # })

    return {"messages": [response]}


def is_finished(state: SubAgentInput):

    last_message = state["messages"][
        -1
    ]  # todo reactor to check the entire tool call list

    # ToolNode returns ToolMessages
    if last_message.type == "tool":
        if last_message.name == "conclude_evidence":
            return "process_evidence"

    return "gather_evidence"


def process_evidence_node(state: SubAgentInput):
    writer = get_stream_writer()

    writer(
        {
            "type": "status",
            "message": "Processing evidence and concluding results...",
        }
    )

    evidence_items: list[dict] = []

    if state["messages"]:
        last_message = state["messages"][-1]
    else:
        last_message = None

    if (
        last_message
        and last_message.type == "tool"
        and last_message.name == "conclude_evidence"
    ):
        conclusion = last_message.content
        if isinstance(conclusion, str):
            conclusion = json.loads(conclusion)
        evidence_items = conclusion.get("evidence_items", [])

    normalized_items = []
    for item in evidence_items:
        if isinstance(item, EvidenceItem):
            normalized_items.append(item.model_dump())
        else:
            normalized_items.append(item)

    evidence_results = []
    for index, control in enumerate(state["controls"]):
        item = normalized_items[index] if index < len(normalized_items) else {}
        files_searched = item.get("files_searched", []) or []
        code_snippets = item.get("code_snippets", []) or []
        description = item.get("description", "") or ""
        no_evidence_found = item.get("no_evidence_found")
        if no_evidence_found is None:
            no_evidence_found = len(code_snippets) == 0
        evidence_results.append(
            EvidenceResult(
                regulation_id=control["regulation_id"],
                title=control["title"],
                requirement=control["requirement"],
                files_searched=files_searched,
                code_snippets=code_snippets,
                description=description,
                no_evidence_found=no_evidence_found,
            )
        )

    return {"evidence_results": evidence_results}
