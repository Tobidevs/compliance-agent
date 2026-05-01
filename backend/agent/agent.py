from langgraph.graph import StateGraph, START, END
from .state import ComplianceAgentState
from .nodes import extraction_node, invoke_evidence_subagent, policy_validator_node
import asyncio

compliance_agent_builder = StateGraph(ComplianceAgentState)

compliance_agent_builder.add_node("extraction", extraction_node)
compliance_agent_builder.add_node("policy_validation", policy_validator_node)
compliance_agent_builder.add_node("evidence_subagent", invoke_evidence_subagent)

compliance_agent_builder.add_edge(START, "extraction")
compliance_agent_builder.add_edge("extraction", "policy_validation")
compliance_agent_builder.add_edge("policy_validation", END)

compliance_agent = compliance_agent_builder.compile()

async def run_compliance_agent(framework: str, category: str):
    initial_state = {
        "framework": framework,
        "category": category,
        "regulations": []
    }
    final_state = await compliance_agent.ainvoke(initial_state)
    return final_state


async def main():
    await run_compliance_agent(framework="soc2-policy-doc", category="Identity & Access Management")
    print("Run completed successfully.")

asyncio.run(main())