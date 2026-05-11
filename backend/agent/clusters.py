
from .state import EvidenceResult


def group_controls_into_clusters(
    regulations: list[dict],
) -> dict[str, list[dict]]:
    """
    Groups regulation + excerpt pairs into predefined clusters by control ID prefix.
    Unmatched controls fall into 'misc' so nothing is silently dropped.
    """
    result = {}

    for reg in regulations:
        reg_id = reg.get("control_id", "")
        control = {
            "regulation_id": reg_id,
            "title": reg.get("title", ""),
            "requirement": reg.get("requirement", ""),
        }
        result[reg.get("category", "misc")] = result.get(reg.get("category", "misc"), []) + [control]
        
    return result

def update_clusters_with_evidence(
    clusters: dict[str, list[dict]],
    evidence_items: list[EvidenceResult],
) -> dict[str, list[dict]]:
    """
    Merges retrieved evidence items into the existing cluster structure by matching regulation_id.
    This enriches the cluster data for downstream sub-agents without changing the overall organization.
    """
    for cluster_id, controls in clusters.items():
        for control in controls:
            reg_id = control["regulation_id"]
            matching_evidence = next((e for e in evidence_items if e.regulation_id == reg_id), None)
            if matching_evidence:
                control["evidence"] = {
                    "files_searched": matching_evidence.files_searched,
                    "code_snippets": matching_evidence.code_snippets,
                    "description": matching_evidence.description,
                    "no_evidence_found": matching_evidence.no_evidence_found,
                }
    return clusters

    


def filter_paths_for_cluster(artifact_paths: list[str], keywords: list[str]) -> list[str]:
    """
    Scores each artifact path by keyword overlap with the cluster domain.
    Returns top-N ranked paths. Falls back to first 10 paths if no matches.
    This keeps each sub-agent's 'where to look first' list tight and relevant.
    """
    scored = []
    for path in artifact_paths:
        path_lower = path.lower()
        score = sum(1 for kw in keywords if kw in path_lower)
        if score > 0:
            scored.append((score, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    priority = [path for _, path in scored[:PRIORITY_PATH_CAP]]
    return priority if priority else artifact_paths[:10]