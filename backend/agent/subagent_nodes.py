import json

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from .tools import conclude_evidence, think

from .state import EvidenceResult, SubAgentInput
from .utils.github_mcp import GitHubMCPManager

github_mcp_manager = GitHubMCPManager()

model = init_chat_model(model="anthropic:claude-haiku-4-5")
llm = model.bind_tools([github_mcp_manager.get_file_content, conclude_evidence, think])


def gather_evidence_node(state: SubAgentInput):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def is_finished(state: SubAgentInput):

    last_message = state["messages"][-1] # todo reactor to check the entire tool call list 

    # ToolNode returns ToolMessages
    if last_message.type == "tool":
        if last_message.name == "conclude_evidence":
            return "process_evidence"

    return "gather_evidence"


def process_evidence_node(state: SubAgentInput):

    files_searched = []
    code_snippets = []
    description = ""
    no_evidence_found = False

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
        files_searched = conclusion["files_searched"]
        code_snippets = conclusion["code_snippets"]
        description = conclusion["description"]
        no_evidence_found = conclusion["no_evidence_found"]

    evidence_results = []
    for control in state["controls"]:
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
