import asyncio
import json
import os
from typing import Literal
import braintrust
from langchain_pinecone._utilities import cosine_similarity
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Send
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field
from dotenv import load_dotenv


from .prompts import (
    POLICY_EXTRACTION_PROMPT,
    POLICY_VALIDATION_PROMPT,
    EVIDENCE_SUBAGENT_SYSTEM_PROMPT,
    VALIDATION_SUBAGENT_SYSTEM_PROMPT,
)
from .state import (
    ComplianceAgentState,
    EvidenceResult,
    PolicyExtractionResults,
    PolicyValidationResults,
    ValidationBatch,
)
from .utils.regulation_rag_service import RegulationRAGService, REGULATION_NAMESPACE
from .utils.policy_rag_service import PolicyRAGService
from .utils.github_mcp import GitHubMCPManager
from .utils.agent_utils import (
    _build_evidence_user_message,
    _build_validation_user_message,
)
from .subagents import evidence_subagent
from .clusters import (
    group_controls_into_clusters,
    filter_paths_for_cluster,
    update_clusters_with_evidence,
)

load_dotenv()

regulation_service = RegulationRAGService(index="compliance-frameworks")
policy_service = PolicyRAGService(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)


gpt_model = init_chat_model(model="openai:gpt-5.4-mini")
haiku_model = init_chat_model(model="anthropic:claude-haiku-4-5")
sonnet_model = init_chat_model(model="anthropic:claude-sonnet-4-6")
# Swap providers via env, e.g. VALIDATION_SUBAGENT_MODEL="openai:gpt-5.4-mini".
validation_model = init_chat_model(
    model=os.getenv("VALIDATION_SUBAGENT_MODEL", "anthropic:claude-sonnet-4-6")
)
policy_extraction_model = haiku_model.with_structured_output(PolicyExtractionResults)
policy_validation_model = haiku_model.with_structured_output(PolicyValidationResults)
compliance_validation_model = validation_model.with_structured_output(ValidationBatch)

github_mcp_manager = GitHubMCPManager()


def _normalize_evidence_items(raw_items: list) -> list[EvidenceResult]:
    normalized: list[EvidenceResult] = []
    for item in raw_items:
        if isinstance(item, EvidenceResult):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            normalized.append(EvidenceResult(**item))
    return normalized


@braintrust.traced(name="extraction")
async def extraction_node(state: ComplianceAgentState):

    policy_query = (
        f"Retrieve compliance policies relevant to {state['framework']}"
        f"and category {state['category']}."
    )

    regulation_task = asyncio.to_thread(
        regulation_service.get_controls_for_categories,
        categories=state["category"],
        namespace=REGULATION_NAMESPACE,
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


@braintrust.traced(name="policy_validation")
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
    if not isinstance(evidence_items, list):
        evidence_items = [evidence_items]

    normalized_items = _normalize_evidence_items(evidence_items)
    return {"evidence_items": normalized_items}


@braintrust.traced(name="artifact_extraction")
async def artifact_extractor_node(
    state: ComplianceAgentState, config: RunnableConfig | None = None
):
    writer = get_stream_writer()

    regulations = []
    categories = state["source_code_categories"]
    if isinstance(categories, str):
        categories = [categories]

    writer(
        {
            "type": "status",
            "message": f"Extracting regulations and fetching {state['repo_owner']}/{state['repo_name']} root directory file list...",
        }
    )

    regulation_task = asyncio.to_thread(
        regulation_service.get_controls_for_categories,
        categories=categories,
        namespace=REGULATION_NAMESPACE,
    )

    regulation_hits, file_paths = await asyncio.gather(
        regulation_task,
        github_mcp_manager.get_file_content(
            owner=state["repo_owner"], repo=state["repo_name"], path=""
        ),
    )

    regulations = list(regulation_hits)

    clusters = group_controls_into_clusters([reg.fields for reg in regulations])

    return {
        "regulations": [reg.fields for reg in regulations],
        "artifact_paths": file_paths,
        "clusters": clusters,
    }


def evidence_subagent_dispatch(
    state: ComplianceAgentState, config: RunnableConfig | None = None
):
    writer = get_stream_writer()
    clusters = state.get("clusters", {})
    file_paths = state.get("artifact_paths", [])

    writer(
        {
            "type": "status",
            "message": f"Gathering evidence for {state.get('framework', '')} compliance...",
        }
    )

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
            HumanMessage(content=_build_evidence_user_message(subagent_input)),
        ]

        sends.append(
            Send(
                "evidence_subagent",
                subagent_input,
            )
        )

    return sends


def prepare_validation_subagents(state: ComplianceAgentState):
    evidence_items = _normalize_evidence_items(state.get("evidence_items", []))
    clusters = update_clusters_with_evidence(state.get("clusters", {}), evidence_items)
    # Do not return evidence_items: ComplianceAgentState.evidence_items uses operator.add,
    # so returning the full list here would append it again, doubling every item.
    return {"clusters": clusters}


def validation_subagent_dispatch(
    state: ComplianceAgentState, config: RunnableConfig | None = None
):
    writer = get_stream_writer()
    writer(
        {
            "type": "status",
            "message": "Validating evidence and concluding compliance results...",
        }
    )
    clusters = state.get("clusters", {})
    evidence_items = state.get("evidence_items", [])

    sends = []
    for cluster_id, controls in clusters.items():
        if not controls:
            continue

        control_ids = {control.get("regulation_id") for control in controls}
        scoped_evidence = [
            item for item in evidence_items if item.regulation_id in control_ids
        ]

        subagent_input = {
            "cluster_id": cluster_id,
            "controls": controls,
            "evidence_items": scoped_evidence,
            "framework": state.get("framework", "N/A"),
            "category": state.get("category", "N/A"),
        }
        subagent_input["messages"] = [
            SystemMessage(content=VALIDATION_SUBAGENT_SYSTEM_PROMPT),
            HumanMessage(content=_build_validation_user_message(subagent_input)),
        ]

        sends.append(
            Send(
                "validation_subagent",
                subagent_input,
            )
        )

    return sends


@braintrust.traced(name="validation_subagent")
def invoke_validation_subagent(state, config: RunnableConfig | None = None):
    raw_response = compliance_validation_model.invoke(state["messages"])
    if isinstance(raw_response, ValidationBatch):
        validation_result = raw_response
    else:
        content = (
            raw_response.content
            if hasattr(raw_response, "content")
            else str(raw_response)
        )
        parsed = json.loads(content)
        if isinstance(parsed, list):
            parsed = {"validations": parsed}
        if isinstance(parsed, dict) and isinstance(parsed.get("validations"), str):
            parsed["validations"] = json.loads(parsed["validations"])
        validation_result = ValidationBatch.model_validate(parsed)
    writer = get_stream_writer()
    writer(
        {
            "type": "updates",
            "data": {"validation_results": validation_result.validations},
        }
    )

    return {"validation_results": validation_result.validations}


def combine_validation_results(state: ComplianceAgentState):
    all_results: list = []
    for item in state.get("validation_results", []):
        if isinstance(item, list):
            all_results.extend(item)
        else:
            all_results.append(item)

    writer = get_stream_writer()
    writer(
        {
            "type": "updates",
            "data": {"validation_results": all_results},
        }
    )

    return {"validation_results": all_results}
