"""Conflict detection: surface disagreement between sources, do not resolve it.

Three required conflict types. Detection only records what disagrees and
why it counts as a disagreement, resolution is policies.py's job.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from returnproof.enums import Condition, ConflictType, SupplierInstruction
from returnproof.models import SupplierEvent, WarehouseItem
from returnproof.temporal import SupplierEventResolution
from returnproof.validation import BatchAssessment, classify_batch


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    type: ConflictType
    item_id: str
    description: str
    claim_ids: list[str]


def detect_condition_disagreement(
    item: WarehouseItem, current_event: SupplierEvent | None
) -> Conflict | None:
    """Warehouse condition and the supplier's routing preference point different ways.

    Two directions, both flagged the same way. Warehouse reports anything
    other than GOOD (damaged, or condition unknown) while the supplier
    instructs RESTOCK. Or warehouse reports GOOD while the supplier
    instructs SCRAP, a supplier disposition instruction against physically
    intact stock is just as much a disagreement as the reverse, and
    ignoring it would be an unstated bias toward the warehouse.
    """
    if current_event is None or current_event.instruction is None:
        return None

    if item.condition != Condition.GOOD and current_event.instruction == SupplierInstruction.RESTOCK:
        return Conflict(
            conflict_id=f"{item.item_id}:condition_disagreement",
            type=ConflictType.CONDITION_DISAGREEMENT,
            item_id=item.item_id,
            description=(
                f"warehouse reports condition {item.condition.value} "
                f"but supplier event {current_event.event_id} instructs RESTOCK"
            ),
            claim_ids=[
                f"{item.item_id}:warehouse:condition",
                f"{item.item_id}:supplier:{current_event.event_id}:instruction",
            ],
        )

    if item.condition == Condition.GOOD and current_event.instruction == SupplierInstruction.SCRAP:
        return Conflict(
            conflict_id=f"{item.item_id}:condition_disagreement",
            type=ConflictType.CONDITION_DISAGREEMENT,
            item_id=item.item_id,
            description=(
                f"warehouse reports condition GOOD but supplier event "
                f"{current_event.event_id} instructs SCRAP"
            ),
            claim_ids=[
                f"{item.item_id}:warehouse:condition",
                f"{item.item_id}:supplier:{current_event.event_id}:instruction",
            ],
        )

    return None


def detect_supplier_state_ambiguity(item_id: str, resolution: SupplierEventResolution) -> Conflict | None:
    """Two or more supplier events tie on ordering with genuinely different content.

    See temporal.py, `resolution.ambiguous`. Surfaced as a conflict in its
    own right rather than only as a note in reasoning text, so it shows up
    in the same structured list a reviewer already checks for the other
    three conflict types.
    """
    if not resolution.ambiguous:
        return None
    claim_ids = [
        f"{item_id}:supplier:{event.event_id}:{field}"
        for event in resolution.tied
        for field in ("batch_code", "acknowledged_quantity", "credit_eligible", "credit_quantity", "instruction")
        if getattr(event, field) is not None
    ]
    tied_ids = ", ".join(e.event_id for e in resolution.tied)
    return Conflict(
        conflict_id=f"{item_id}:supplier_state_ambiguous",
        type=ConflictType.SUPPLIER_STATE_AMBIGUOUS,
        item_id=item_id,
        description=(
            f"supplier events {tied_ids} tie on {resolution.ordering_basis} with conflicting "
            "content, current supplier state cannot be determined"
        ),
        claim_ids=claim_ids,
    )


def detect_batch_mismatch(
    item: WarehouseItem,
    batch_assessment: BatchAssessment,
    current_event: SupplierEvent | None,
    batch_pattern: str | None = None,
) -> Conflict | None:
    """Warehouse batch is unusable, or warehouse and supplier batches disagree."""
    if current_event is None or current_event.batch_code is None:
        return None

    supplier_assessment = classify_batch(current_event.batch_code, batch_pattern)
    warehouse_usable = batch_assessment.normalized_value
    supplier_normalized = supplier_assessment.normalized_value

    if warehouse_usable is None:
        description = (
            f"warehouse batch code is {batch_assessment.validity.value.lower()}, "
            f"supplier reports {current_event.batch_code!r}"
        )
    elif warehouse_usable != supplier_normalized:
        description = (
            f"warehouse batch {batch_assessment.raw_value!r} does not match "
            f"supplier batch {current_event.batch_code!r}"
        )
    else:
        return None

    return Conflict(
        conflict_id=f"{item.item_id}:batch_mismatch",
        type=ConflictType.BATCH_MISMATCH,
        item_id=item.item_id,
        description=description,
        claim_ids=[
            f"{item.item_id}:warehouse:batch_code",
            f"{item.item_id}:supplier:{current_event.event_id}:batch_code",
        ],
    )


def detect_quantity_or_eligibility_disputes(
    item: WarehouseItem, current_event: SupplierEvent | None
) -> list[Conflict]:
    """Physical and commercial quantity fields disagreeing. Kept as distinct disputes.

    quantity_received vs acknowledged_quantity is a receiving-count dispute.
    damaged_quantity vs credit_quantity is a separate, commercial-scope
    dispute, they describe different things (what was physically damaged
    vs what the supplier will credit) and are never assumed to be the same
    field under two names.
    """
    if current_event is None:
        return []

    conflicts: list[Conflict] = []

    if (
        current_event.acknowledged_quantity is not None
        and current_event.acknowledged_quantity != item.quantity_received
    ):
        conflicts.append(
            Conflict(
                conflict_id=f"{item.item_id}:quantity_received_dispute",
                type=ConflictType.QUANTITY_OR_ELIGIBILITY_DISPUTE,
                item_id=item.item_id,
                description=(
                    f"warehouse received {item.quantity_received} units, "
                    f"supplier acknowledged {current_event.acknowledged_quantity}"
                ),
                claim_ids=[
                    f"{item.item_id}:warehouse:quantity_received",
                    f"{item.item_id}:supplier:{current_event.event_id}:acknowledged_quantity",
                ],
            )
        )

    if (
        item.damaged_quantity > 0
        and current_event.credit_quantity is not None
        and current_event.credit_quantity != item.damaged_quantity
    ):
        conflicts.append(
            Conflict(
                conflict_id=f"{item.item_id}:credit_quantity_dispute",
                type=ConflictType.QUANTITY_OR_ELIGIBILITY_DISPUTE,
                item_id=item.item_id,
                description=(
                    f"warehouse recorded {item.damaged_quantity} damaged units, "
                    f"supplier credits {current_event.credit_quantity}"
                ),
                claim_ids=[
                    f"{item.item_id}:warehouse:quantity_received",
                    f"{item.item_id}:supplier:{current_event.event_id}:credit_quantity",
                ],
            )
        )

    if (
        current_event.credit_quantity is not None
        and current_event.acknowledged_quantity is not None
        and current_event.credit_quantity > current_event.acknowledged_quantity
    ):
        conflicts.append(
            Conflict(
                conflict_id=f"{item.item_id}:commercial_inconsistency",
                type=ConflictType.QUANTITY_OR_ELIGIBILITY_DISPUTE,
                item_id=item.item_id,
                description=(
                    f"supplier-internal inconsistency on event {current_event.event_id}: "
                    f"credit_quantity ({current_event.credit_quantity}) exceeds its own "
                    f"acknowledged_quantity ({current_event.acknowledged_quantity})"
                ),
                claim_ids=[
                    f"{item.item_id}:supplier:{current_event.event_id}:acknowledged_quantity",
                    f"{item.item_id}:supplier:{current_event.event_id}:credit_quantity",
                ],
            )
        )

    return conflicts


def detect_conflicts(
    item: WarehouseItem,
    batch_assessment: BatchAssessment,
    current_event: SupplierEvent | None,
    batch_pattern: str | None = None,
) -> list[Conflict]:
    """Run all conflict detectors for one item and return whatever they found."""
    conflicts: list[Conflict] = []

    condition_conflict = detect_condition_disagreement(item, current_event)
    if condition_conflict is not None:
        conflicts.append(condition_conflict)

    batch_conflict = detect_batch_mismatch(item, batch_assessment, current_event, batch_pattern)
    if batch_conflict is not None:
        conflicts.append(batch_conflict)

    conflicts.extend(detect_quantity_or_eligibility_disputes(item, current_event))

    return conflicts
