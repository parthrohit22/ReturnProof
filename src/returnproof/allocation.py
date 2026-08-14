"""Partial physical allocation, best-before bucketing, and the conservation invariant.

An item's received quantity is split into one or more allocations, each
with its own route. Routes are derived here, they are never a direct copy
of either source's stated preference (see policies.py's field authority
table, physical route has no single authoritative source).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from returnproof.enums import Condition, Provenance, Route, SupplierInstruction
from returnproof.models import SupplierEvent, WarehouseItem
from returnproof.policies import ResolvedField


class Allocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int
    route: Route
    reason: str
    best_before_bucket: str | None = None
    context: str


class RejectedAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route
    reason: str


class InvariantCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    detail: str


def _route_for_damage(condition: Condition) -> tuple[Route, str]:
    if condition == Condition.DAMAGED_UNSAFE:
        return Route.SCRAP, "unsafe_damage"
    if condition == Condition.DAMAGED_SALVAGEABLE:
        return Route.QUARANTINE, "salvageable_damage"
    return Route.QUARANTINE, "unknown_condition"


def _damaged_allocation(quantity: int, condition: Condition) -> Allocation:
    route, context = _route_for_damage(condition)
    if route == Route.SCRAP:
        reason = (
            f"{condition.value} confirmed by warehouse inspection, "
            "unsafe for restock regardless of supplier instruction"
        )
    elif context == "salvageable_damage":
        reason = (
            f"{condition.value} damage, not confirmed unsafe but not confirmed "
            "restockable either, held for manual inspection"
        )
    else:
        reason = "condition could not be classified, held for manual inspection"
    return Allocation(quantity=quantity, route=route, reason=reason, context=context)


def _good_allocation(
    quantity: int, best_before: ResolvedField, current_event: SupplierEvent | None
) -> Allocation:
    if current_event is not None and current_event.instruction == SupplierInstruction.SCRAP:
        return Allocation(
            quantity=quantity,
            route=Route.QUARANTINE,
            reason=(
                "warehouse reports GOOD condition but the supplier instructs SCRAP, "
                "physical evidence does not justify destruction and the disagreement "
                "is not resolved automatically"
            ),
            context="supplier_disputes_restock",
        )
    if best_before.provenance in (Provenance.DIRECT, Provenance.CORROBORATED) and isinstance(
        best_before.value, date
    ):
        bucket = best_before.value.strftime("%Y-%m")
        return Allocation(
            quantity=quantity,
            route=Route.RESTOCK,
            reason="intact stock with resolved batch identity and best-before date",
            best_before_bucket=bucket,
            context="resolved_good",
        )
    return Allocation(
        quantity=quantity,
        route=Route.QUARANTINE,
        reason=(
            "stock is physically intact but batch identity or best-before date "
            "is unresolved, held for manual inspection rather than guessed"
        ),
        context="unresolved_identity",
    )


def build_allocations(
    item: WarehouseItem, best_before: ResolvedField, current_event: SupplierEvent | None
) -> list[Allocation]:
    """Split quantity_received into routed allocations.

    If damaged_quantity is set, it is treated as the damaged subset and the
    remainder is the intact subset. If damaged_quantity is zero, the whole
    quantity_received shares item.condition (no partial breakdown was
    reported), and is routed as a single allocation.

    `current_event` is the resolved current supplier event (already
    temporally resolved, never raw array order), used only to check for an
    explicit SCRAP disposition instruction against otherwise-good stock,
    see `_good_allocation`. No other field of it drives physical routing.
    """
    allocations: list[Allocation] = []
    damaged_qty = item.damaged_quantity
    intact_qty = item.quantity_received - damaged_qty

    if damaged_qty > 0:
        allocations.append(_damaged_allocation(damaged_qty, item.condition))
        if intact_qty > 0:
            allocations.append(_good_allocation(intact_qty, best_before, current_event))
    elif item.quantity_received > 0:
        if item.condition == Condition.GOOD:
            allocations.append(_good_allocation(item.quantity_received, best_before, current_event))
        else:
            allocations.append(_damaged_allocation(item.quantity_received, item.condition))

    return allocations


def check_conservation(item: WarehouseItem, allocations: list[Allocation]) -> InvariantCheck:
    """R006: scrap + restock + quarantine must equal quantity_received, exactly."""
    allocated = sum(a.quantity for a in allocations)
    passed = allocated == item.quantity_received
    detail = f"{item.quantity_received} received, {allocated} allocated"
    return InvariantCheck(name="R006_QUANTITY_CONSERVATION", passed=passed, detail=detail)


_ALL_ROUTES = (Route.RESTOCK, Route.SCRAP, Route.QUARANTINE)

_ALTERNATIVE_REASONS: dict[str, dict[Route, str]] = {
    "unsafe_damage": {
        Route.RESTOCK: "physical damage was confirmed unsafe, restocking it would ship unsafe stock",
        Route.QUARANTINE: "damage is conclusively unsafe, holding it for inspection would not change the outcome",
    },
    "salvageable_damage": {
        Route.RESTOCK: "damage is present and not yet confirmed safe, cannot restock without inspection",
        Route.SCRAP: "damage is not proven to be irreversible, scrapping now would be premature",
    },
    "unknown_condition": {
        Route.RESTOCK: "condition could not be classified, cannot assume it is safe to restock",
        Route.SCRAP: "condition could not be classified, cannot assume it is unsalvageable",
    },
    "unresolved_identity": {
        Route.RESTOCK: "batch identity or best-before date is unresolved, cannot assign a restock bucket",
        Route.SCRAP: "stock is physically intact, there is no damage evidence to justify scrapping",
    },
    "resolved_good": {
        Route.SCRAP: "no evidence of damage in this portion",
        Route.QUARANTINE: "identity and condition are both sufficiently resolved, no need for manual inspection",
    },
    "supplier_disputes_restock": {
        Route.RESTOCK: (
            "the supplier explicitly instructed SCRAP, restocking despite a stated "
            "disposition instruction would ignore a directly conflicting signal"
        ),
        Route.SCRAP: (
            "warehouse reports the item in good physical condition, there is no "
            "physical evidence to justify destruction on the strength of a commercial "
            "instruction alone"
        ),
    },
}


def explain_alternatives(allocation: Allocation) -> list[RejectedAlternative]:
    """Why the routes not chosen were rejected, for the audit's rejected_alternatives."""
    reasons = _ALTERNATIVE_REASONS.get(allocation.context, {})
    return [
        RejectedAlternative(route=route, reason=reasons[route])
        for route in _ALL_ROUTES
        if route != allocation.route and route in reasons
    ]
