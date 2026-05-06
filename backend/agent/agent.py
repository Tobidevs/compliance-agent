from langgraph.graph import StateGraph, START, END

from .state import ComplianceAgentState
from .nodes import artifact_extractor_node, combine_evidence_results, dispatch, extraction_node, invoke_evidence_subagent, policy_validator_node
import asyncio

compliance_agent_builder = StateGraph(ComplianceAgentState)

compliance_agent_builder.add_node("extraction", extraction_node)
compliance_agent_builder.add_node("policy_validation", policy_validator_node)
compliance_agent_builder.add_node("evidence_subagent", invoke_evidence_subagent)
compliance_agent_builder.add_node("artifact_extraction", artifact_extractor_node)
compliance_agent_builder.add_node("combine_evidence_results", combine_evidence_results)

# compliance_agent_builder.add_edge(START, "extraction")
# compliance_agent_builder.add_edge("extraction", "policy_validation")
compliance_agent_builder.add_edge(START, "artifact_extraction")
compliance_agent_builder.add_conditional_edges("artifact_extraction", dispatch)
compliance_agent_builder.add_edge("evidence_subagent", "combine_evidence_results")
compliance_agent_builder.add_edge("combine_evidence_results", END)

compliance_agent = compliance_agent_builder.compile()

async def run_compliance_agent(framework: str, categories: list[str]):
    initial_state = {
        "framework": framework,
        "category": categories[0],
        "source_code_categories": categories,
        "repo_owner": "acmuta",
        "repo_name": "mavresume"
    }
    final_state = await compliance_agent.ainvoke(initial_state, config={"id": "compliance_agent_run_1"})
    return final_state


async def main():
    await run_compliance_agent(framework="soc2-source-code", categories=["Identity & Access Management"])
    print("Run completed successfully.")

asyncio.run(main())