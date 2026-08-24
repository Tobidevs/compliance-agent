
from .state import EvidenceResult

def group_controls_into_clusters(
    regulations: list[dict],
) -> dict[str, list[dict]]:
    """
    Groups controls into clusters keyed by their `category` metadata field.
    Controls with a missing or blank category fall into 'misc' so nothing is dropped.
    """
    result: dict[str, list[dict]] = {}

    for reg in regulations:
        reg_id = reg.get("control_id", "")
        control = {
            "regulation_id": reg_id,
            "title": reg.get("title", ""),
            "requirement": reg.get("requirement") or reg.get("criterion_text", ""),
            "points_of_focus": reg.get("points_of_focus", ""),
        }
        # Blank/whitespace categories would otherwise create an unnamed "" cluster.
        cluster_id = str(reg.get("category") or "").strip() or "misc"
        result.setdefault(cluster_id, []).append(control)

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
