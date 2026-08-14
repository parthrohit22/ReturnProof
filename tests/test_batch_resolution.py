from returnproof.enums import ConflictType, EvidenceStatus, Provenance, Route
from returnproof.reconciler import reconcile
from tests.conftest import make_event, make_item, make_known_batch, make_metadata, make_shipment


def test_valid_matching_batch_accepted():
    item = make_item(batch_code="AB1234")
    event = make_event(batch_code="AB1234")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.value == "AB1234"
    assert batch_field.provenance == Provenance.CORROBORATED
    assert record.resolved.batch_code == "AB1234"
    assert not any(c.type == ConflictType.BATCH_MISMATCH for c in record.conflicts)


def test_corrupted_warehouse_batch_resolves_via_corroborated_supplier():
    item = make_item(batch_code="BA?9O2", sku="MILK-01")
    event = make_event(batch_code="BA1902", sku="MILK-01")
    metadata = make_metadata(sku="MILK-01", known_batches=[make_known_batch(batch_code="BA1902")])
    shipment = make_shipment([item], [event], [metadata])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.value == "BA1902"
    assert batch_field.provenance == Provenance.CORROBORATED
    assert "R002" in record.rules_applied
    assert "R003" in record.rules_applied

    warehouse_claim = next(
        c for c in record.evidence if c.claim_id == f"{item.item_id}:warehouse:batch_code"
    )
    assert warehouse_claim.status == EvidenceStatus.CORRUPTED

    supplier_claim = next(
        c for c in record.evidence if c.claim_id == f"{item.item_id}:supplier:{event.event_id}:batch_code"
    )
    assert supplier_claim.status == EvidenceStatus.CORROBORATED


def test_unresolved_mismatch_quarantines_rather_than_guesses():
    item = make_item(batch_code="BA?9O2", sku="MILK-01", condition="GOOD", quantity_received=10)
    event = make_event(batch_code="ZZ9999", sku="MILK-01")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.value is None
    assert batch_field.provenance == Provenance.UNRESOLVED
    assert "R007" in record.rules_applied
    assert record.allocations[0].route == Route.QUARANTINE


def test_no_supplier_batch_and_corrupted_warehouse_is_unresolved():
    item = make_item(batch_code="BA?9O2", condition="GOOD", quantity_received=10)
    shipment = make_shipment([item], [])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.provenance == Provenance.UNRESOLVED
    assert record.allocations[0].route == Route.QUARANTINE


def test_missing_warehouse_batch_still_resolves_via_corroboration():
    item = make_item(batch_code=None, sku="MILK-01")
    event = make_event(batch_code="BA1902", sku="MILK-01")
    metadata = make_metadata(sku="MILK-01", known_batches=[make_known_batch(batch_code="BA1902")])
    shipment = make_shipment([item], [event], [metadata])

    report = reconcile(shipment)
    record = report.items[0]
    batch_field = next(f for f in record.resolved_fields if f.field == "batch_code")

    assert batch_field.value == "BA1902"
    assert batch_field.provenance == Provenance.CORROBORATED
