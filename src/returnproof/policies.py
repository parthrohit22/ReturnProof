"""Decision rules and field authority. The one place a reviewer should check.

Central principle: authority is contextual, not global. Table below is the
whole policy, not a summary of logic scattered elsewhere.

| Field                  | Authority                                          |
|-------------------------|----------------------------------------------------|
| condition                | Warehouse (direct physical observation)           |
| damage_type               | Warehouse                                        |
| quantity_received          | Warehouse (physical count)                     |
| acknowledged_quantity        | Supplier (their own acknowledgement)         |
| credit_eligible                | Supplier (contractual/commercial decision) |
| credit_quantity                  | Supplier                                 |
| instruction (routing preference)   | Neither, a preference weighed by rules |
| batch_code                           | Evidence/corroboration based, see resolve_batch()
| best_before                            | Evidence/corroboration based, tied to batch_code
| physical route (restock/scrap/quarantine)| Derived by policy, see allocation.py

No field is ever resolved by asking "which source do we trust more"
globally. Every function below answers "is this specific claim, in this
specific field, good enough to act on."
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from returnproof.enums import EvidenceField, EvidenceSource, EvidenceStatus, Provenance
from returnproof.models import KnownBatch, SupplierEvent, WarehouseItem
from returnproof.validation import BatchAssessment, BatchValidity, classify_batch

RULES: dict[str, str] = {
    "R001": (
        "PHYSICAL_CONDITION_AUTHORITY: warehouse direct physical observation has "
        "authority over supplier routing preference for physical condition."
    ),
    "R002": (
        "INVALID_EVIDENCE_LOSES_AUTHORITY: corrupted or suspect evidence cannot win "
        "a decision merely because of its source."
    ),
    "R003": (
        "BATCH_CORROBORATION: a supplier batch may resolve corrupted or suspect "
        "warehouse evidence when independently corroborated by product metadata."
    ),
    "R004": (
        "SUPPLIER_TEMPORAL_ORDERING: supplier state is resolved using business "
        "event order/version, not message arrival order."
    ),
    "R005": (
        "PHYSICAL_SAFETY_OVERRIDE: credible unsafe physical condition prevents "
        "restocking regardless of supplier instruction."
    ),
    "R006": (
        "QUANTITY_CONSERVATION: all received physical quantity must be allocated "
        "exactly once, across scrap, restock, and quarantine."
    ),
    "R007": (
        "UNCERTAINTY_ESCALATION: material unresolved identity, safety, or disposition "
        "uncertainty routes the affected stock to quarantine instead of guessing."
    ),
    "R008": (
        "COMMERCIAL_OPERATIONAL_SEPARATION: supplier credit eligibility does not "
        "determine physical stock routing, and physical routing does not determine "
        "credit eligibility."
    ),
}

FIELD_AUTHORITY: dict[EvidenceField, EvidenceSource | None] = {
    EvidenceField.CONDITION: EvidenceSource.WAREHOUSE,
    EvidenceField.DAMAGE_TYPE: EvidenceSource.WAREHOUSE,
    EvidenceField.QUANTITY_RECEIVED: EvidenceSource.WAREHOUSE,
    EvidenceField.ACKNOWLEDGED_QUANTITY: EvidenceSource.SUPPLIER,
    EvidenceField.CREDIT_ELIGIBLE: EvidenceSource.SUPPLIER,
    EvidenceField.CREDIT_QUANTITY: EvidenceSource.SUPPLIER,
    EvidenceField.INSTRUCTION: EvidenceSource.SUPPLIER,
    EvidenceField.BATCH_CODE: None,
    EvidenceField.BEST_BEFORE: None,
}


class ResolvedField(BaseModel):
    """Provenance record for one resolved field. This is the audit's core unit."""

    model_config = ConfigDict(extra="forbid")

    field: EvidenceField
    value: Any
    winning_source: EvidenceSource | None
    provenance: Provenance
    reason: str
    rules_applied: list[str]
    accepted_claim_ids: list[str] = []
    rejected_claim_ids: list[str] = []


