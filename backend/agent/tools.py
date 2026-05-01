from backend.agent.state import EvidenceItem
from langchain.tools import tool

@tool
def conclude_evidence(
    files_searched: list[str],
    code_snippets: list[str],
    description: str,
    no_evidence_found: bool,
):
    return "concluded evidence"
