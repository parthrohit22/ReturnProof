import json
from pathlib import Path

from returnproof.enums import EvidenceStatus, Route
from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "compound_failure.json"


def _load_shipment():
    raw = json.loads(EXAMPLE_PATH.read_text())
    return parse_shipment(raw)


def test_compound_failure_resolves_batch_and_bucket():
    report = reconcile(_load_shipment())
    record = report.items[0]

    assert record.resolved.batch_code == "BA1902"
    assert record.resolved.best_before_bucket == "2026-10"


def test_compound_failure_allocation_quantities():
    report = reconcile(_load_shipment())
    record = report.items[0]

    routes = {a.route: a.quantity for a in record.allocations}
    assert routes[Route.SCRAP] == 6
    assert routes[Route.RESTOCK] == 18


def test_compound_failure_applies_the_expected_rules():
    report = reconcile(_load_shipment())
    record = report.items[0]

    for rule in ("R002", "R003", "R004", "R005"):
        assert rule in record.rules_applied, f"expected {rule} in {record.rules_applied}"


def test_compound_failure_evidence_statuses():
    report = reconcile(_load_shipment())
    record = report.items[0]

    warehouse_batch_claim = next(
        c for c in record.evidence if c.claim_id == "MILK-01-1:warehouse:batch_code"
    )
    assert warehouse_batch_claim.status == EvidenceStatus.CORRUPTED

    stale_event_claims = [c for c in record.evidence if c.source_reference == "evt-1"]
    assert stale_event_claims and all(c.status == EvidenceStatus.SUPERSEDED for c in stale_event_claims)


def test_compound_failure_commercial_decision_is_separate_from_physical_routing():
    report = reconcile(_load_shipment())
    record = report.items[0]

    # 6 units physically scrapped, but the supplier's credit figure (4) is its
    # own independent commercial number, not derived from the scrap quantity.
    assert record.commercial_decision.credit_quantity == 4
    scrap_quantity = next(a.quantity for a in record.allocations if a.route == Route.SCRAP)
    assert record.commercial_decision.credit_quantity != scrap_quantity


def test_compound_failure_conservation_invariant_passes():
    report = reconcile(_load_shipment())
    assert report.summary.invariants_passed is True


def test_compound_failure_is_deterministic():
    first = reconcile(_load_shipment())
    second = reconcile(_load_shipment())
    assert first.model_dump() == second.model_dump()


def test_compound_failure_independent_of_supplier_event_array_order():
    shipment = _load_shipment()
    reversed_shipment = shipment.model_copy(
        update={"supplier_events": list(reversed(shipment.supplier_events))}
    )

    forward = reconcile(shipment)
    reversed_result = reconcile(reversed_shipment)

    assert forward.model_dump() == reversed_result.model_dump()


def test_compound_failure_does_not_crash_and_does_not_default_globally():
    report = reconcile(_load_shipment())
    record = report.items[0]

    # neither source won every field: warehouse wins condition, supplier
    # (corroborated) wins batch, both are represented in the winning sources.
    winning_sources = {f.winning_source for f in record.resolved_fields if f.winning_source}
    assert len(winning_sources) > 1