class ClaimStatusUpdate(BaseModel):
    """An instruction to update one claim's status/reason after policy resolution."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    status: EvidenceStatus
    reason: str


def resolve_warehouse_only_field(
    item: WarehouseItem, field: EvidenceField, value: Any, rule: str | None = None
) -> ResolvedField:
    """Fields where the warehouse is the sole authoritative source by policy.

    `rule` is only set to a numbered rule ID (R001) for condition, where the
    brief names an explicit rule. Quantity/damage_type authority follows the
    same field-authority table but isn't one of the eight numbered rules.
    """
    return ResolvedField(
        field=field,
        value=value,
        winning_source=EvidenceSource.WAREHOUSE,
        provenance=Provenance.DIRECT if value is not None else Provenance.UNRESOLVED,
        reason=f"warehouse has policy authority for {field.value}",
        rules_applied=[rule] if rule else [],
        accepted_claim_ids=[f"{item.item_id}:warehouse:{field.value}"],
    )


def resolve_supplier_only_field(
    item_id: str,
    field: EvidenceField,
    current_event: SupplierEvent | None,
) -> ResolvedField:
    """Fields where the supplier is the sole authoritative source by policy (R008).

    R008 is only tagged when there is an actual current supplier event to
    separate from physical state, tagging it on an item with no supplier
    data at all would assert a separation that has nothing to separate.
    """
    value = getattr(current_event, field.value) if current_event is not None else None
    return ResolvedField(
        field=field,
        value=value,
        winning_source=EvidenceSource.SUPPLIER if value is not None else None,
        provenance=Provenance.DIRECT if value is not None else Provenance.UNRESOLVED,
        reason=(
            f"supplier has policy authority for {field.value}"
            if value is not None
            else "no supplier data available for this field"
        ),
        rules_applied=["R008"] if current_event is not None else [],
        accepted_claim_ids=(
            [f"{item_id}:supplier:{current_event.event_id}:{field.value}"]
            if current_event is not None and value is not None
            else []
        ),
    )


def _find_known_batch(known_batches: list[KnownBatch], code: str) -> KnownBatch | None:
    normalized = code.strip().upper()
    for batch in known_batches:
        if batch.batch_code.strip().upper() == normalized:
            return batch
    return None


def resolve_batch(
    item: WarehouseItem,
    batch_assessment: BatchAssessment,
    current_event: SupplierEvent | None,
    known_batches: list[KnownBatch],
) -> tuple[ResolvedField, list[ClaimStatusUpdate]]:
    """Resolve batch_code. Neither source wins automatically, see module docstring.

    Returns the resolved field plus any claim status updates the caller
    should apply to the working evidence list (e.g. promoting a supplier
    claim from ACCEPTED to CORROBORATED).
    """
    warehouse_claim_id = f"{item.item_id}:warehouse:batch_code"
    supplier_batch = current_event.batch_code if current_event else None
    supplier_claim_id = (
        f"{item.item_id}:supplier:{current_event.event_id}:batch_code"
        if current_event and supplier_batch
        else None
    )
    updates: list[ClaimStatusUpdate] = []

    if batch_assessment.validity == BatchValidity.VALID:
        warehouse_value = batch_assessment.normalized_value
        if supplier_batch is None:
            return (
                ResolvedField(
                    field=EvidenceField.BATCH_CODE,
                    value=warehouse_value,
                    winning_source=EvidenceSource.WAREHOUSE,
                    provenance=Provenance.DIRECT,
                    reason="warehouse batch code is well-formed and uncontested",
                    rules_applied=["R001"],
                    accepted_claim_ids=[warehouse_claim_id],
                ),
                updates,
            )

        supplier_normalized = classify_batch(supplier_batch).normalized_value
        if supplier_normalized == warehouse_value:
            updates.append(
                ClaimStatusUpdate(
                    claim_id=supplier_claim_id,
                    status=EvidenceStatus.CORROBORATED,
                    reason="agrees with a well-formed warehouse batch code",
                )
            )
            return (
                ResolvedField(
                    field=EvidenceField.BATCH_CODE,
                    value=warehouse_value,
                    winning_source=EvidenceSource.WAREHOUSE,
                    provenance=Provenance.CORROBORATED,
                    reason="warehouse batch code is well-formed and independently agreed by supplier",
                    rules_applied=["R001", "R003"],
                    accepted_claim_ids=[warehouse_claim_id, supplier_claim_id],
                ),
                updates,
            )

        # Both format-valid, but they disagree: consult product metadata for the tiebreak.
        warehouse_known = _find_known_batch(known_batches, warehouse_value)
        supplier_known = _find_known_batch(known_batches, supplier_batch)
        if warehouse_known and not supplier_known:
            updates.append(
                ClaimStatusUpdate(
                    claim_id=supplier_claim_id,
                    status=EvidenceStatus.REJECTED,
                    reason=f"does not match any known batch for SKU {item.sku}",
                )
            )
            return (
                ResolvedField(
                    field=EvidenceField.BATCH_CODE,
                    value=warehouse_value,
                    winning_source=EvidenceSource.WAREHOUSE,
                    provenance=Provenance.CORROBORATED,
                    reason="warehouse batch matches known product metadata, supplier batch does not",
                    rules_applied=["R003"],
                    accepted_claim_ids=[warehouse_claim_id],
                    rejected_claim_ids=[supplier_claim_id],
                ),
                updates,
            )
        if supplier_known and not warehouse_known:
            updates.append(
                ClaimStatusUpdate(
                    claim_id=supplier_claim_id,
                    status=EvidenceStatus.CORROBORATED,
                    reason=f"matches known batch metadata for SKU {item.sku}",
                )
            )
            updates.append(
                ClaimStatusUpdate(
                    claim_id=warehouse_claim_id,
                    status=EvidenceStatus.REJECTED,
                    reason=f"well-formed but does not match any known batch for SKU {item.sku}",
                )
            )
            return (
                ResolvedField(
                    field=EvidenceField.BATCH_CODE,
                    value=supplier_known.batch_code,
                    winning_source=EvidenceSource.SUPPLIER,
                    provenance=Provenance.CORROBORATED,
                    reason="supplier batch matches known product metadata, warehouse batch does not",
                    rules_applied=["R003"],
                    accepted_claim_ids=[supplier_claim_id],
                    rejected_claim_ids=[warehouse_claim_id],
                ),
                updates,
            )
        contest_reason = (
            "well-formed but contested by the other source, neither is corroborated "
            f"(or both are) by known batch metadata for SKU {item.sku}"
        )
        updates.append(
            ClaimStatusUpdate(claim_id=warehouse_claim_id, status=EvidenceStatus.UNRESOLVED, reason=contest_reason)
        )
        if supplier_claim_id:
            updates.append(
                ClaimStatusUpdate(claim_id=supplier_claim_id, status=EvidenceStatus.UNRESOLVED, reason=contest_reason)
            )
        return (
            ResolvedField(
                field=EvidenceField.BATCH_CODE,
                value=None,
                winning_source=None,
                provenance=Provenance.UNRESOLVED,
                reason=(
                    "warehouse and supplier batch codes disagree and neither is "
                    "corroborated (or both are) by product metadata"
                ),
                rules_applied=["R007"],
                rejected_claim_ids=[warehouse_claim_id]
                + ([supplier_claim_id] if supplier_claim_id else []),
            ),
            updates,
        )

    # Warehouse batch is SUSPECT, CORRUPTED, or MISSING: it cannot win by default (R002).
    if supplier_batch is None:
        return (
            ResolvedField(
                field=EvidenceField.BATCH_CODE,
                value=None,
                winning_source=None,
                provenance=Provenance.UNRESOLVED,
                reason=(
                    f"warehouse batch is {batch_assessment.validity.value.lower()} "
                    "and no supplier batch is available to corroborate against"
                ),
                rules_applied=["R002", "R007"],
                rejected_claim_ids=[warehouse_claim_id],
            ),
            updates,
        )

    known = _find_known_batch(known_batches, supplier_batch)
    if known is not None:
        updates.append(
            ClaimStatusUpdate(
                claim_id=supplier_claim_id,
                status=EvidenceStatus.CORROBORATED,
                reason=f"matches known batch metadata for SKU {item.sku}",
            )
        )
        candidate_note = ""
        if batch_assessment.normalized_candidate == known.batch_code:
            candidate_note = " (agrees with warehouse's OCR-repair candidate, still unused for the decision itself)"
        return (
            ResolvedField(
                field=EvidenceField.BATCH_CODE,
                value=known.batch_code,
                winning_source=EvidenceSource.SUPPLIER,
                provenance=Provenance.CORROBORATED,
                reason=(
                    f"warehouse batch is {batch_assessment.validity.value.lower()}, "
                    f"supplier batch independently corroborated by product metadata for SKU "
                    f"{item.sku}{candidate_note}"
                ),
                rules_applied=["R002", "R003"],
                accepted_claim_ids=[supplier_claim_id],
                rejected_claim_ids=[warehouse_claim_id],
            ),
            updates,
        )

    updates.append(
        ClaimStatusUpdate(
            claim_id=supplier_claim_id,
            status=EvidenceStatus.UNRESOLVED,
            reason=f"not corroborated by any known batch metadata for SKU {item.sku}",
        )
    )
    return (
        ResolvedField(
            field=EvidenceField.BATCH_CODE,
            value=None,
            winning_source=None,
            provenance=Provenance.UNRESOLVED,
            reason=(
                f"warehouse batch is {batch_assessment.validity.value.lower()} and the supplier "
                f"batch cannot be independently corroborated against product metadata for SKU {item.sku}"
            ),
            rules_applied=["R002", "R007"],
            rejected_claim_ids=[warehouse_claim_id, supplier_claim_id],
        ),
        updates,
    )


def resolve_best_before(
    item: WarehouseItem,
    batch_resolution: ResolvedField,
    known_batches: list[KnownBatch],
) -> tuple[ResolvedField, list[ClaimStatusUpdate]]:
    """Resolve best_before. Only trusted for restock bucketing when batch identity is resolved.

    Uses the known-batch's best_before when the batch was corroborated
    against metadata (that value is independently sourced). Falls back to
    the warehouse label reading when the batch resolved directly with no
    metadata involved. If batch identity is unresolved, best_before is
    unresolved too, a bucket cannot be trusted for stock whose identity is
    unknown (see R007 and allocation.py).

    If the warehouse's own best-before reading disagrees with the
    corroborated batch's metadata, the metadata wins (the batch identity is
    independently confirmed, a date-label misread is exactly the kind of
    warehouse error this system is built to catch), but the disagreement is
    never silent: the warehouse's claim is marked REJECTED with the
    specific conflicting value on record, rather than left ACCEPTED while a
    different value quietly wins the resolved field.
    """
    warehouse_claim_id = f"{item.item_id}:warehouse:best_before"
    updates: list[ClaimStatusUpdate] = []

    if batch_resolution.provenance == Provenance.UNRESOLVED:
        return (
            ResolvedField(
                field=EvidenceField.BEST_BEFORE,
                value=None,
                winning_source=None,
                provenance=Provenance.UNRESOLVED,
                reason="batch identity is unresolved, best-before cannot be trusted for bucketing",
                rules_applied=["R007"],
            ),
            updates,
        )

    if batch_resolution.provenance == Provenance.CORROBORATED and batch_resolution.value is not None:
        known = _find_known_batch(known_batches, str(batch_resolution.value))
        if known is not None and known.best_before is not None:
            reason = "taken from product metadata for the corroborated batch"
            if item.best_before is not None and item.best_before != known.best_before:
                reason += (
                    f", overriding the warehouse's own label reading of "
                    f"{item.best_before.isoformat()}, which disagreed"
                )
                updates.append(
                    ClaimStatusUpdate(
                        claim_id=warehouse_claim_id,
                        status=EvidenceStatus.REJECTED,
                        reason=(
                            f"disagrees with product metadata for the corroborated batch "
                            f"({known.best_before.isoformat()}), metadata preferred since "
                            "batch identity is independently confirmed"
                        ),
                    )
                )
            return (
                ResolvedField(
                    field=EvidenceField.BEST_BEFORE,
                    value=known.best_before,
                    winning_source=EvidenceSource.DERIVED,
                    provenance=Provenance.CORROBORATED,
                    reason=reason,
                    rules_applied=["R003"],
                ),
                updates,
            )

    if item.best_before is not None:
        return (
            ResolvedField(
                field=EvidenceField.BEST_BEFORE,
                value=item.best_before,
                winning_source=EvidenceSource.WAREHOUSE,
                provenance=Provenance.DIRECT,
                reason="warehouse label reading, batch identity independently resolved",
                rules_applied=["R001"],
                accepted_claim_ids=[warehouse_claim_id],
            ),
            updates,
        )

    return (
        ResolvedField(
            field=EvidenceField.BEST_BEFORE,
            value=None,
            winning_source=None,
            provenance=Provenance.UNRESOLVED,
            reason="no best-before value reported by either source",
            rules_applied=["R007"],
        ),
        updates,
    )
