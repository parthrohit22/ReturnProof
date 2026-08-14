from returnproof.allocation import Allocation, check_conservation
from returnproof.reconciler import reconcile
from tests.conftest import make_event, make_item, make_shipment


def test_conservation_passes_for_simple_item():
    item = make_item(quantity_received=10, condition="GOOD")
    shipment = make_shipment([item], [make_event()])

    report = reconcile(shipment)
    record = report.items[0]

    assert all(check.passed for check in record.invariants)
    assert report.summary.invariants_passed is True


def test_conservation_passes_for_partial_allocation():
    item = make_item(quantity_received=20, damaged_quantity=8, condition="DAMAGED_SALVAGEABLE")
    shipment = make_shipment([item], [make_event()])

    report = reconcile(shipment)
    record = report.items[0]

    total = sum(a.quantity for a in record.allocations)
    assert total == item.quantity_received
    assert all(check.passed for check in record.invariants)


def test_conservation_checker_detects_a_broken_allocation_set():
    item = make_item(quantity_received=10)
    broken_allocations = [
        Allocation(quantity=4, route="RESTOCK", reason="test", context="resolved_good"),
    ]

    check = check_conservation(item, broken_allocations)

    assert check.passed is False
    assert "10 received" in check.detail
    assert "4 allocated" in check.detail


def test_conservation_checker_detects_over_allocation():
    item = make_item(quantity_received=10)
    broken_allocations = [
        Allocation(quantity=6, route="RESTOCK", reason="test", context="resolved_good"),
        Allocation(quantity=6, route="SCRAP", reason="test", context="unsafe_damage"),
    ]

    check = check_conservation(item, broken_allocations)

    assert check.passed is False


def test_zero_quantity_item_has_empty_allocations_and_passes():
    item = make_item(quantity_received=0, damaged_quantity=0)
    shipment = make_shipment([item], [])

    report = reconcile(shipment)
    record = report.items[0]

    assert record.allocations == []
    assert all(check.passed for check in record.invariants)
