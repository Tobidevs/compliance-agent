import json

from ..state import SubAgentInput


def _format_points_of_focus(raw) -> str:
    """Turn the raw pipe-delimited points_of_focus cell into a readable bullet list."""
    if not raw:
        return ""
    parts = [p.strip() for p in str(raw).split("|") if p.strip()]
    return "\n".join(f"      - {p}" for p in parts)


def _build_control_block(c: dict) -> str:
    block = (
        f"Regulation {c['regulation_id']}: {c['title']}\n"
        f"Requirement: {c['requirement']}"
    )
    points_of_focus = _format_points_of_focus(c.get("points_of_focus"))
    if points_of_focus:
        block += (
            "\nPoints of focus — search context, NOT a checklist. Together these describe "
            "what a complete implementation of this control looks like. Use them to guide "
            "WHAT you search for in a single unified search for this control; do not run a "
            "separate search per item:\n"
            f"{points_of_focus}"
        )
    return block


def _build_evidence_user_message(state: SubAgentInput) -> str:
    controls_block = "\n\n".join(
        _build_control_block(c) for c in state["controls"]
    )

    full_paths_block = "\n".join(f"  - {p}" for p in state["artifact_paths"])

    return f"""REPOSITORY: {state["repo_owner"]}/{state["repo_name"]}
    CLUSTER: {state["cluster_id"]}

    COMPLIANCE CONTROLS TO INVESTIGATE:
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
            "points_of_focus_coverage": [
                {"point_of_focus": p.point_of_focus, "coverage": p.coverage}
                for p in e.points_of_focus_coverage
            ],
            "files_searched": e.files_searched,
            "code_snippets": e.code_snippets,
            "description": e.description,
            "no_evidence_found": e.no_evidence_found,
        }
        for e in evidence_results
    ]

    return f"""Framework: {framework}
    Category: {category}
    Controls to validate: {control_count}

    ## Evidence results

    Each item below corresponds to one control for this subagent.
    Validate each control against its evidence. Use regulation_id as the sole
    identifier in your output — do not emit a separate control_id field.

    {json.dumps(evidence, indent=2)}

    Assess all {control_count} controls and return a validation result
    for each one.
    """
