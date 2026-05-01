from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from .state import EvidenceSubAgentState, EvidenceResult
from utils.github_mcp import GitHubMCPManager

github_mcp_manager = GitHubMCPManager()

model = init_chat_model(model="anthropic:claude-haiku-4-5")
llm = model.bind_tools([github_mcp_manager.search_codebase, github_mcp_manager.get_file_content, ])

def gather_evidence_node(state: EvidenceSubAgentState):
    response = llm.invoke(
        [
            HumanMessage(
                content="You are a helpful assistant." # todo Build prompt
            )
        ]
    )
    return {"messages": response.messages} #todo verify output
    
    
def concluded_evidence(state: EvidenceSubAgentState):
    last_message = state["messages"][-1]

    # ToolNode returns ToolMessages
    if last_message.type == "tool":
        if last_message.name == "concluded_evidence":
            return "process_evidence"

    return "gather_evidence"

def process_evidence_node(state: EvidenceSubAgentState):

    last_message = state["messages"][-1]
    if last_message.type == "tool" and last_message.name == "concluded_evidence":
        tool_args = last_message.args
        files_searched = tool_args.get("files_searched", [])
        code_snippets = tool_args.get("code_snippets", [])
        description = tool_args.get("description", "")
        no_evidence_found = tool_args.get("no_evidence_found", False)\
    
    evidence = EvidenceResult(
        regulation_id=state["regulation_id"],
        title=state["title"],
        requirement=state["requirement"],
        files_searched=files_searched,
        code_snippets=code_snippets,
        description=description,
        no_evidence_found=no_evidence_found,
    )

    return {"evidence_result": evidence}