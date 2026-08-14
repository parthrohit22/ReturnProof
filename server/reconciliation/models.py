"""Application history, not decision logic.

`ReconciliationRun` stores a snapshot of what was submitted and what the
`returnproof` engine decided about it. Nothing here re-derives, re-checks,
or overrides a decision, `summary_status` is a coarse, deterministically
derived label for the queue view, computed once in services.py from the
engine's own output, not a second opinion.
"""

from __future__ import annotations

import uuid

from django.db import models


class SummaryStatus(models.TextChoices):
    RESOLVED = "RESOLVED", "Resolved"
    REQUIRES_REVIEW = "REQUIRES_REVIEW", "Requires review"


class ReconciliationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_id = models.CharField(max_length=255)
    scenario_name = models.CharField(max_length=255, blank=True, null=True)
    input_payload = models.JSONField()
    audit_report = models.JSONField()
    summary_status = models.CharField(max_length=32, choices=SummaryStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.return_id} ({self.summary_status})"
