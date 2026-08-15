"""Input domain model: what the warehouse and the supplier each report.

These are the raw, untrusted inputs. Nothing here is a decision, it is only
a structured, validated shape for evidence extraction to work from.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from returnproof.enums import Condition, SupplierInstruction


class WarehouseItem(BaseModel):
    """One line of the warehouse inspection report."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    sku: str
    quantity_received: int = Field(ge=0)
    condition: Condition = Condition.UNKNOWN
    damage_type: str | None = None
    damaged_quantity: int = Field(default=0, ge=0)
    batch_code: str | None = None
    best_before: date | None = None
    inspection_timestamp: datetime | None = None

    @model_validator(mode="after")
    def _damaged_within_received(self) -> WarehouseItem:
        if self.damaged_quantity > self.quantity_received:
            raise ValueError(
                f"item {self.item_id}: damaged_quantity ({self.damaged_quantity}) "
                f"exceeds quantity_received ({self.quantity_received})"
            )
        return self


class WarehouseReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WarehouseItem]


class SupplierEvent(BaseModel):
    """One supplier credit-note event. Multiple events may describe the same item."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    item_id: str
    sku: str
    batch_code: str | None = None
    acknowledged_quantity: int | None = Field(default=None, ge=0)
    credit_eligible: bool | None = None
    credit_quantity: int | None = Field(default=None, ge=0)
    instruction: SupplierInstruction | None = None
    event_timestamp: datetime
    received_at: datetime
    version: int | None = None


class KnownBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_code: str
    best_before: date | None = None


class ProductMetadata(BaseModel):
    """Optional catalog data used only to corroborate, never to originate, evidence."""

    model_config = ConfigDict(extra="forbid")

    sku: str
    known_batches: list[KnownBatch] = Field(default_factory=list)
    batch_pattern: str | None = None
    """SKU-specific batch code regex, overriding validation.py's default demo grammar
    (two letters + 4-6 digits). Optional, most SKUs rely on the default."""

    @field_validator("batch_pattern")
    @classmethod
    def _batch_pattern_must_be_a_valid_regex(cls, value: str | None) -> str | None:
        """A malformed regex is bad input, not uncertain business evidence, it
        must fail here, at parse time, rather than reach classify_batch() mid
        reconciliation and raise re.error. This is the one authoritative place
        batch_pattern syntax is checked, see validation.classify_batch()'s own
        guard for why a second check still exists there.
        """
        if value is None:
            return value
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"batch_pattern is not a valid regular expression: {exc}") from exc
        return value


class ReturnShipment(BaseModel):
    """Top-level input document: one return, both sources, optional catalog data."""

    model_config = ConfigDict(extra="forbid")

    return_id: str
    warehouse_report: WarehouseReport
    supplier_events: list[SupplierEvent] = Field(default_factory=list)
    product_metadata: list[ProductMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def _dedupe_or_reject_event_id_collisions(self) -> ReturnShipment:
        """A repeated event_id is either a harmless retried delivery (identical
        content, silently collapsed to one) or two different records sharing
        an id (a data integrity problem, rejected outright rather than left to
        silently corrupt claim lookups downstream, which key off event_id).
        """
        seen: dict[str, SupplierEvent] = {}
        deduped: list[SupplierEvent] = []
        for event in self.supplier_events:
            prior = seen.get(event.event_id)
            if prior is None:
                seen[event.event_id] = event
                deduped.append(event)
            elif prior != event:
                raise ValueError(
                    f"event_id {event.event_id!r} appears twice with different content, "
                    "this is either a duplicate delivery with corrupted content or two "
                    "distinct events that were assigned the same id, both are input errors"
                )
            # else: exact duplicate delivery, silently collapsed.
        self.supplier_events = deduped
        return self

    def known_batches_for_sku(self, sku: str) -> list[KnownBatch]:
        for meta in self.product_metadata:
            if meta.sku == sku:
                return meta.known_batches
        return []

    def batch_pattern_for_sku(self, sku: str) -> str | None:
        for meta in self.product_metadata:
            if meta.sku == sku:
                return meta.batch_pattern
        return None
