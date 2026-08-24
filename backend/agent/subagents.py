from langgraph.graph import StateGraph, START, END
from .state import SubAgentInput
from langgraph.prebuilt import ToolNode

from .subagent_nodes import (
    EVIDENCE_TOOLS,
    gather_evidence_node,
    is_finished,
    process_evidence_node,
)

evidence_subagent_builder = StateGraph(SubAgentInput)

evidence_subagent_builder.add_node("gather_evidence", gather_evidence_node)
evidence_subagent_builder.add_node("tool_call", ToolNode(EVIDENCE_TOOLS))
evidence_subagent_builder.add_node("process_evidence", process_evidence_node)

evidence_subagent_builder.add_edge(START, "gather_evidence")
evidence_subagent_builder.add_edge("gather_evidence", "tool_call")
evidence_subagent_builder.add_conditional_edges("tool_call", is_finished, {
    "gather_evidence": "gather_evidence",
    "process_evidence": "process_evidence",
})
evidence_subagent_builder.add_edge("process_evidence", END)

evidence_subagent = evidence_subagent_builder.compile()
