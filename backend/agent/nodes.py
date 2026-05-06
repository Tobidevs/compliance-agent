import asyncio
import os
from typing import Literal
from langchain_pinecone._utilities import cosine_similarity
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Send
from pydantic import BaseModel, Field
from dotenv import load_dotenv


from .prompts import (
    POLICY_EXTRACTION_PROMPT,
    POLICY_VALIDATION_PROMPT,
    EVIDENCE_SUBAGENT_SYSTEM_PROMPT,
)
from .state import (
    ComplianceAgentState,
    PolicyExtractionResults,
    PolicyValidationResults,
)
from .utils.regulation_rag_service import RegulationRAGService
from .utils.policy_rag_service import PolicyRAGService
from .utils.github_mcp import GitHubMCPManager
from .utils._agent_utils import _build_user_message
from .subagents import evidence_subagent
from .clusters import group_controls_into_clusters, filter_paths_for_cluster, CLUSTERS

load_dotenv()

regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)


gpt_model = init_chat_model(model="openai:gpt-4.1")  # anthropic:claude-haiku-4-5
policy_extraction_model = gpt_model.with_structured_output(PolicyExtractionResults)
policy_validation_model = gpt_model.with_structured_output(PolicyValidationResults)

github_mcp_manager = GitHubMCPManager()


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

    return {
        "policy_validation_results": validation_results.results,
        "policy_excerpts": [res.model_dump() for res in extracted_policies.results],
    }


async def invoke_evidence_subagent(state, config: RunnableConfig | None = None):
    base_config = config or {}
    evidence_result = await evidence_subagent.ainvoke(
        state,
        config={
            **base_config,
            "name": f"invoked_evidence_subagent_{state['cluster_id']}",
        },
    )

    evidence_items = evidence_result.get("evidence_results", [])
    if isinstance(evidence_items, list):
        return {"evidence_items": evidence_items}

    return {"evidence_items": [evidence_items]}


async def artifact_extractor_node(
    state: ComplianceAgentState, config: RunnableConfig | None = None
):
    regulations = []
    categories = state["source_code_categories"]
    if isinstance(categories, str):
        categories = [categories]

    for category in categories:
        regulations.extend(
            regulation_service.query_regulations(
                query=f"Retrieve {state['framework']} control requirements for category {category}. ",
                top_k=3,
                rerank_top_k=1,
                namespace=state["framework"].lower(),
                category=category,
            )
        )

    file_paths = await github_mcp_manager.get_file_content(
        owner=state["repo_owner"], repo=state["repo_name"], path=""
    )

    clusters = group_controls_into_clusters([reg.fields for reg in regulations])

    return {
        "regulations": [reg.fields for reg in regulations],
        "artifact_paths": file_paths,
        "clusters": clusters,
    }


def dispatch(state: ComplianceAgentState, config: RunnableConfig | None = None):
    clusters = state.get("clusters", {})
    file_paths = state.get("artifact_paths", [])

    sends = []
    for cluster_id, controls in clusters.items():
        if not controls:
            continue

        subagent_input = {
            "cluster_id": cluster_id,
            "controls": controls,
            "artifact_paths": file_paths,
            "repo_owner": state["repo_owner"],
            "repo_name": state["repo_name"],
        }
        subagent_input["messages"] = [
            SystemMessage(content=EVIDENCE_SUBAGENT_SYSTEM_PROMPT),
            HumanMessage(content=_build_user_message(subagent_input)),
        ]

        sends.append(
            Send(
                "evidence_subagent",
                subagent_input,
            )
        )

    return sends


def combine_evidence_results(state: ComplianceAgentState):
    evidence_items = state.get("evidence_items", [])
    if not isinstance(evidence_items, list):
        evidence_items = [evidence_items]

    return {"evidence_results": evidence_items}


