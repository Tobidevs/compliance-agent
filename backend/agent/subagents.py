from langgraph.graph import StateGraph, START, END
from .state import SubAgentInput
from langgraph.prebuilt import ToolNode

from .tools import conclude_evidence, finished_gathering_evidence, think
from .subagent_nodes import (
    gather_evidence_node,
    github_mcp_manager,
    is_finished,
    process_evidence_node,
)
from .utils.github_mcp import format_github_mcp_tool_error

evidence_subagent_builder = StateGraph(SubAgentInput)

evidence_subagent_builder.add_node("gather_evidence", gather_evidence_node)
evidence_subagent_builder.add_node(
    "tool_call",
    ToolNode(
        [
            github_mcp_manager.get_file_content,
            github_mcp_manager.get_repository_tree,
            conclude_evidence,
            finished_gathering_evidence,
            think,
        ],
        handle_tool_errors=format_github_mcp_tool_error,
    ),
)
evidence_subagent_builder.add_node("process_evidence", process_evidence_node)

evidence_subagent_builder.add_edge(START, "gather_evidence")
evidence_subagent_builder.add_edge("gather_evidence", "tool_call")
evidence_subagent_builder.add_conditional_edges("tool_call", is_finished, {
    "gather_evidence": "gather_evidence",
    "process_evidence": "process_evidence",
})
evidence_subagent_builder.add_edge("process_evidence", END)

evidence_subagent = evidence_subagent_builder.compile()
