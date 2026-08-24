from typing import Annotated, TypedDict, Literal
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator

from .budget import BudgetLedger


class PointOfFocusCoverage(BaseModel):
    point_of_focus: str = Field(
        description="The control's point of focus being assessed."
    )
    coverage: Literal["satisfied", "partial", "absent"] = Field(
        description="Whether gathered evidence shows this point of focus is satisfied, partially covered, or absent."
    )


class EvidenceResult(BaseModel):
    regulation_id: str
    title: str
    requirement: str
    files_searched: list[str]
    code_snippets: list[str]
    description: str
    no_evidence_found: bool
    points_of_focus_coverage: list[PointOfFocusCoverage] = Field(
        description="One entry per point of focus for this control. Empty if the control lists no points of focus."
    )


class EvidenceRef(BaseModel):
    snippet: str = Field(
        description=(
            "Verbatim excerpt from a code_snippets entry, max 200 characters. "
            "Do not paraphrase."
        )
    )


class ValidationFinding(BaseModel):
    type: Literal["violation", "pass", "gap"]
    description: str = Field(
        description="Specific finding tied directly to the evidence."
    )
    evidence_ref: EvidenceRef | None = Field(
        default=None,
        description=(
            "Required for 'pass' and 'violation' findings. "
            "Null only for NO_EVIDENCE gap findings."
        ),
    )
    reasoning: str = Field(
        default="", description="Step-by-step reasoning for this individual finding."
    )


class PointOfFocusAssessment(BaseModel):
    point_of_focus: str = Field(
        description="The point-of-focus statement being assessed, verbatim."
    )
    status: Literal["satisfied", "partial", "absent", "not_applicable"] = Field(
        description=(
            "Validator's judged coverage for this point of focus: satisfied, partial, "
            "absent, or not_applicable when it is enforced outside the codebase "
            "(infrastructure, DevOps, or a third-party service) so its absence from "
            "source is not a deficiency."
        )
    )
    assessment: str = Field(
        description="Concise, evidence-grounded reason for the assigned status."
    )


class ControlValidation(BaseModel):
    regulation_id: str = Field(
        description="Regulation ID from the EvidenceResult (e.g. 'CC6.1.1')."
    )
    title: str = Field(description="Control title from the EvidenceResult.")
    # ERROR is set by the runtime only (failed or unparseable assessment), never by the model.
    status: Literal["PASS", "FAIL", "PARTIAL", "NO_EVIDENCE", "ERROR"]
    severity: Literal["critical", "high", "medium", "low"] | None = Field(
        description=(
            "Null for PASS, NO_EVIDENCE and ERROR. " "Required for FAIL and PARTIAL."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Calibrated confidence float between 0.0 and 1.0.",
    )
    confidence_label: Literal["High", "Medium", "Low", "Inconclusive"]
    findings: list[ValidationFinding] = Field(
        min_length=1,
        description="At least one finding required per control.",
    )
    points_of_focus: list[PointOfFocusAssessment] = Field(
        description="One assessment per point of focus for this control. Empty if the control lists none.",
    )
    overall_reasoning: str = Field(
        description=(
            "Client-facing plain-language summary of the final status. "
            "Explain what was checked, what was found, and the main gap or support."
        )
    )


class ComplianceAgentState(TypedDict):
    # Input state
    framework: Annotated[str, "The compliance framework to be used."]
    category: Annotated[str, "The category of the compliance requirement."]
    source_code_categories: Annotated[
        list[str], "The categories to search for in the source code repository."
    ]

    regulations: Annotated[
        list[dict], "The retrieved regulations relevant to the framework and category."
    ]
    evidence_items: Annotated[list[EvidenceResult], operator.add]
    validation_results: Annotated[list[ControlValidation], operator.add]

    repo_owner: Annotated[str, "GitHub repository owner."]
    repo_name: Annotated[str, "GitHub repository name."]

    artifact_paths: Annotated[
        list[str], "In-scope source code file paths from the repository."
    ]
    clusters: Annotated[
        dict[str, list[dict]],
        "Mapping of cluster IDs to their assigned controls. Each control includes regulation_id, title, requirement.",
    ]

    # Written concurrently by failing Send branches, so it needs an additive reducer.
    cluster_errors: Annotated[list[dict], operator.add]


class SubAgentInput(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    cluster_id: str
    controls: list[dict]  # [{regulation_id, title, requirement, excerpt}]
    artifact_paths: list[str]  # full artifact list (search fallback)
    repo_owner: str
    repo_name: str
    # Mutable, passed by reference: every budgeted tool call in the run debits this object.
    budget: BudgetLedger
    evidence_results: Annotated[list[EvidenceResult], operator.add]


class ValidationBatch(BaseModel):
    validations: list[ControlValidation] = Field(
        description="One ControlValidation per EvidenceResult in the input batch."
    )
