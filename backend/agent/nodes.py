import asyncio
import json
import os
from functools import cache
from typing import Literal
import braintrust
from langchain_pinecone._utilities import cosine_similarity
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.types import Send
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field
from dotenv import load_dotenv


from .prompts import (
    POLICY_EXTRACTION_PROMPT,
    POLICY_VALIDATION_PROMPT,
    EVIDENCE_SUBAGENT_SYSTEM_PROMPT,
    VALIDATION_SUBAGENT_SYSTEM_PROMPT,
    cacheable_system_message,
)
from .state import (
    ComplianceAgentState,
    ControlValidation,
    EvidenceResult,
    PolicyExtractionResults,
    PolicyValidationResults,
    ValidationBatch,
)
from .utils.regulation_rag_service import RegulationRAGService, REGULATION_NAMESPACE
from .utils.policy_rag_service import PolicyRAGService
from .utils.github_mcp import DirListing, get_github_mcp_manager
from .utils.agent_utils import (
    _build_evidence_user_message,
    _build_validation_user_message,
)
from .subagents import evidence_subagent
from .subagent_nodes import EVIDENCE_MODEL_ID
from .budget import BudgetLedger
from .resilience import (
    DESERIALIZATION_ERRORS,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    cluster_slot,
    error_validation,
    format_error,
    no_evidence_validation,
    normalize_regulation_id,
)
from .clusters import (
    group_controls_into_clusters,
    filter_paths_for_cluster,
    update_clusters_with_evidence,
)

load_dotenv()

# Everything below is built on first use, never at import. Constructing these eagerly made
# `import agent.agent` read provider credentials, open a Chroma store on disk, and — via
# PineconeClient.has_index() — potentially *create* a Pinecone index as an import side effect.


@cache
def get_regulation_service() -> RegulationRAGService:
    return RegulationRAGService(index="compliance-frameworks")


@cache
def get_policy_service() -> PolicyRAGService:
    return PolicyRAGService(
        persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    )


# Provider SDKs back max_retries with exponential backoff + jitter; timeout bounds a hung call.
_llm_defaults = {"max_retries": LLM_MAX_RETRIES, "timeout": LLM_TIMEOUT_SECONDS}
# Swap providers via env, e.g. VALIDATION_SUBAGENT_MODEL="openai:gpt-5.4-mini".
VALIDATION_MODEL_ID = os.getenv("VALIDATION_SUBAGENT_MODEL", "anthropic:claude-sonnet-4-6")


@cache
def get_gpt_model():
    return init_chat_model(model="openai:gpt-5.4-mini", **_llm_defaults)


@cache
def get_haiku_model():
    return init_chat_model(model="anthropic:claude-haiku-4-5", **_llm_defaults)


@cache
def get_sonnet_model():
    return init_chat_model(model="anthropic:claude-sonnet-4-6", **_llm_defaults)


@cache
def get_validation_model():
    return init_chat_model(model=VALIDATION_MODEL_ID, **_llm_defaults)


@cache
def get_policy_extraction_model():
    return get_haiku_model().with_structured_output(PolicyExtractionResults)


@cache
def get_policy_validation_model():
    return get_haiku_model().with_structured_output(PolicyValidationResults)


@cache
def get_compliance_validation_model():
    return get_validation_model().with_structured_output(ValidationBatch)


def _load_controls_for_categories(categories: list[str] | str):
    """Runs on a worker thread, so the service is built off the event loop too."""
    return get_regulation_service().get_controls_for_categories(
        categories=categories, namespace=REGULATION_NAMESPACE
    )


def _normalize_evidence_items(raw_items: list) -> list[EvidenceResult]:
    normalized: list[EvidenceResult] = []
    for item in raw_items:
        if isinstance(item, EvidenceResult):
            normalized.append(item)
            continue
        if not isinstance(item, dict):
            continue
        try:
            normalized.append(EvidenceResult(**item))
        except DESERIALIZATION_ERRORS:
            # A malformed item is dropped here and backfilled by reconciliation.
            continue
    return normalized


@braintrust.traced(name="extraction")
async def extraction_node(state: ComplianceAgentState):

    policy_query = (
        f"Retrieve compliance policies relevant to {state['framework']}"
        f"and category {state['category']}."
    )

    regulation_task = asyncio.to_thread(
        _load_controls_for_categories,
        state["category"],
    )
    policy_task = asyncio.to_thread(
        lambda: get_policy_service().query_policies(query=policy_query, top_k=5)
    )

    regulation_results, policy_results = await asyncio.gather(
        regulation_task, policy_task
    )
    formatted_regulations = get_regulation_service().format_regulation_results(
        regulation_results
    )
    formatted_policies = get_policy_service().format_policy_results(policy_results)

    return {"regulations": formatted_regulations, "policies": formatted_policies}


