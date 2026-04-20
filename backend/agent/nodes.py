import os

from .state import ComplianceAgentState
from .utils.regulation_rag_service import RegulationRAGService
from .utils.policy_rag_service import PolicyRAGService

regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))


def extraction_node(state: ComplianceAgentState):
    # Query the regulations database based on the framework and category
    regulation_results = regulation_service.query_regulations(
        query=f"Retrieve {state['framework']} control requirements for category {state['category']}. ",  # TODO: Refine the query for better retrieval
        top_k=5,
        namespace=state["framework"].lower(),
        category=state["category"],
    )

    policy_results = policy_service.query_policies(
        query=f"Retrieve compliance policies relevant to {state['framework']} and category {state['category']}.", # TODO: Refine the query for better retrieval
        top_k=5
    )

    formatted_regulations = regulation_service.format_regulation_results(
        regulation_results
    )
    formatted_policies = policy_service.format_policy_results(
        policy_results
    )
    return {"regulations": formatted_regulations, "policies": formatted_policies}
