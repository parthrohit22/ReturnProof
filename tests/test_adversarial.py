"""Hostile cases from the adversarial audit pass. Each test targets a specific
scenario the audit identified as under-covered or previously mishandled,
not a rewrite of the original test suite.
"""

from __future__ import annotations

import itertools

import pytest
from pydantic import ValidationError

from returnproof.conflicts import ConflictType
from returnproof.enums import EvidenceStatus, Provenance, Route
from returnproof.reconciler import reconcile
from returnproof.temporal import resolve_supplier_state
from returnproof.validation import classify_batch
from tests.conftest import make_event, make_item, make_known_batch, make_metadata, make_shipment, ts

# --- Temporal: permutation invariance beyond a single reversal ---------------


def test_permutation_invariance_across_all_orderings():
    a = make_event(event_id="A", event_timestamp=ts(9, 0))
    b = make_event(event_id="B", event_timestamp=ts(10, 0))
    c = make_event(event_id="C", event_timestamp=ts(11, 0))

    results = {
        resolve_supplier_state(list(order)).current.event_id
        for order in itertools.permutations([a, b, c])
    }

    assert results == {"C"}


# --- Test Case E: same effective timestamp, conflicting payload --------------


def test_same_timestamp_conflicting_instructions_is_unresolved():
    a = make_event(event_id="A", event_timestamp=ts(14, 0), instruction="RESTOCK")
    b = make_event(event_id="B", event_timestamp=ts(14, 0), instruction="SCRAP")

    resolution = resolve_supplier_state([a, b])

    assert resolution.ambiguous is True
    assert resolution.current is None
    assert {e.event_id for e in resolution.tied} == {"A", "B"}


def test_ambiguous_supplier_state_surfaces_as_a_conflict_and_quarantines_material_stock():
    item = make_item(condition="GOOD", quantity_received=10, damaged_quantity=0)
    a = make_event(event_id="A", event_timestamp=ts(14, 0), instruction="RESTOCK")
    b = make_event(event_id="B", event_timestamp=ts(14, 0), instruction="SCRAP")
    shipment = make_shipment([item], [a, b])

    report = reconcile(shipment)
    record = report.items[0]

    assert any(c.type == ConflictType.SUPPLIER_STATE_AMBIGUOUS for c in record.conflicts)
    # no current supplier event means credit fields resolve to UNRESOLVED, not a guess
    credit_field = next(f for f in record.resolved_fields if f.field == "credit_eligible")
    assert credit_field.provenance == Provenance.UNRESOLVED


# --- Test Case F: exact duplicate events, no false ambiguity -----------------


def test_duplicate_content_tied_events_are_not_ambiguous():
    a = make_event(event_id="A", event_timestamp=ts(14, 0), instruction="RESTOCK")
    b = make_event(event_id="B", event_timestamp=ts(14, 0), instruction="RESTOCK")

    resolution = resolve_supplier_state([a, b])

    assert resolution.ambiguous is False
    assert resolution.current is not None
    assert resolution.current.event_id == "A"  # deterministic: lowest event_id
    assert resolution.superseded[0].event_id == "B"


def test_exact_duplicate_event_id_same_content_is_deduped_at_parse():
    item = make_item()
    event = make_event(event_id="evt-1")
    duplicate = event.model_copy()
    shipment = make_shipment([item], [event, duplicate])

    assert len(shipment.supplier_events) == 1


def test_duplicate_event_id_different_content_is_rejected():
    item = make_item()
    a = make_event(event_id="evt-1", instruction="RESTOCK")
    b = make_event(event_id="evt-1", instruction="SCRAP")
    with pytest.raises(ValidationError):
        make_shipment([item], [a, b])


# --- Test Case D: partially missing versions ---------------------------------


def test_partial_versions_fall_back_deterministically_regardless_of_order():
    a = make_event(event_id="A", version=1, event_timestamp=ts(9, 0))
    b = make_event(event_id="B", version=None, event_timestamp=ts(11, 0))
    c = make_event(event_id="C", version=3, event_timestamp=ts(10, 0))

    forward = resolve_supplier_state([a, b, c])
    reversed_order = resolve_supplier_state([c, b, a])

    assert forward.ordering_basis == "event_timestamp"
    assert forward.current.event_id == reversed_order.current.event_id == "B"


# --- Section 7: both batches format-valid but conflicting --------------------


def test_valid_conflicting_batches_no_corroboration_is_unresolved_not_arbitrary():
    item = make_item(batch_code="BA1902", sku="MILK-01")
    event = make_event(batch_code="BA1903", sku="MILK-01")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    batch_field = next(f for f in report.items[0].resolved_fields if f.field == "batch_code")

    assert batch_field.value is None
    assert batch_field.provenance == Provenance.UNRESOLVED
    assert batch_field.winning_source is None


def test_valid_conflicting_batches_corroboration_breaks_the_tie():
    item = make_item(batch_code="BA1902", sku="MILK-01")
    event = make_event(batch_code="BA1903", sku="MILK-01")
    metadata = make_metadata(sku="MILK-01", known_batches=[make_known_batch(batch_code="BA1903")])
    shipment = make_shipment([item], [event], [metadata])

    report = reconcile(shipment)
    batch_field = next(f for f in report.items[0].resolved_fields if f.field == "batch_code")

    assert batch_field.value == "BA1903"
    assert batch_field.provenance == Provenance.CORROBORATED


def test_valid_conflicting_batches_marks_both_claims_unresolved_not_silently_accepted():
    item = make_item(batch_code="BA1902", sku="MILK-01")
    event = make_event(batch_code="BA1903", sku="MILK-01")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    warehouse_claim = next(c for c in record.evidence if c.claim_id == f"{item.item_id}:warehouse:batch_code")
    supplier_claim = next(
        c for c in record.evidence if c.claim_id == f"{item.item_id}:supplier:{event.event_id}:batch_code"
    )
    assert warehouse_claim.status == EvidenceStatus.UNRESOLVED
    assert supplier_claim.status == EvidenceStatus.UNRESOLVED


