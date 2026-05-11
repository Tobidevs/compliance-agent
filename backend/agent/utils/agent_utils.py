from ..state import SubAgentInput


def _build_evidence_user_message(state: SubAgentInput) -> str:
    controls_block = "\n\n".join(
        [
            f"Regulation {c['regulation_id']}: {c['title']}\n"
            f"Requirement: {c['requirement']}\n"
            for c in state["controls"]
        ]
    )

    full_paths_block = "\n".join(f"  - {p}" for p in state["artifact_paths"])

    return f"""REPOSITORY: {state["repo_owner"]}/{state["repo_name"]}
    CLUSTER: {state["cluster_id"]}

    SOC 2 CONTROLS TO INVESTIGATE:
    {controls_block}

    FULL ARTIFACT PATH LIST — root directory files and folders in the repo.
    {full_paths_block}
    """.strip()

def _build_validation_user_message(state: SubAgentInput) -> str:
    framework = state.get("framework", "N/A")
    category = state.get("category", "N/A")
    control_count = len(state.get("controls", [])) 
    evidence_results = state.get("evidence_items", [])
    evidence = [
        {
            "regulation_id": e.regulation_id,
            "title": e.title,
            "requirement": e.requirement,
            "files_searched": e.files_searched,
            "code_snippets": e.code_snippets,
            "description": e.description,
            "no_evidence_found": e.no_evidence_found,
        } for e in evidence_results
    ]
    
    
    return f"""Framework: {framework}
    Category: {category}
    Controls to validate: {control_count}

    ## Evidence results

    Each item below corresponds to one control for this subagent.
    Validate each control against its evidence. Use regulation_id as the sole
    identifier in your output — do not emit a separate control_id field.

    {evidence}

    Assess all {control_count} controls and return a validation result
    for each one.
    """