@braintrust.traced(name="policy_validation")
async def policy_validator_node(state: ComplianceAgentState):

    extracted_policies = get_policy_extraction_model().invoke(
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

    validation_results = get_policy_validation_model().invoke(
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


def _record_cluster_failure(cluster_id: str, stage: str, error: BaseException) -> dict:
    """Sentinel state update for a failed Send branch; the run continues without it."""
    reason = format_error(error)
    get_stream_writer()(
        {
            "type": "status",
            "message": f"Cluster '{cluster_id}' failed during {stage} ({reason}); continuing with the remaining clusters.",
        }
    )
    return {"cluster_errors": [{"cluster_id": cluster_id, "stage": stage, "error": reason}]}


async def invoke_evidence_subagent(state, config: RunnableConfig | None = None):
    base_config = config or {}
    cluster_id = state.get("cluster_id", "unknown")
    ledger = state.get("budget") or BudgetLedger.for_controls(state.get("controls", []))
    try:
        # The semaphore, not the graph, decides how many clusters hit the model at once.
        # cluster_scope holds one MCP session and one file cache for the whole subagent
        # run: one handshake per cluster instead of one per tool call.
        async with cluster_slot(), get_github_mcp_manager().cluster_scope():
            evidence_result = await evidence_subagent.ainvoke(
                {**state, "budget": ledger},
                config={
                    **base_config,
                    "name": f"invoked_evidence_subagent_{cluster_id}",
                    # LangGraph 1.1.8 defaults to 10007 steps, so a stuck subagent loops
                    # effectively forever; the enforced budget gives it a real ceiling.
                    "recursion_limit": ledger.recursion_limit(),
                },
            )
    except GraphRecursionError as error:
        # Called out explicitly: the derived recursion_limit made this reachable.
        return _record_cluster_failure(cluster_id, "evidence gathering", error)
    except Exception as error:
        # MCP failures, 429s, ValidationErrors — one cluster must not kill the run.
        return _record_cluster_failure(cluster_id, "evidence gathering", error)

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

    regulation_task = asyncio.to_thread(_load_controls_for_categories, categories)

    regulation_hits, root_listing = await asyncio.gather(
        regulation_task,
        get_github_mcp_manager().fetch_path(
            owner=state["repo_owner"], repo=state["repo_name"], path=""
        ),
    )

    # artifact_paths is list[str]; a non-directory root degrades to its own path.
    file_paths = (
        root_listing.entries
        if isinstance(root_listing, DirListing)
        else [root_listing.path]
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
            # Sized from cluster width: 3 fetches / 2 trees per assigned control.
            "budget": BudgetLedger.for_controls(controls),
        }
        subagent_input["messages"] = [
            # ~5k tokens re-sent on every turn of every cluster without a cache breakpoint.
            cacheable_system_message(
                EVIDENCE_SUBAGENT_SYSTEM_PROMPT, EVIDENCE_MODEL_ID
            ),
            HumanMessage(content=_build_evidence_user_message(subagent_input)),
        ]

        sends.append(
            Send(
                "evidence_subagent",
                subagent_input,
            )
        )

    # An empty conditional edge would strand the graph, skipping reconciliation entirely.
    return sends or ["prepare_validation_subagents"]


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
    # Clusters whose evidence subagent died have nothing to validate; reconciliation marks them.
    failed_clusters = {
        failure.get("cluster_id") for failure in state.get("cluster_errors", [])
    }

    sends = []
    for cluster_id, controls in clusters.items():
        if not controls or cluster_id in failed_clusters:
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
            # One call per cluster, so the breakpoint pays off across clusters, not turns.
            cacheable_system_message(
                VALIDATION_SUBAGENT_SYSTEM_PROMPT, VALIDATION_MODEL_ID
            ),
            HumanMessage(content=_build_validation_user_message(subagent_input)),
        ]

        sends.append(
            Send(
                "validation_subagent",
                subagent_input,
            )
        )

    # An empty conditional edge would strand the graph, skipping reconciliation entirely.
    return sends or ["combine_validation_results"]


def _parse_validation_batch(raw_response) -> ValidationBatch:
    """Structured output is not guaranteed: a truncated batch arrives as unparseable text."""
    if isinstance(raw_response, ValidationBatch):
        return raw_response

    content = (
        raw_response.content if hasattr(raw_response, "content") else str(raw_response)
    )
    parsed = json.loads(content)
    if isinstance(parsed, list):
        parsed = {"validations": parsed}
    if isinstance(parsed, dict) and isinstance(parsed.get("validations"), str):
        parsed["validations"] = json.loads(parsed["validations"])
    return ValidationBatch.model_validate(parsed)


def _align_validations(
    produced: list[ControlValidation], controls: list[dict]
) -> list[ControlValidation]:
    """Return at most one validation per requested control, in the requested order.

    Duplicates and ids the batch invented are dropped so the accumulated
    validation_results stays a strict subset of the roster reconciliation joins against.
    """
    expected: dict[str, str] = {}
    for control in controls:
        raw_id = str(control.get("regulation_id") or "")
        expected.setdefault(normalize_regulation_id(raw_id), raw_id)

    matched: dict[str, ControlValidation] = {}
    for validation in produced:
        key = normalize_regulation_id(getattr(validation, "regulation_id", ""))
        if key not in expected or key in matched:
            continue
        canonical_id = expected[key]
        if validation.regulation_id != canonical_id:
            # Snap casing/whitespace drift back so the reconciliation join matches.
            validation = validation.model_copy(update={"regulation_id": canonical_id})
        matched[key] = validation

    return [matched[key] for key in expected if key in matched]


@braintrust.traced(name="validation_subagent")
async def invoke_validation_subagent(state, config: RunnableConfig | None = None):
    cluster_id = state.get("cluster_id", "unknown")
    controls = state.get("controls", [])
    try:
        # The semaphore, not the graph, decides how many clusters hit the model at once.
        async with cluster_slot():
            raw_response = await get_compliance_validation_model().ainvoke(state["messages"])
        validation_result = _parse_validation_batch(raw_response)
    except GraphRecursionError as error:
        # Called out explicitly: the derived recursion_limit made this reachable.
        return _validation_failure(cluster_id, controls, error)
    except Exception as error:
        # Covers JSONDecodeError/ValidationError from a truncated batch as well as API failures.
        return _validation_failure(cluster_id, controls, error)

    validations = _align_validations(validation_result.validations, controls)

    writer = get_stream_writer()
    writer(
        {
            "type": "updates",
            "data": {"validation_results": validations},
        }
    )

    return {"validation_results": validations}


def _validation_failure(
    cluster_id: str, controls: list[dict], error: BaseException
) -> dict:
    """Emit an ERROR verdict per control in the cluster instead of aborting the run."""
    failure = _record_cluster_failure(cluster_id, "validation", error)
    reason = failure["cluster_errors"][0]["error"]
    sentinels = [error_validation(control, reason) for control in controls]

    get_stream_writer()(
        {
            "type": "updates",
            "data": {"validation_results": sentinels},
        }
    )
    return {**failure, "validation_results": sentinels}


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

    # validation_results uses operator.add: invoke_validation_subagent already appended
    # every batch, so returning the accumulated list here would double every result.
    return {}


def _flatten_validations(raw_results) -> list[ControlValidation]:
    flattened: list[ControlValidation] = []
    for item in raw_results or []:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    return flattened


def reconcile_validation_results(state: ComplianceAgentState):
    """Left-join every requested control against what was actually validated.

    Controls go missing two ways: the model returns a short batch (truncation), and a
    cluster whose evidence subagent failed is never dispatched at all. A compliance report
    that silently omits a control is the worst available failure mode, so anything absent
    is backfilled as ERROR (the run failed on it) or NO_EVIDENCE (nothing came back).
    """
    produced = _flatten_validations(state.get("validation_results", []))
    seen = {
        normalize_regulation_id(getattr(item, "regulation_id", "")) for item in produced
    }

    failures_by_cluster: dict[str, str] = {}
    for failure in state.get("cluster_errors", []):
        failures_by_cluster.setdefault(
            failure.get("cluster_id"), failure.get("error", "unknown error")
        )

    backfilled: list[ControlValidation] = []
    for cluster_id, controls in (state.get("clusters", {}) or {}).items():
        for control in controls or []:
            key = normalize_regulation_id(control.get("regulation_id"))
            if key in seen:
                continue
            seen.add(key)
            cluster_error = failures_by_cluster.get(cluster_id)
            if cluster_error:
                backfilled.append(error_validation(control, cluster_error))
            else:
                backfilled.append(
                    no_evidence_validation(
                        control,
                        "The validator returned no result for this control, so it was "
                        "backfilled during reconciliation.",
                    )
                )

    writer = get_stream_writer()
    if backfilled:
        writer(
            {
                "type": "status",
                "message": f"Reconciled {len(backfilled)} control(s) missing from the validation output.",
            }
        )
    writer(
        {
            "type": "updates",
            "data": {"validation_results": produced + backfilled},
        }
    )

    # validation_results uses operator.add, so return only the additions.
    return {"validation_results": backfilled}
