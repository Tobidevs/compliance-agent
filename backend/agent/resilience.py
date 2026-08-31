"""Failure isolation for the graph's fan-out paths.

A `Send` target that raises aborts the whole compliance run, so both fan-outs degrade to
sentinel results instead. This module owns those sentinels, the error classification used
to build them, and the runtime knobs (LLM retries/timeouts, cluster concurrency cap) that
keep the fan-out from being the thing that fails in the first place.
"""

import asyncio
import os
import weakref
from json import JSONDecodeError

from dotenv import load_dotenv
from pydantic import ValidationError

from .state import ControlValidation, EvidenceResult, ValidationFinding

# Read before the constants below: this module is imported before nodes.py calls load_dotenv().
load_dotenv()

# Anthropic/OpenAI SDKs apply exponential backoff with jitter between these retries.
LLM_MAX_RETRIES = max(0, int(os.getenv("LLM_MAX_RETRIES", "5")))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
# Caps how many clusters hit the model concurrently; the graph would otherwise fan out all 12.
CLUSTER_CONCURRENCY = max(1, int(os.getenv("CLUSTER_CONCURRENCY", "5")))

# Malformed model output must degrade to a sentinel, never propagate out of a Send target.
DESERIALIZATION_ERRORS = (
    ValidationError,
    JSONDecodeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)

MAX_REASON_CHARS = 300

# One semaphore per event loop, weakly keyed so a finished loop does not leak.
_cluster_semaphores: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def cluster_slot() -> asyncio.Semaphore:
    """Concurrency gate shared by both fan-outs, bound lazily to the running loop."""
    loop = asyncio.get_running_loop()
    semaphore = _cluster_semaphores.get(loop)
    if semaphore is None:
        semaphore = asyncio.Semaphore(CLUSTER_CONCURRENCY)
        _cluster_semaphores[loop] = semaphore
    return semaphore


def format_error(error: BaseException) -> str:
    """Single-line, length-capped rendering of an exception for prompts and UI copy."""
    text = " ".join(str(error).split()).strip()
    label = type(error).__name__
    if not text:
        return label
    return f"{label}: {text[:MAX_REASON_CHARS]}"


def normalize_regulation_id(value) -> str:
    """Join key for control rosters: model output drifts in case and surrounding space."""
    return str(value or "").strip().casefold()


def _control_fields(control: dict) -> tuple[str, str, str]:
    return (
        str(control.get("regulation_id") or "unknown"),
        str(control.get("title") or "Untitled control"),
        str(control.get("requirement") or ""),
    )


def error_validation(control: dict, reason: str) -> ControlValidation:
    """Sentinel for a control the runtime failed to assess at all."""
    regulation_id, title, _ = _control_fields(control)
    return ControlValidation(
        regulation_id=regulation_id,
        title=title,
        status="ERROR",
        severity=None,
        confidence=0.0,
        confidence_label="Inconclusive",
        findings=[
            ValidationFinding(
                type="gap",
                description="This control could not be assessed because the automated check failed.",
                evidence_ref=None,
                reasoning=reason,
            )
        ],
        points_of_focus=[],
        overall_reasoning=(
            "The compliance run did not produce a verdict for this control: "
            f"{reason}. This is a tooling failure, not a finding about the repository — "
            "re-run the check before treating it as a gap."
        ),
    )


def no_evidence_validation(control: dict, reason: str) -> ControlValidation:
    """Sentinel for a requested control the validator simply never returned."""
    regulation_id, title, _ = _control_fields(control)
    return ControlValidation(
        regulation_id=regulation_id,
        title=title,
        status="NO_EVIDENCE",
        severity=None,
        confidence=0.0,
        confidence_label="Inconclusive",
        findings=[
            ValidationFinding(
                type="gap",
                description="No evidence retrieved for this control.",
                evidence_ref=None,
                reasoning=reason,
            )
        ],
        points_of_focus=[],
        overall_reasoning=(
            "No repository evidence was returned for this control, so no verdict could be "
            "reached. It is reported as no evidence rather than omitted from the report."
        ),
    )


def degraded_evidence_result(control: dict, reason: str) -> EvidenceResult:
    """Placeholder evidence so a control is never invisible to the validator."""
    regulation_id, title, requirement = _control_fields(control)
    return EvidenceResult(
        regulation_id=regulation_id,
        title=title,
        requirement=requirement,
        files_searched=[],
        code_snippets=[],
        description=f"Evidence gathering did not complete for this control: {reason}",
        no_evidence_found=True,
        points_of_focus_coverage=[],
    )
