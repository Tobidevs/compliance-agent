from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field


class ComplianceAgentState(TypedDict):
    # Input state
    framework: Annotated[str, "The compliance framework to be used."]
    category: Annotated[str, "The category of the compliance requirement."]

    regulations: Annotated[
        list[dict], "The retrieved regulations relevant to the framework and category."
    ]
    policies: Annotated[
        list[dict], "The retrieved policies relevant to the framework and category."
    ]
    policy_validation_results: Annotated[
        list[dict], "The results of validating policies against regulations."
    ]

class PolicyExtractionResult(BaseModel):
    title: str = Field(description="The title of the policy claim.")
    regulation_id: str = Field(description="The ID of the regulation this claim addresses.")
    regulation_requirement: str = Field(description="The specific requirement from the regulation that this claim addresses.")
    excerpt: str | None = Field(description="The verbatim sentences from the policy that best matches the regulation requirement.")


class PolicyExtractionResults(BaseModel):
    results: list[PolicyExtractionResult] = Field(default_factory=list)
    

class PolicyValidationResult(BaseModel):
    title: str = Field(description="The title of the policy claim.")
    regulation_id: str = Field(description="The ID of the regulation this claim addresses.")
    score: float = Field(ge=0.0, le=1.0, description="Compliance coverage score: 0.0=none, 0.3=marginal, 0.7=partial, 1.0=full.")
    coverage: Literal["none", "marginal", "partial", "full"] = Field(description="Categorical coverage label corresponding to the score.")
    rationale: str = Field(description="Concise explanation of the score: what the excerpt satisfies, what it misses, and what would be needed for full coverage.")

class PolicyValidationResults(BaseModel):
    results: list[PolicyValidationResult] = Field(default_factory=list)