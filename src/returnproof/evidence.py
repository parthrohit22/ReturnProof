"""Evidence extraction: turn raw source values into structured, provenance-tagged claims.

This module only extracts. It does not decide which claim wins a field,
that happens in policies.py / reconciler.py, which read this evidence list
and update claim status (ACCEPTED -> REJECTED, SUSPECT -> CORROBORATED,
etc) as resolution proceeds. Extraction never drops a value, an absent or
corrupted field still produces a claim carrying its own status, so the
audit trail always shows what was available and what state it was in.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from returnproof.enums import EvidenceField, EvidenceSource, EvidenceStatus, Provenance
from returnproof.models import SupplierEvent, WarehouseItem
from returnproof.temporal import SupplierEventResolution
from returnproof.validation import BatchAssessment, BatchValidity

_BATCH_STATUS_BY_VALIDITY = {
    BatchValidity.VALID: EvidenceStatus.ACCEPTED,
    BatchValidity.SUSPECT: EvidenceStatus.SUSPECT,
    BatchValidity.CORRUPTED: EvidenceStatus.CORRUPTED,
    BatchValidity.MISSING: EvidenceStatus.UNRESOLVED,
}


class EvidenceClaim(BaseModel):
    """A single field value reported by a single source, with its provenance."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    claim_id: str
    item_id: str
    field: EvidenceField
    value: Any
    source: EvidenceSource
    status: EvidenceStatus
    authority: Provenance
    reason: str
    source_reference: str
    timestamp: datetime | None = None


def extract_warehouse_claims(
    item: WarehouseItem, batch_assessment: BatchAssessment
) -> list[EvidenceClaim]:
    """Build evidence claims from one warehouse report line."""
    claims: list[EvidenceClaim] = []
    ref = "warehouse_report"

    claims.append(
        EvidenceClaim(
            claim_id=f"{item.item_id}:warehouse:condition",
            item_id=item.item_id,
            field=EvidenceField.CONDITION,
            value=item.condition,
            source=EvidenceSource.WAREHOUSE,
            status=EvidenceStatus.ACCEPTED,
            authority=Provenance.DIRECT,
            reason="warehouse direct physical inspection",
            source_reference=ref,
            timestamp=item.inspection_timestamp,
        )
    )

    if item.damage_type is not None:
        claims.append(
            EvidenceClaim(
                claim_id=f"{item.item_id}:warehouse:damage_type",
                item_id=item.item_id,
                field=EvidenceField.DAMAGE_TYPE,
                value=item.damage_type,
                source=EvidenceSource.WAREHOUSE,
                status=EvidenceStatus.ACCEPTED,
                authority=Provenance.DIRECT,
                reason="warehouse direct physical inspection",
                source_reference=ref,
                timestamp=item.inspection_timestamp,
            )
        )

    claims.append(
        EvidenceClaim(
            claim_id=f"{item.item_id}:warehouse:quantity_received",
            item_id=item.item_id,
            field=EvidenceField.QUANTITY_RECEIVED,
            value=item.quantity_received,
            source=EvidenceSource.WAREHOUSE,
            status=EvidenceStatus.ACCEPTED,
            authority=Provenance.DIRECT,
            reason="warehouse physical count on receipt",
            source_reference=ref,
            timestamp=item.inspection_timestamp,
        )
    )

    if item.best_before is not None:
        claims.append(
            EvidenceClaim(
                claim_id=f"{item.item_id}:warehouse:best_before",
                item_id=item.item_id,
                field=EvidenceField.BEST_BEFORE,
                value=item.best_before,
                source=EvidenceSource.WAREHOUSE,
                status=EvidenceStatus.ACCEPTED,
                authority=Provenance.DIRECT,
                reason="warehouse label reading",
                source_reference=ref,
                timestamp=item.inspection_timestamp,
            )
        )

    batch_status = _BATCH_STATUS_BY_VALIDITY[batch_assessment.validity]
    batch_reason = batch_assessment.transformation or "warehouse scanned batch code"
    claims.append(
        EvidenceClaim(
            claim_id=f"{item.item_id}:warehouse:batch_code",
            item_id=item.item_id,
            field=EvidenceField.BATCH_CODE,
            value=batch_assessment.raw_value,
            source=EvidenceSource.WAREHOUSE,
            status=batch_status,
            authority=(
                Provenance.DIRECT
                if batch_assessment.validity == BatchValidity.VALID
                else Provenance.UNRESOLVED
            ),
            reason=batch_reason,
            source_reference=ref,
            timestamp=item.inspection_timestamp,
        )
    )

    return claims


_SUPPLIER_FIELDS: tuple[EvidenceField, ...] = (
    EvidenceField.BATCH_CODE,
    EvidenceField.ACKNOWLEDGED_QUANTITY,
    EvidenceField.CREDIT_ELIGIBLE,
    EvidenceField.CREDIT_QUANTITY,
    EvidenceField.INSTRUCTION,
)


def _supplier_field_value(event: SupplierEvent, field: EvidenceField) -> Any:
    return getattr(event, field.value)


def _claims_for_event(
    event: SupplierEvent, status: EvidenceStatus, reason: str
) -> list[EvidenceClaim]:
    claims: list[EvidenceClaim] = []
    for field in _SUPPLIER_FIELDS:
        value = _supplier_field_value(event, field)
        if value is None:
            continue
        claims.append(
            EvidenceClaim(
                claim_id=f"{event.item_id}:supplier:{event.event_id}:{field.value}",
                item_id=event.item_id,
                field=field,
                value=value,
                source=EvidenceSource.SUPPLIER,
                status=status,
                authority=Provenance.DIRECT,
                reason=reason,
                source_reference=event.event_id,
                timestamp=event.event_timestamp,
            )
        )
    return claims


def extract_supplier_claims(resolution: SupplierEventResolution) -> list[EvidenceClaim]:
    """Build evidence claims from a temporally-resolved set of supplier events.

    The current event's claims are ACCEPTED. Every field of every superseded
    event still produces a claim, marked SUPERSEDED with the reason it lost,
    so a reviewer can see exactly what was discarded and why. If the
    resolution is ambiguous (two events tie with conflicting content, see
    temporal.py), there is no current event: the tied events' claims are
    marked UNRESOLVED rather than either ACCEPTED or SUPERSEDED, since
    neither is known to be current or stale.
    """
    claims: list[EvidenceClaim] = []
    if resolution.current is not None:
        claims.extend(
            _claims_for_event(
                resolution.current,
                EvidenceStatus.ACCEPTED,
                f"current supplier state, resolved via {resolution.ordering_basis} ordering",
            )
        )
    for stale_event in resolution.superseded:
        superseded_by = resolution.current.event_id if resolution.current else "an equivalent duplicate"
        claims.extend(
            _claims_for_event(
                stale_event,
                EvidenceStatus.SUPERSEDED,
                f"superseded by event {superseded_by} ({resolution.reasoning})",
            )
        )
    for tied_event in resolution.tied:
        claims.extend(
            _claims_for_event(
                tied_event,
                EvidenceStatus.UNRESOLVED,
                f"tied with conflicting content against another event, current state ambiguous "
                f"({resolution.reasoning})",
            )
        )
    return claims
