"""Supplier event ordering: business state, not message arrival order.

Policy (R004 SUPPLIER_TEMPORAL_ORDERING, documented here because this is
where it is enforced):

1. If every event for an item carries a ``version``, version order decides
   the current state. Version is an explicit business-state counter from
   the supplier, when present for all events it is the least ambiguous
   signal available.
2. Otherwise, ``event_timestamp`` order decides the current state. This is
   when the supplier says the state became true, not when we heard about
   it.
3. ``received_at`` is never used to order state. It is retained on every
   event purely as audit metadata (useful for spotting delivery delays),
   and only breaks ties in the human-readable ordering trace, never in the
   decision itself.

Mixed inputs (some events have a version, some do not) fall back to rule 2
for the whole item rather than partially trusting version, comparing a
versioned event against an unversioned one has no defined meaning.

Sorting is by explicit key, not input array order, so passing the same
logical events in a different array order produces an identical result.
``event_id`` only breaks ties among events that agree on every
decision-relevant field (see below), it never breaks a genuine tie.

Two or more events can legitimately tie on the ordering key (same version,
or same event_timestamp with no version). That is handled two ways:

- If the tied events agree on every decision-relevant field (batch_code,
  acknowledged_quantity, credit_eligible, credit_quantity, instruction),
  they're the same logical event delivered more than once (a retry), not a
  conflict. One is kept as current, deterministically (lowest event_id),
  the rest are marked superseded as duplicates, not as replaced state.
- If they disagree on any of those fields, there is no defensible way to
  pick a winner. Supplier state is reported unresolved rather than
  guessed: `current` is None, the tied events are exposed in `tied`, and
  the resolution is flagged `ambiguous`, which downstream code treats the
  same as "no current supplier event" for every field that would
  otherwise come from the supplier.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from returnproof.models import SupplierEvent

_MATERIAL_FIELDS = (
    "batch_code",
    "acknowledged_quantity",
    "credit_eligible",
    "credit_quantity",
    "instruction",
)


class SupplierEventResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    current: SupplierEvent | None
    superseded: list[SupplierEvent]
    tied: list[SupplierEvent] = []
    ambiguous: bool = False
    ordering_basis: str
    reasoning: str


def _materially_equivalent(events: list[SupplierEvent]) -> bool:
    first = events[0]
    return all(
        all(getattr(event, field) == getattr(first, field) for field in _MATERIAL_FIELDS)
        for event in events[1:]
    )


def resolve_supplier_state(events: list[SupplierEvent]) -> SupplierEventResolution:
    """Resolve the current supplier event for one item's events, marking the rest superseded."""
    if not events:
        return SupplierEventResolution(
            item_id="",
            current=None,
            superseded=[],
            ordering_basis="none",
            reasoning="no supplier events available for this item",
        )

    item_id = events[0].item_id
    use_version = all(event.version is not None for event in events)

    if use_version:
        ordering_basis = "version"
        primary_key = lambda e: e.version
    else:
        ordering_basis = "event_timestamp"
        primary_key = lambda e: e.event_timestamp

    ordered = sorted(events, key=lambda e: (primary_key(e), e.event_id))
    top_key = primary_key(ordered[-1])
    top_group = [e for e in ordered if primary_key(e) == top_key]
    older = [e for e in ordered if primary_key(e) != top_key]

    if len(top_group) == 1:
        current = top_group[0]
        reasoning = (
            f"ordered by {ordering_basis} (current: "
            f"{current.version if use_version else current.event_timestamp.isoformat()}), "
            "received_at ignored for ordering"
        )
        return SupplierEventResolution(
            item_id=item_id,
            current=current,
            superseded=older,
            ordering_basis=ordering_basis,
            reasoning=reasoning,
        )

    if _materially_equivalent(top_group):
        current = min(top_group, key=lambda e: e.event_id)
        duplicates = [e for e in top_group if e.event_id != current.event_id]
        reasoning = (
            f"{len(top_group)} events tie on {ordering_basis} with identical content, "
            f"treated as one logical event delivered more than once (current: {current.event_id})"
        )
        return SupplierEventResolution(
            item_id=item_id,
            current=current,
            superseded=older + duplicates,
            ordering_basis=ordering_basis,
            reasoning=reasoning,
        )

    tied_ids = ", ".join(e.event_id for e in top_group)
    reasoning = (
        f"{len(top_group)} events ({tied_ids}) tie on {ordering_basis} with conflicting "
        "content, no defensible winner, supplier state is unresolved rather than guessed"
    )
    return SupplierEventResolution(
        item_id=item_id,
        current=None,
        superseded=older,
        tied=top_group,
        ambiguous=True,
        ordering_basis=ordering_basis,
        reasoning=reasoning,
    )
