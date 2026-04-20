from langgraph.graph import StateGraph, START, END
from .state import ComplianceAgentState
from .nodes import extraction_node

compliance_agent_builder = StateGraph(ComplianceAgentState)

compliance_agent_builder.add_node("extraction", extraction_node)

compliance_agent_builder.add_edge(START, "extraction")
compliance_agent_builder.add_edge("extraction", END)

compliance_agent = compliance_agent_builder.compile()

def run_compliance_agent(framework: str, category: str):
    initial_state = {
        "framework": framework,
        "category": category,
        "regulations": []
    }
    final_state = compliance_agent.invoke(initial_state)
    return final_state


print(run_compliance_agent(framework="soc2", category="Identity & Access Management"))