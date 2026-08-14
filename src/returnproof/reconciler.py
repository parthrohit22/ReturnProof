"""Pipeline orchestration: wires evidence, temporal resolution, conflicts, and
policy into one ItemAuditRecord per warehouse item, then a ReturnAuditReport.

This module makes decisions by calling into policies.py / allocation.py, it
does not invent new rules of its own, it only sequences them and builds the
audit trail.
"""

from __future__ import annotations

from returnproof.allocation import build_allocations, check_conservation, explain_alternatives
from returnproof.audit import (
    AllocationExplanation,
    CommercialDecision,
    ItemAuditRecord,
    ResolvedSummary,
    ReturnAuditReport,
    ReturnSummary,
)
from returnproof.conflicts import ConflictType, detect_conflicts, detect_supplier_state_ambiguity
from returnproof.enums import EvidenceField, EvidenceStatus, Route
from returnproof.evidence import EvidenceClaim, extract_supplier_claims, extract_warehouse_claims
from returnproof.models import ReturnShipment, WarehouseItem
from returnproof.policies import (
    resolve_batch,
    resolve_best_before,
    resolve_supplier_only_field,
    resolve_warehouse_only_field,
)
from returnproof.temporal import resolve_supplier_state
from returnproof.validation import classify_batch


def _apply_claim_updates(claims: list[EvidenceClaim], updates: list) -> None:
    by_id = {claim.claim_id: claim for claim in claims}
    for update in updates:
        claim = by_id.get(update.claim_id)
        if claim is not None:
            claim.status = update.status
            claim.reason = update.reason


def _reconcile_item(item: WarehouseItem, shipment: ReturnShipment) -> ItemAuditRecord:
    batch_pattern = shipment.batch_pattern_for_sku(item.sku)
    batch_assessment = classify_batch(item.batch_code, batch_pattern)
    item_events = [e for e in shipment.supplier_events if e.item_id == item.item_id]
    supplier_resolution = resolve_supplier_state(item_events)
    known_batches = shipment.known_batches_for_sku(item.sku)

    claims: list[EvidenceClaim] = extract_warehouse_claims(item, batch_assessment)
    claims.extend(extract_supplier_claims(supplier_resolution))

    conflicts = detect_conflicts(item, batch_assessment, supplier_resolution.current, batch_pattern)
    ambiguity_conflict = detect_supplier_state_ambiguity(item.item_id, supplier_resolution)
    if ambiguity_conflict is not None:
        conflicts.append(ambiguity_conflict)

    batch_resolved, batch_updates = resolve_batch(
        item, batch_assessment, supplier_resolution.current, known_batches
    )
    _apply_claim_updates(claims, batch_updates)

    best_before_resolved, best_before_updates = resolve_best_before(item, batch_resolved, known_batches)
    _apply_claim_updates(claims, best_before_updates)
    condition_resolved = resolve_warehouse_only_field(
        item, EvidenceField.CONDITION, item.condition, rule="R001"
    )
    quantity_resolved = resolve_warehouse_only_field(
        item, EvidenceField.QUANTITY_RECEIVED, item.quantity_received
    )
    credit_eligible_resolved = resolve_supplier_only_field(
        item.item_id, EvidenceField.CREDIT_ELIGIBLE, supplier_resolution.current
    )
    credit_quantity_resolved = resolve_supplier_only_field(
        item.item_id, EvidenceField.CREDIT_QUANTITY, supplier_resolution.current
    )

    allocations = build_allocations(item, best_before_resolved, supplier_resolution.current)

    has_condition_conflict = any(
        c.type == ConflictType.CONDITION_DISAGREEMENT for c in conflicts
    )
    safety_override_applied = False
    if has_condition_conflict and supplier_resolution.current is not None:
        for allocation in allocations:
            if allocation.context == "unsafe_damage":
                safety_override_applied = True
                instruction_claim_id = (
                    f"{item.item_id}:supplier:{supplier_resolution.current.event_id}:instruction"
                )
                by_id = {c.claim_id: c for c in claims}
                instruction_claim = by_id.get(instruction_claim_id)
                if instruction_claim is not None and instruction_claim.status != EvidenceStatus.SUPERSEDED:
                    instruction_claim.status = EvidenceStatus.REJECTED
                    instruction_claim.reason = (
                        "overridden by physical safety override (R005): "
                        "warehouse confirmed unsafe damage"
                    )

    invariants = [check_conservation(item, allocations)]

    rules_applied: set[str] = set()
    for resolved in (
        batch_resolved,
        best_before_resolved,
        condition_resolved,
        quantity_resolved,
        credit_eligible_resolved,
        credit_quantity_resolved,
    ):
        rules_applied.update(resolved.rules_applied)
    if supplier_resolution.superseded or supplier_resolution.ambiguous:
        rules_applied.add("R004")
    if safety_override_applied:
        rules_applied.add("R005")
    if any(a.route == Route.QUARANTINE for a in allocations):
        rules_applied.add("R007")
    rules_applied.add("R006")

    rejected_alternatives = [
        AllocationExplanation(
            quantity=a.quantity,
            route=a.route.value,
            reason=a.reason,
            best_before_bucket=a.best_before_bucket,
            rejected_alternatives=explain_alternatives(a),
        )
        for a in allocations
    ]

    commercial_reason = credit_eligible_resolved.reason
    commercial_decision = CommercialDecision(
        credit_eligible=credit_eligible_resolved.value,
        credit_quantity=credit_quantity_resolved.value,
        reason=commercial_reason,
        rules_applied=sorted(set(credit_eligible_resolved.rules_applied + credit_quantity_resolved.rules_applied)),
    )

    resolved_summary = ResolvedSummary(
        condition=item.condition,
        batch_code=batch_resolved.value,
        best_before_bucket=(
            best_before_resolved.value.strftime("%Y-%m")
            if best_before_resolved.value is not None
            else None
        ),
    )

    reasoning = _build_reasoning(
        item=item,
        batch_assessment_valid=batch_assessment.validity.value,
        batch_resolved=batch_resolved,
        best_before_resolved=best_before_resolved,
        supplier_resolution=supplier_resolution,
        conflicts=conflicts,
        allocations=allocations,
        commercial_decision=commercial_decision,
    )

    return ItemAuditRecord(
        item_id=item.item_id,
        sku=item.sku,
        resolved=resolved_summary,
        conflicts=conflicts,
        evidence=claims,
        resolved_fields=[
            condition_resolved,
            quantity_resolved,
            batch_resolved,
            best_before_resolved,
            credit_eligible_resolved,
            credit_quantity_resolved,
        ],
        rules_applied=sorted(rules_applied),
        allocations=allocations,
        commercial_decision=commercial_decision,
        invariants=invariants,
        reasoning=reasoning,
        rejected_alternatives=rejected_alternatives,
    )


