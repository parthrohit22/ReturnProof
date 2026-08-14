"""Read-only queries against persisted reconciliation runs."""

from __future__ import annotations

import uuid

from django.db.models import QuerySet

from .models import ReconciliationRun


def list_runs() -> QuerySet[ReconciliationRun]:
    return ReconciliationRun.objects.all()


def get_run(run_id: uuid.UUID) -> ReconciliationRun:
    """Raises `ReconciliationRun.DoesNotExist` for an unknown id, mapped to
    a 404 at the API layer."""
    return ReconciliationRun.objects.get(id=run_id)
