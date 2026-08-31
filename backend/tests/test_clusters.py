"""Phase 0.5 / 5.1 — cluster grouping and evidence merge."""

from conftest import make_evidence, make_regulation

from agent.clusters import group_controls_into_clusters, update_clusters_with_evidence


def test_groups_by_category_not_by_id_prefix():
    clusters = group_controls_into_clusters(
        [
            make_regulation("CC6.1", category="Logical and Physical Access Controls"),
            make_regulation("CC7.2", category="System Operations"),
            make_regulation("A1.1", category="Logical and Physical Access Controls"),
        ]
    )

    assert set(clusters) == {"Logical and Physical Access Controls", "System Operations"}
    assert [c["regulation_id"] for c in clusters["Logical and Physical Access Controls"]] == [
        "CC6.1",
        "A1.1",
    ]


def test_blank_and_missing_categories_both_land_in_misc():
    # An empty-string category used to create an unnamed "" cluster, not misc.
    regulations = [
        make_regulation("CC1.1", category=""),
        make_regulation("CC1.2", category="   "),
        make_regulation("CC1.3"),
    ]
    regulations[2].pop("category")

    clusters = group_controls_into_clusters(regulations)

    assert set(clusters) == {"misc"}
    assert len(clusters["misc"]) == 3


def test_points_of_focus_survives_grouping():
    clusters = group_controls_into_clusters([make_regulation("CC6.1")])
    assert clusters["System Operations"][0]["points_of_focus"] == "focus a|focus b"


def test_requirement_falls_back_to_criterion_text():
    record = make_regulation("CC6.1")
    record.pop("requirement")
    record["criterion_text"] = "v3 field name"

    clusters = group_controls_into_clusters([record])

    assert clusters["System Operations"][0]["requirement"] == "v3 field name"


def test_update_clusters_with_evidence_matches_on_regulation_id():
    clusters = group_controls_into_clusters(
        [make_regulation("CC6.1"), make_regulation("CC6.2")]
    )

    merged = update_clusters_with_evidence(clusters, [make_evidence("CC6.1")])

    controls = {c["regulation_id"]: c for c in merged["System Operations"]}
    assert controls["CC6.1"]["evidence"]["files_searched"] == ["src/middleware.ts"]
    # An unmatched control must stay evidence-free rather than borrow a neighbour's.
    assert "evidence" not in controls["CC6.2"]


def test_update_clusters_with_evidence_ignores_unknown_ids():
    clusters = group_controls_into_clusters([make_regulation("CC6.1")])

    merged = update_clusters_with_evidence(clusters, [make_evidence("NOT-A-CONTROL")])

    assert "evidence" not in merged["System Operations"][0]