def _build_reasoning(
    *,
    item: WarehouseItem,
    batch_assessment_valid: str,
    batch_resolved,
    best_before_resolved,
    supplier_resolution,
    conflicts,
    allocations,
    commercial_decision,
) -> list[str]:
    lines: list[str] = []
    lines.append(
        f"Condition: warehouse reports {item.condition.value} "
        f"({item.damaged_quantity} of {item.quantity_received} units affected), direct observation (R001)."
    )
    lines.append(
        f"Batch: resolved to {batch_resolved.value!r} "
        f"[{batch_resolved.provenance.value}]. {batch_resolved.reason}."
    )
    if supplier_resolution.current is not None:
        lines.append(
            f"Supplier timeline: current event {supplier_resolution.current.event_id} "
            f"accepted ({supplier_resolution.reasoning})."
        )
        if supplier_resolution.current.instruction is not None:
            lines.append(
                f"Supplier instruction: {supplier_resolution.current.instruction.value} "
                f"(event {supplier_resolution.current.event_id}), a routing preference weighed "
                "against physical evidence, not followed automatically."
            )
        for stale in supplier_resolution.superseded:
            lines.append(f"Supplier timeline: event {stale.event_id} marked SUPERSEDED.")
    elif supplier_resolution.ambiguous:
        lines.append(f"Supplier timeline: {supplier_resolution.reasoning}.")
    if conflicts:
        lines.append(f"Conflicts detected: {', '.join(c.type.value for c in conflicts)}.")
    for allocation in allocations:
        bucket = f" / {allocation.best_before_bucket}" if allocation.best_before_bucket else ""
        lines.append(f"Routing: {allocation.quantity} -> {allocation.route.value}{bucket} ({allocation.reason}).")
    r008_suffix = ", kept separate from physical routing (R008)" if "R008" in commercial_decision.rules_applied else ""
    lines.append(
        f"Commercial: credit_eligible={commercial_decision.credit_eligible}, "
        f"credit_quantity={commercial_decision.credit_quantity}{r008_suffix}."
    )
    return lines


def reconcile(shipment: ReturnShipment) -> ReturnAuditReport:
    """Reconcile every item in a return shipment into a full audit report."""
    items = [_reconcile_item(item, shipment) for item in shipment.warehouse_report.items]
    conflict_count = sum(len(item.conflicts) for item in items)
    invariants_passed = all(check.passed for item in items for check in item.invariants)
    return ReturnAuditReport(
        return_id=shipment.return_id,
        items=items,
        summary=ReturnSummary(
            item_count=len(items),
            conflict_count=conflict_count,
            invariants_passed=invariants_passed,
        ),
    )
