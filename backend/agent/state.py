from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph.message import MessagesState
 

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
    evidence_items: list[EvidenceResult]

class ComplianceAgentState(TypedDict):
    # Input state
    framework: Annotated[str, "The compliance framework to be used."]
    category: Annotated[str, "The category of the compliance requirement."]
    source_code_category: Annotated[str, "The category to search for in the source code repository."]

    regulations: Annotated[
        list[dict], "The retrieved regulations relevant to the framework and category."
    ]
    policies: Annotated[
        list[dict], "The retrieved policies relevant to the framework and category."
    ]
    policy_excerpts: Annotated[
        list[dict], "The extracted excerpts from policies that are relevant to the regulations."
    ]
    policy_validation_results: Annotated[
        list[dict], "The results of validating policies against regulations."
    ]
    evidence_results: Annotated[
        list[EvidenceResult], "The processed evidence results that summarize the findings from the codebase search."
    ]