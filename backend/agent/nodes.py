import asyncio
import os

from .state import ComplianceAgentState
from .utils.regulation_rag_service import RegulationRAGService
from .utils.policy_rag_service import PolicyRAGService

regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)

# 1st Node: Extract regulations and policies from RAG services based on the input framework and category
async def extraction_node(state: ComplianceAgentState):

    regulation_query = f"Retrieve {state['framework']} control requirements for category {state['category']}. "
    policy_query = (
        f"Retrieve compliance policies relevant to {state['framework']} "
        f"and category {state['category']}."
    )

    regulation_task = asyncio.to_thread(
        regulation_service.query_regulations,
        query=regulation_query,
        top_k=5,
        namespace=state["framework"].lower(),
        category=state["category"],
    )
    policy_task = asyncio.to_thread(
        policy_service.query_policies,
        query=policy_query,
        top_k=5,
    )

    regulation_results, policy_results = await asyncio.gather(
        regulation_task, policy_task
    )
    formatted_regulations = regulation_service.format_regulation_results(
        regulation_results
    )
    formatted_policies = policy_service.format_policy_results(policy_results)
    return {"regulations": formatted_regulations, "policies": formatted_policies}
