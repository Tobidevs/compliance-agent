"""Phase 0.1 / 2.4 — 5.6 invariant 1, the property that makes a report trustworthy.

`len(validation_results)` must equal the requested control count on every run. That is
enforced by an interaction across `_align_validations`, both dispatch fall-throughs and
`reconcile_validation_results`, so it regresses silently: a diff review of any one of them
looks fine. Every path that can drop a control is covered here.

All of these nodes call `get_stream_writer()`; the autouse `stream_events` fixture patches
it, otherwise they raise RuntimeError before running.
"""

from conftest import make_control, make_validation

from agent.nodes import (
    _align_validations,
    combine_validation_results,
    reconcile_validation_results,
)


def roster(*specs) -> dict[str, list[dict]]:
    """Build a clusters dict: roster(("System Operations", ["CC7.1", "CC7.2"]), ...)."""
    return {
        cluster_id: [make_control(rid, category=cluster_id) for rid in ids]
        for cluster_id, ids in specs
    }


def requested_count(clusters: dict[str, list[dict]]) -> int:
    return sum(len(controls) for controls in clusters.values())


def final_results(state: dict) -> list:
    """Apply the reducer the way the graph does: produced + whatever reconciliation adds."""
    added = reconcile_validation_results(state).get("validation_results", [])
    return list(state.get("validation_results", [])) + list(added)


# ---------------------------------------------------------------------------
# Phase 0.1 — the reducer must not double-append
# ---------------------------------------------------------------------------
def test_combine_validation_results_returns_no_additions():
    clusters = roster(("System Operations", ["CC7.1", "CC7.2"]))
    produced = [make_validation("CC7.1"), make_validation("CC7.2")]

    update = combine_validation_results(
        {"clusters": clusters, "validation_results": produced}
    )

    # validation_results uses operator.add; returning the accumulated list here would
    # append every result a second time.
    assert update == {}


def test_combine_validation_results_still_streams_the_flattened_set(stream_events):
    produced = [make_validation("CC7.1")]
    combine_validation_results({"clusters": {}, "validation_results": produced})

    updates = [e for e in stream_events if e.get("type") == "updates"]
    assert updates and updates[-1]["data"]["validation_results"] == produced


# ---------------------------------------------------------------------------
# 5.6 invariant 1 — the count always matches the requested roster
# ---------------------------------------------------------------------------
def test_short_batch_is_backfilled_as_no_evidence():
    clusters = roster(("System Operations", ["CC7.1", "CC7.2", "CC7.3"]))
    state = {"clusters": clusters, "validation_results": [make_validation("CC7.1")]}

    results = final_results(state)

    assert len(results) == requested_count(clusters)
    by_id = {r.regulation_id: r for r in results}
    assert by_id["CC7.2"].status == "NO_EVIDENCE"
    assert by_id["CC7.3"].status == "NO_EVIDENCE"


def test_failed_cluster_is_backfilled_as_error_not_no_evidence():
    clusters = roster(
        ("System Operations", ["CC7.1"]),
        ("Availability", ["A1.1", "A1.2"]),
    )
    state = {
        "clusters": clusters,
        "validation_results": [make_validation("CC7.1")],
        "cluster_errors": [
            {"cluster_id": "Availability", "stage": "evidence gathering",
             "error": "GraphRecursionError: limit reached"}
        ],
    }

    results = final_results(state)

    assert len(results) == requested_count(clusters)
    by_id = {r.regulation_id: r for r in results}
    # ERROR means "we failed to assess this", which is not the same claim as "no evidence".
    assert by_id["A1.1"].status == "ERROR"
    assert by_id["A1.2"].status == "ERROR"
    assert "GraphRecursionError" in by_id["A1.1"].findings[0].reasoning


def test_every_cluster_failing_still_produces_a_full_roster():
    clusters = roster(
        ("System Operations", ["CC7.1", "CC7.2"]),
        ("Availability", ["A1.1"]),
    )
    state = {
        "clusters": clusters,
        "validation_results": [],
        "cluster_errors": [
            {"cluster_id": "System Operations", "stage": "validation", "error": "boom"},
            {"cluster_id": "Availability", "stage": "validation", "error": "boom"},
        ],
    }

    results = final_results(state)

    assert len(results) == requested_count(clusters) == 3
    assert {r.status for r in results} == {"ERROR"}


