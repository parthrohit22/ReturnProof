from returnproof.enums import Route
from returnproof.reconciler import reconcile
from tests.conftest import make_event, make_item, make_shipment


def test_damaged_and_intact_portions_route_independently():
    item = make_item(
        quantity_received=20,
        damaged_quantity=8,
        condition="DAMAGED_SALVAGEABLE",
    )
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    assert len(record.allocations) == 2
    routes = {a.route: a.quantity for a in record.allocations}
    assert routes[Route.QUARANTINE] == 8
    assert routes[Route.RESTOCK] == 12
    assert sum(a.quantity for a in record.allocations) == 20


def test_unsafe_damage_scraps_only_the_damaged_subset():
    item = make_item(quantity_received=24, damaged_quantity=6, condition="DAMAGED_UNSAFE")
    event = make_event(instruction="RESTOCK")
    shipment = make_shipment([item], [event])

    report = reconcile(shipment)
    record = report.items[0]

    routes = {a.route: a.quantity for a in record.allocations}
    assert routes[Route.SCRAP] == 6
    assert routes[Route.RESTOCK] == 18


def test_whole_item_condition_with_no_partial_split():
    item = make_item(quantity_received=15, damaged_quantity=0, condition="DAMAGED_UNSAFE")
    shipment = make_shipment([item], [])

    report = reconcile(shipment)
    record = report.items[0]

    assert len(record.allocations) == 1
    assert record.allocations[0].route == Route.SCRAP
    assert record.allocations[0].quantity == 15


def test_rejected_alternatives_present_for_each_allocation():
    item = make_item(quantity_received=20, damaged_quantity=8, condition="DAMAGED_SALVAGEABLE")
    shipment = make_shipment([item], [])

    report = reconcile(shipment)
    record = report.items[0]

    assert len(record.rejected_alternatives) == len(record.allocations)
    for explanation in record.rejected_alternatives:
        assert len(explanation.rejected_alternatives) >= 1
