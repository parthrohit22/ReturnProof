"""Application orchestration: validate, reconcile, persist.

This is the only place Django touches the reconciliation engine, and all
it does is call it. `parse_shipment` and `reconcile` are the exact
functions the CLI calls, unmodified, this module adds no decision logic of
its own, only a persistence step after the engine has already decided.
"""

from __future__ import annotations

from typing import Any

from returnproof.audit import ReturnAuditReport
from returnproof.enums import Route
from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

from .models import ReconciliationRun, SummaryStatus


def derive_summary_status(report: ReturnAuditReport) -> str:
    """RESOLVED if every allocation across every item is RESTOCK or SCRAP.
    REQUIRES_REVIEW if any quantity anywhere is QUARANTINE.

    This is the only distinction the engine's own output supports without
    guessing. A `PARTIAL` status was considered and deliberately left out,
    see the README, an "item partly resolved" label would need a rule for
    what counts as partial that the engine itself doesn't define.
    """
    any_quarantined = any(
        allocation.route == Route.QUARANTINE for item in report.items for allocation in item.allocations
    )
    return SummaryStatus.REQUIRES_REVIEW if any_quarantined else SummaryStatus.RESOLVED


def run_reconciliation(payload: dict[str, Any], scenario_name: str | None = None) -> ReconciliationRun:
    """Validate, reconcile, and persist one return shipment.

    Raises `returnproof.exceptions.InputValidationError` on invalid input.
    Callers (the API layer) map that to a structured HTTP response, this
    function doesn't catch it itself, there's nothing useful to add.
    """
    shipment = parse_shipment(payload)
    report = reconcile(shipment)
    return ReconciliationRun.objects.create(
        return_id=report.return_id,
        scenario_name=scenario_name,
        input_payload=payload,
        audit_report=report.model_dump(mode="json"),
        summary_status=derive_summary_status(report),
    )