def test_a_complete_batch_needs_no_backfill():
    clusters = roster(("System Operations", ["CC7.1", "CC7.2"]))
    state = {
        "clusters": clusters,
        "validation_results": [make_validation("CC7.1"), make_validation("CC7.2")],
    }

    assert reconcile_validation_results(state)["validation_results"] == []
    assert len(final_results(state)) == requested_count(clusters)


def test_reconciliation_joins_across_case_and_whitespace_drift():
    clusters = roster(("System Operations", ["CC7.1"]))
    state = {"clusters": clusters, "validation_results": [make_validation(" cc7.1 ")]}

    # Already covered by the roster: a drifted id must not produce a duplicate row.
    assert reconcile_validation_results(state)["validation_results"] == []


def test_nested_batches_are_flattened_before_the_join():
    clusters = roster(("System Operations", ["CC7.1", "CC7.2"]))
    state = {
        "clusters": clusters,
        "validation_results": [[make_validation("CC7.1"), make_validation("CC7.2")]],
    }

    assert reconcile_validation_results(state)["validation_results"] == []


def test_reconciliation_announces_what_it_backfilled(stream_events):
    clusters = roster(("System Operations", ["CC7.1", "CC7.2"]))
    reconcile_validation_results(
        {"clusters": clusters, "validation_results": [make_validation("CC7.1")]}
    )

    statuses = [e for e in stream_events if e.get("type") == "status"]
    assert any("Reconciled 1 control" in e["message"] for e in statuses)


# ---------------------------------------------------------------------------
# _align_validations — keeps validation_results a strict subset of the roster
# ---------------------------------------------------------------------------
def test_align_drops_ids_the_model_invented():
    controls = [make_control("CC7.1")]
    aligned = _align_validations(
        [make_validation("CC7.1"), make_validation("TOTALLY-MADE-UP")], controls
    )

    assert [v.regulation_id for v in aligned] == ["CC7.1"]


def test_align_drops_duplicate_verdicts_for_one_control():
    controls = [make_control("CC7.1")]
    aligned = _align_validations(
        [make_validation("CC7.1", "PASS"), make_validation("CC7.1", "FAIL")], controls
    )

    assert len(aligned) == 1
    # First verdict wins; a duplicate must not silently overwrite it.
    assert aligned[0].status == "PASS"


def test_align_snaps_case_drift_back_to_the_canonical_id():
    controls = [make_control("CC7.1")]
    aligned = _align_validations([make_validation("cc7.1")], controls)

    # Without the snap, reconciliation's join misses and the control is backfilled twice.
    assert [v.regulation_id for v in aligned] == ["CC7.1"]


def test_align_returns_controls_in_the_requested_order():
    controls = [make_control("CC7.1"), make_control("CC7.2"), make_control("CC7.3")]
    aligned = _align_validations(
        [make_validation("CC7.3"), make_validation("CC7.1")], controls
    )

    assert [v.regulation_id for v in aligned] == ["CC7.1", "CC7.3"]


def test_align_then_reconcile_together_hit_the_count_exactly():
    """The invariant is a property of the interaction, not of either function alone."""
    clusters = roster(("System Operations", ["CC7.1", "CC7.2", "CC7.3"]))
    controls = clusters["System Operations"]

    # A realistically bad batch: one drifted id, one duplicate, one hallucination, one miss.
    raw = [
        make_validation("cc7.1"),
        make_validation("CC7.1", "FAIL"),
        make_validation("GHOST-1"),
        make_validation("CC7.2"),
    ]
    produced = _align_validations(raw, controls)

    results = final_results({"clusters": clusters, "validation_results": produced})

    assert len(results) == requested_count(clusters) == 3
    assert sorted(r.regulation_id for r in results) == ["CC7.1", "CC7.2", "CC7.3"]
