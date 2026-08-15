"""HIGH-2 regression: a return shipment with more than one warehouse item.

Every other test file in this suite exercises exactly one item. This file
is the committed evidence that the engine's per-item loop in reconciler.py
actually keeps evidence, conflicts, resolved fields, allocations, and rules
scoped to the item they belong to, and that mixed outcomes across items are
returned as-is rather than collapsed into one shipment-wide disposition.
"""

from __future__ import annotations

import json
from pathlib import Path

from returnproof.enums import Route
from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_multi_item_report():
    raw = json.loads((EXAMPLES_DIR / "multi_item_return.json").read_text())
    shipment = parse_shipment(raw)
    return reconcile(shipment)


def test_multi_item_shipment_returns_one_record_per_item():
    report = _load_multi_item_report()
    assert report.summary.item_count == 3
    assert [item.item_id for item in report.items] == [
        "CEREAL-12-1",
        "YOGURT-22-1",
        "SAUCE-99-1",
    ]


def test_multi_item_outcomes_are_not_collapsed_into_one_disposition():
    """Item A resolves clean, item B is a safety override, item C is
    genuinely unresolved, all three routes appear in the same report.
    """
    report = _load_multi_item_report()
    routes_by_item = {
        item.item_id: {a.route for a in item.allocations} for item in report.items
    }
    assert routes_by_item["CEREAL-12-1"] == {Route.RESTOCK}
    assert routes_by_item["YOGURT-22-1"] == {Route.SCRAP}
    assert routes_by_item["SAUCE-99-1"] == {Route.QUARANTINE}


def test_multi_item_conservation_is_checked_independently_per_item():
    """R006 must pass per item, checking only the shipment-wide total would
    hide a broken item whose over- and under-allocation happen to cancel out.
    """
    report = _load_multi_item_report()
    expected_quantity = {"CEREAL-12-1": 20, "YOGURT-22-1": 8, "SAUCE-99-1": 12}

    for item in report.items:
        assert len(item.invariants) == 1
        check = item.invariants[0]
        assert check.passed is True
        allocated = sum(a.quantity for a in item.allocations)
        assert allocated == expected_quantity[item.item_id]

    assert report.summary.invariants_passed is True


def test_multi_item_evidence_and_conflicts_stay_item_scoped():
    """No claim ID or conflict belonging to one item may reference, or be
    influenced by, another item's data, even though all three items share
    the same shipment and were reconciled in the same call.
    """
    report = _load_multi_item_report()

    for item in report.items:
        for claim in item.evidence:
            assert claim.item_id == item.item_id
            assert claim.claim_id.startswith(f"{item.item_id}:")
        for conflict in item.conflicts:
            assert conflict.item_id == item.item_id
            for claim_id in conflict.claim_ids:
                assert claim_id.startswith(f"{item.item_id}:")

    # only YOGURT-22-1 (safety override) and SAUCE-99-1 (batch mismatch)
    # have conflicts, CEREAL-12-1 resolves cleanly
    conflict_counts = {item.item_id: len(item.conflicts) for item in report.items}
    assert conflict_counts["CEREAL-12-1"] == 0
    assert conflict_counts["YOGURT-22-1"] == 1
    assert conflict_counts["SAUCE-99-1"] == 1


def test_multi_item_supplier_events_do_not_bleed_across_items():
    """Each item's supplier evidence must come only from that item's own
    supplier_events entries, keyed by item_id, never by array position or
    another item's event.
    """
    report = _load_multi_item_report()

    by_item = {item.item_id: item for item in report.items}
    cereal_supplier_claims = [
        c for c in by_item["CEREAL-12-1"].evidence if c.source == "SUPPLIER"
    ]
    yogurt_supplier_claims = [
        c for c in by_item["YOGURT-22-1"].evidence if c.source == "SUPPLIER"
    ]
    sauce_supplier_claims = [
        c for c in by_item["SAUCE-99-1"].evidence if c.source == "SUPPLIER"
    ]

    assert cereal_supplier_claims and all(
        c.source_reference == "evt-cereal-1" for c in cereal_supplier_claims
    )
    assert yogurt_supplier_claims and all(
        c.source_reference == "evt-yogurt-1" for c in yogurt_supplier_claims
    )
    assert sauce_supplier_claims and all(
        c.source_reference == "evt-sauce-1" for c in sauce_supplier_claims
    )


def test_multi_item_rules_applied_are_specific_to_each_item():
    report = _load_multi_item_report()
    by_item = {item.item_id: item for item in report.items}

    # R005 (physical safety override) only fired for the unsafe-damage item.
    assert "R005" in by_item["YOGURT-22-1"].rules_applied
    assert "R005" not in by_item["CEREAL-12-1"].rules_applied
    assert "R005" not in by_item["SAUCE-99-1"].rules_applied

    # R007 (uncertainty escalation) only fired for the unresolved-identity item.
    assert "R007" in by_item["SAUCE-99-1"].rules_applied
    assert "R007" not in by_item["CEREAL-12-1"].rules_applied


def test_multi_item_commercial_credit_stays_independent_per_item():
    """R008: the credit figures are independent per item and independent of
    physical routing within each item (YOGURT-22-1 is fully credited despite
    being scrapped).
    """
    report = _load_multi_item_report()
    by_item = {item.item_id: item for item in report.items}

    assert by_item["CEREAL-12-1"].commercial_decision.credit_quantity == 0
    assert by_item["YOGURT-22-1"].commercial_decision.credit_quantity == 8
    assert by_item["SAUCE-99-1"].commercial_decision.credit_quantity == 0
