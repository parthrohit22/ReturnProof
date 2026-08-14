"""Thin HTTP boundary schemas.

Deliberately not a restatement of `returnproof.models.ReturnShipment`'s
twenty-odd fields. The reconciliation request body is validated by the
existing `parse_shipment` function against the existing pydantic models,
these schemas only shape what the API layer adds on top: persistence
metadata and the two JSON blobs (`input_payload`, `audit_report`) that are
the engine's own output, passed through unmodified.
"""

from __future__ import annotations

import uuid
from typing import Any

from ninja import Schema


class ErrorDetail(Schema):
    path: str
    message: str


class ErrorResponse(Schema):
    error: str
    message: str
    details: list[ErrorDetail] = []


class ExampleListSchema(Schema):
    examples: list[str]


class RunSummarySchema(Schema):
    id: uuid.UUID
    return_id: str
    scenario_name: str | None = None
    summary_status: str
    item_count: int
    conflict_count: int
    quantity_received: int
    route_totals: dict[str, int]
    created_at: str


class RunDetailSchema(RunSummarySchema):
    input_payload: dict[str, Any]
    audit_report: dict[str, Any]
