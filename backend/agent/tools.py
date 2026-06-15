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


def think(
    evidence: str,
    code_snippets: list[str],
    finished: bool,
    fetches_remaining: int,
    tree_calls_remaining: int,
) -> dict:
    """
    Structured mid-loop checkpoint. Call this immediately after EVERY get_file_content call,
    before issuing any other tool call.

    Args:
        evidence: One or two factual sentences describing what this file contained
                or did not contain relative to the CURRENT control being investigated.
                Do not use compliant, non-compliant, violation, passes, fails,
                secure, insecure, adequate, inadequate.
        code_snippets: Exact verbatim code from the file relevant to the current control.
                        Preserve whitespace. Empty list if nothing relevant was found.
        finished: A boolean flag indicating whether the current control is ready to conclude.
        fetches_remaining: An integer indicating how many more file fetches are allowed before concluding.
        tree_calls_remaining: An integer indicating how many more repository tree calls are allowed before concluding.
    """
    # No-op server-side. Forces the model to externalize and structure
    # its working memory after each fetch before context grows further.
    return {
        "status": "logged",
        "snippets_captured": len(code_snippets),
        "tree_calls_remaining": tree_calls_remaining,
        "fetches_remaining": fetches_remaining,
    }
