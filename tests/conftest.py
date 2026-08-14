"""Shared test fixtures: small factories for building valid domain objects
without repeating every field in each test.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from returnproof.models import (
    KnownBatch,
    ProductMetadata,
    ReturnShipment,
    SupplierEvent,
    WarehouseItem,
    WarehouseReport,
)


def ts(hour: int, minute: int, day: int = 10) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=UTC)


def make_item(**overrides) -> WarehouseItem:
    defaults = {
        "item_id": "ITEM-1",
        "sku": "SKU-1",
        "quantity_received": 10,
        "condition": "GOOD",
        "damaged_quantity": 0,
        "batch_code": "AB1234",
        "best_before": date(2027, 1, 1),
        "inspection_timestamp": ts(9, 0),
    }
    defaults.update(overrides)
    return WarehouseItem(**defaults)


def make_event(**overrides) -> SupplierEvent:
    defaults = {
        "event_id": "evt-1",
        "item_id": "ITEM-1",
        "sku": "SKU-1",
        "batch_code": "AB1234",
        "acknowledged_quantity": 10,
        "credit_eligible": True,
        "credit_quantity": 0,
        "instruction": "RESTOCK",
        "event_timestamp": ts(10, 0),
        "received_at": ts(10, 1),
    }
    defaults.update(overrides)
    return SupplierEvent(**defaults)


def make_known_batch(**overrides) -> KnownBatch:
    defaults = {"batch_code": "AB1234", "best_before": date(2027, 1, 1)}
    defaults.update(overrides)
    return KnownBatch(**defaults)


def make_metadata(sku: str = "SKU-1", known_batches=None) -> ProductMetadata:
    return ProductMetadata(sku=sku, known_batches=known_batches or [])


def make_shipment(items, events=None, metadata=None, return_id="RET-TEST") -> ReturnShipment:
    return ReturnShipment(
        return_id=return_id,
        warehouse_report=WarehouseReport(items=items),
        supplier_events=events or [],
        product_metadata=metadata or [],
    )
