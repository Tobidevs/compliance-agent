

CLUSTERS: dict[str, dict] = {
    "access_auth": {
        "prefixes": ["CC6"],
        "path_keywords": [
            "auth", "session", "login", "middleware", "jwt", "token",
            "permission", "rbac", "oauth", "guard", "credential", "callback",
        ],
    },
    "change_management": {
        "prefixes": ["CC8"],
        "path_keywords": [
            "deploy", "pipeline", "ci", "migration", "schema", "config",
            "release", "dockerfile", "workflow", "action",
        ],
    },
    "monitoring_logging": {
        "prefixes": ["CC7", "CC4"],
        "path_keywords": [
            "log", "monitor", "alert", "audit", "trace", "error",
            "event", "sentry", "datadog", "observe",
        ],
    },
    "data_protection": {
        "prefixes": ["A1", "CC9"],
        "path_keywords": [
            "encrypt", "crypto", "tls", "backup", "retention",
            "pii", "data", "storage", "vault", "kms",
        ],
    },
}

PRIORITY_PATH_CAP = 12  # max priority paths per cluster to prevent context bloat


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
        

        # assigned = False
        # for cluster_id, cluster_def in CLUSTERS.items():
        #     if any(reg_id.startswith(prefix) for prefix in cluster_def["prefixes"]):
        #         result[cluster_id].append(control)
        #         assigned = True
        #         break

        # if not assigned:
        #     result["misc"].append(control)

    return result

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