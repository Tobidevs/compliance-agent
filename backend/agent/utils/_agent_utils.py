from ..state import SubAgentInput


def _build_user_message(state: SubAgentInput) -> str:
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
