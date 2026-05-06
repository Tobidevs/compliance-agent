from typing import Annotated, TypedDict, Literal
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph.message import MessagesState
import operator


class PolicyExtractionResult(BaseModel):
    title: str = Field(description="The title of the policy claim.")
    regulation_id: str = Field(
        description="The ID of the regulation this claim addresses."
    )
    regulation_requirement: str = Field(
        description="The specific requirement from the regulation that this claim addresses."
    )
    excerpt: str | None = Field(
        description="The verbatim sentences from the policy that best matches the regulation requirement."
    )


class PolicyExtractionResults(BaseModel):
    results: list[PolicyExtractionResult] = Field(default_factory=list)


class PolicyValidationResult(BaseModel):
    title: str = Field(description="The title of the policy claim.")
    regulation_id: str = Field(
        description="The ID of the regulation this claim addresses."
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Compliance coverage score: 0.0=none, 0.3=marginal, 0.7=partial, 1.0=full.",
    )
    coverage: Literal["none", "marginal", "partial", "full"] = Field(
        description="Categorical coverage label corresponding to the score."
    )
    rationale: str = Field(
        description="Concise explanation of the score: what the excerpt satisfies, what it misses, and what would be needed for full coverage."
    )


class PolicyValidationResults(BaseModel):
    results: list[PolicyValidationResult] = Field(default_factory=list)


class EvidenceResult(BaseModel):
    regulation_id: str
    title: str
    requirement: str
    files_searched: list[str]
    code_snippets: list[str]
    description: str
    no_evidence_found: bool


class EvidenceSubAgentState(MessagesState):
    regulation_id: str
    title: str
    requirement: str
    evidence_results: list[EvidenceResult]
    evidence_items: list[EvidenceResult]


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
    policies: Annotated[
        list[dict], "The retrieved policies relevant to the framework and category."
    ]
    policy_excerpts: Annotated[
        list[dict],
        "The extracted excerpts from policies that are relevant to the regulations.",
    ]
    policy_validation_results: Annotated[
        list[dict], "The results of validating policies against regulations."
    ]
    evidence_items: Annotated[list[dict], operator.add]

    repo_owner: Annotated[str, "GitHub repository owner."]
    repo_name: Annotated[str, "GitHub repository name."]

    artifact_paths: Annotated[
        list[str], "In-scope source code file paths from the repository."
    ]
    clusters: Annotated[
        dict[str, list[dict]],
        "Mapping of cluster IDs to their assigned controls. Each control includes regulation_id, title, requirement.",
    ]

    extraction_evidence: Annotated[list[dict], operator.add]
    extraction_errors: Annotated[list[str], operator.add]


class SubAgentInput(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    cluster_id: str
    controls: list[dict]  # [{regulation_id, title, requirement, excerpt}]
    artifact_paths: list[str]  # full artifact list (search fallback)
    priority_paths: list[str]  # pre-filtered high-relevance paths for this cluster
    repo_owner: str
    repo_name: str
    evidence_results: list[EvidenceResult]