# --- Section 8: corrupted warehouse + uncorroborated supplier, metadata present for SKU ---


def test_corrupted_warehouse_uncorroborated_supplier_with_metadata_present_for_sku():
    item = make_item(batch_code="BA?9O2", sku="MILK-01")
    event = make_event(batch_code="BA1902", sku="MILK-01")
    # metadata exists for this SKU, but does not contain the supplier's batch
    metadata = make_metadata(sku="MILK-01", known_batches=[make_known_batch(batch_code="ZZ0000")])
    shipment = make_shipment([item], [event], [metadata])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.provenance == Provenance.UNRESOLVED
    assert record.allocations[0].route == Route.QUARANTINE


# --- Section 11: supplier RESTOCK against UNKNOWN condition ------------------


def test_supplier_restock_against_unknown_condition_quarantines_and_flags_conflict():
    item = make_item(condition="UNKNOWN", damaged_quantity=0, quantity_received=10)
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)
    assert record.allocations[0].route == Route.QUARANTINE


# --- Section 12: supplier SCRAP against GOOD physical stock ------------------


def test_supplier_scrap_against_good_condition_is_flagged_and_quarantined():
    item = make_item(condition="GOOD", damaged_quantity=0, quantity_received=10)
    event = make_event(instruction="SCRAP")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)
    # not auto-restocked, and not auto-scrapped either, no physical evidence of damage
    assert record.allocations[0].route == Route.QUARANTINE
    assert "R007" in record.rules_applied


def test_supplier_restock_against_good_condition_is_not_a_conflict():
    item = make_item(condition="GOOD", damaged_quantity=0, quantity_received=10)
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert not any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)
    assert record.allocations[0].route == Route.RESTOCK


# --- Section 15: unresolved best-before blocks restock despite RESTOCK -------


def test_unresolved_identity_blocks_restock_even_with_explicit_supplier_restock():
    item = make_item(condition="GOOD", batch_code=None, best_before=None, quantity_received=10)
    event = make_event(instruction="RESTOCK", batch_code=None)
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert record.resolved.batch_code is None
    assert record.resolved.best_before_bucket is None
    assert record.allocations[0].route == Route.QUARANTINE


def test_best_before_disagreement_with_corroborated_metadata_is_recorded_not_silent():
    from datetime import date

    item = make_item(batch_code="BA?9O2", sku="MILK-01", best_before=date(2026, 10, 18))
    event = make_event(batch_code="BA1902", sku="MILK-01")
    metadata = make_metadata(
        sku="MILK-01",
        known_batches=[make_known_batch(batch_code="BA1902", best_before=date(2026, 11, 18))],
    )
    shipment = make_shipment([item], [event], [metadata])

    report = reconcile(shipment)
    record = report.items[0]

    best_before_field = next(f for f in record.resolved_fields if f.field == "best_before")
    assert best_before_field.value.isoformat() == "2026-11-18"

    warehouse_claim = next(c for c in record.evidence if c.claim_id == f"{item.item_id}:warehouse:best_before")
    assert warehouse_claim.status == EvidenceStatus.REJECTED
    assert "2026-11-18" in warehouse_claim.reason


# --- Section 13: supplier-internal commercial inconsistency ------------------


def test_credit_quantity_exceeding_acknowledged_quantity_is_flagged():
    item = make_item(condition="GOOD", quantity_received=10, damaged_quantity=0)
    event = make_event(acknowledged_quantity=5, credit_quantity=8)
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert any("supplier-internal inconsistency" in c.description for c in record.conflicts)
    # physical routing is unaffected by the commercial data-quality problem
    assert record.allocations[0].route == Route.RESTOCK


# --- Section 6: contextual batch pattern --------------------------------------


def test_contextual_batch_pattern_overrides_default_grammar():
    assessment = classify_batch("2026-A-771", pattern=r"\d{4}-[A-Z]-\d{3}")
    assert assessment.validity.value == "VALID"

    # the same raw value fails the default grammar
    assessment_default = classify_batch("2026-A-771")
    assert assessment_default.validity.value == "CORRUPTED"


def test_contextual_batch_pattern_applied_through_full_reconciliation():
    item = make_item(batch_code="2026-A-771", sku="WIDGET-1")
    metadata = make_metadata(sku="WIDGET-1")
    metadata = metadata.model_copy(update={"batch_pattern": r"\d{4}-[A-Z]-\d{3}"})
    shipment = make_shipment([item], [], [metadata])

    report = reconcile(shipment)
    batch_field = next(f for f in report.items[0].resolved_fields if f.field == "batch_code")

    assert batch_field.value == "2026-A-771"
    assert batch_field.provenance == Provenance.DIRECT


# --- Section 26: human and JSON render the same underlying decision ----------


def test_human_and_json_renderers_agree_on_material_values():
    from typer.testing import CliRunner

    from returnproof.cli import app

    runner = CliRunner()
    args = ["reconcile", "examples/compound_failure.json"]
    human = runner.invoke(app, args)
    machine = runner.invoke(app, [*args, "--json"])

    assert human.exit_code == 0
    assert machine.exit_code == 0

    import json

    payload = json.loads(machine.stdout)
    resolved = payload["items"][0]["resolved"]

    assert resolved["batch_code"] in human.stdout
    assert resolved["best_before_bucket"] in human.stdout
    for allocation in payload["items"][0]["allocations"]:
        assert str(allocation["quantity"]) in human.stdout
        assert allocation["route"] in human.stdout
