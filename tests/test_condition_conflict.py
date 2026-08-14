from returnproof.enums import ConflictType, Route
from returnproof.reconciler import reconcile
from tests.conftest import make_event, make_item, make_shipment


def test_unsafe_condition_overrides_supplier_restock():
    item = make_item(
        quantity_received=10,
        condition="DAMAGED_UNSAFE",
        damaged_quantity=10,
    )
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)
    assert len(record.allocations) == 1
    assert record.allocations[0].route == Route.SCRAP
    assert record.allocations[0].quantity == 10
    assert "R005" in record.rules_applied


def test_salvageable_damage_quarantines_instead_of_restocking():
    item = make_item(
        quantity_received=10,
        condition="DAMAGED_SALVAGEABLE",
        damaged_quantity=10,
    )
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert record.allocations[0].route == Route.QUARANTINE
    # not proven unsafe, so the safety-override rule does not fire
    assert "R005" not in record.rules_applied


def test_no_conflict_when_supplier_agrees_item_is_damaged():
    item = make_item(condition="DAMAGED_UNSAFE", damaged_quantity=10, quantity_received=10)
    event = make_event(instruction="SCRAP")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert not any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)


def test_good_condition_no_condition_conflict():
    item = make_item(condition="GOOD", damaged_quantity=0, quantity_received=10)
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert not any(c.type == ConflictType.CONDITION_DISAGREEMENT for c in record.conflicts)
    assert record.allocations[0].route == Route.RESTOCK
