import pytest
from pydantic import ValidationError

from returnproof.enums import ConflictType
from returnproof.reconciler import reconcile
from tests.conftest import make_event, make_item, make_shipment


def test_received_vs_acknowledged_dispute_detected():
    item = make_item(quantity_received=20, damaged_quantity=0)
    event = make_event(acknowledged_quantity=16)
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert any(c.type == ConflictType.QUANTITY_OR_ELIGIBILITY_DISPUTE for c in record.conflicts)


def test_damaged_vs_credit_quantity_dispute_detected():
    item = make_item(quantity_received=10, damaged_quantity=8, condition="DAMAGED_UNSAFE")
    event = make_event(acknowledged_quantity=10, credit_quantity=5)
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    descriptions = [c.description for c in record.conflicts]
    assert any("credit" in d for d in descriptions)


def test_physical_quantity_and_credit_quantity_remain_separate():
    item = make_item(quantity_received=20, damaged_quantity=5, condition="DAMAGED_UNSAFE")
    event = make_event(acknowledged_quantity=20, credit_quantity=3)
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    quantity_field = next(f for f in record.resolved_fields if f.field == "quantity_received")
    credit_field = next(f for f in record.resolved_fields if f.field == "credit_quantity")

    assert quantity_field.value == 20
    assert credit_field.value == 3
    # physical allocation uses the warehouse's damaged_quantity, not the supplier's credit figure
    scrap_allocation = next(a for a in record.allocations if a.route == "SCRAP")
    assert scrap_allocation.quantity == 5


def test_negative_acknowledged_quantity_rejected():
    with pytest.raises(ValidationError):
        make_event(acknowledged_quantity=-1)


def test_negative_credit_quantity_rejected():
    with pytest.raises(ValidationError):
        make_event(credit_quantity=-1)


def test_allocations_never_exceed_received_quantity():
    item = make_item(quantity_received=10, damaged_quantity=4, condition="DAMAGED_UNSAFE")
    event = make_event()
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert sum(a.quantity for a in record.allocations) == item.quantity_received
