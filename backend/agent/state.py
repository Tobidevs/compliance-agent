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

class PolicyValidationResult(BaseModel):
    topic: str
    strength: Literal["explicit", "implicit", "absent"]
    excerpt: str | None = None
    policy_assertion: str


class PolicyValidationResults(BaseModel):
    results: list[PolicyValidationResult] = Field(default_factory=list)