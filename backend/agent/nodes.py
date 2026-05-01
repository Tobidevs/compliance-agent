import asyncio
import os
from typing import Literal
from langchain_pinecone._utilities import cosine_similarity
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.types import Send
from pydantic import BaseModel, Field
from dotenv import load_dotenv


from .prompts import POLICY_EXTRACTION_PROMPT, POLICY_VALIDATION_PROMPT
from .state import (
    ComplianceAgentState,
    PolicyExtractionResults,
    PolicyValidationResults,
)
from .utils.regulation_rag_service import RegulationRAGService
from .utils.policy_rag_service import PolicyRAGService
from .utils.github_mcp import GitHubMCPManager
from .subagents import evidence_subagent

load_dotenv()

regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)



model = init_chat_model(model="anthropic:claude-haiku-4-5")
policy_extraction_model = model.with_structured_output(PolicyExtractionResults)
policy_validation_model = model.with_structured_output(PolicyValidationResults)


# 1st Node: Extract regulations and policies from RAG services based on the input framework and category
async def extraction_node(state: ComplianceAgentState):

    regulation_query = f"Retrieve {state['framework']} control requirements for category {state['category']}. "
    policy_query = (
        f"Retrieve compliance policies relevant to {state['framework']}"
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


async def policy_validator_node(state: ComplianceAgentState):

    extracted_policies = policy_extraction_model.invoke(
        [
            HumanMessage(
                content=POLICY_EXTRACTION_PROMPT.format(
                    regulations="\n\n".join(
                        [
                            f"{reg['title']} ({reg['control_id']}): {reg['requirement']}"
                            for reg in state["regulations"]
                        ]
                    ),
                    excerpts="\n\n".join(
                        [
                            f"Policy Excerpt {i+1}: {policy['content']}"
                            for i, policy in enumerate(state["policies"])
                        ]
                    ),
                )
            )
        ]
    )

    validation_results = policy_validation_model.invoke(
        [
            HumanMessage(
                content=POLICY_VALIDATION_PROMPT.format(
                    extraction_results="\n\n".join(
                        [
                            f" - Regulation {res.regulation_id}: {res.title} - {res.regulation_requirement}\nExcerpt: {res.excerpt or 'No matching claim found'}"
                            for res in extracted_policies.results
                        ]
                    )
                )
            )
        ]
    )

    return {"policy_validation_results": validation_results.results, "policy_excerpts": extracted_policies.results}

def invoke_evidence_subagent(state):
    evidence_result = evidence_subagent.invoke(state)
    return {"evidence_items": [evidence_result["evidence_result"]]}

async def artifact_extractor_node(state: ComplianceAgentState):
    
    regulations = regulation_service.query_regulations(
        query=f"Retrieve {state['framework']} control requirements for category {state['source_code_category']}. ",
        top_k=5,
        namespace=state["framework"].lower(),
        category=state["source_code_category"],
    )
    
    evidence_results = [Send("evidence_subagent", {
        "regulation_id": reg["control_id"],
        "title": reg["title"],
        "requirement": reg["requirement"],
        "evidence_items": [] # to be populated by subagent
    }) for reg in regulations]
    
    
    return {"artifacts": [], "evidence_results": evidence_results}

