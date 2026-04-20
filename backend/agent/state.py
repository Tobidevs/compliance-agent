
from typing import Annotated, TypedDict


class ComplianceAgentState(TypedDict):
    # Input state
    framework: Annotated[str, "The compliance framework to be used."]
    category: Annotated[str, "The category of the compliance requirement."]
    
    regulations: Annotated[list[dict], "The retrieved regulations relevant to the framework and category."]
    policies: Annotated[list[dict], "The retrieved policies relevant to the framework and category."]
    
    
    
    
    