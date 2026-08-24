from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .state import EvidenceResult


def conclude_evidence(evidence_result: EvidenceResult):
    """Call this after completing evidence gathering for one control. This records that control's evidence result, then you should continue to the next assigned control."""

    if isinstance(evidence_result, EvidenceResult):
        normalized_result = evidence_result.model_dump()
    else:
        normalized_result = evidence_result

    return {"evidence_result": normalized_result}


def finished_gathering_evidence():
    """Call this only after every assigned control has been completed with conclude_evidence."""

    return {"status": "finished"}


@tool("think")
def think(
    evidence: str,
    code_snippets: list[str],
    finished: bool,
    state: Annotated[dict, InjectedState],
) -> dict:
    """
    Structured mid-loop checkpoint. Call this immediately after EVERY get_file_content call,
    before issuing any other tool call. Returns your remaining tool budget, which is tracked
    by the runtime — you do not report it.

    Args:
        evidence: One or two factual sentences describing what this file contained
                or did not contain relative to the CURRENT control being investigated.
                Do not use compliant, non-compliant, violation, passes, fails,
                secure, insecure, adequate, inadequate.
        code_snippets: Exact verbatim code from the file relevant to the current control.
                        Preserve whitespace. Empty list if nothing relevant was found.
        finished: A boolean flag indicating whether the current control is ready to conclude.
    """
    # Forces the model to externalize its working memory after each fetch, and is the
    # channel by which the runtime reports the authoritative remaining budget back.
    ledger = state.get("budget")
    if ledger is None:
        return {"status": "logged", "snippets_captured": len(code_snippets)}

    return {
        "status": "logged",
        "snippets_captured": len(code_snippets),
        "current_control": ledger.current_control_id,
        "fetches_remaining_this_control": ledger.control_remaining("fetch"),
        "tree_calls_remaining_this_control": ledger.control_remaining("tree"),
        "fetches_remaining_this_cluster": ledger.cluster_remaining("fetch"),
        "tree_calls_remaining_this_cluster": ledger.cluster_remaining("tree"),
    }
