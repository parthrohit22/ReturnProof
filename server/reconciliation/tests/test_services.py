from __future__ import annotations

import pytest

from returnproof.exceptions import InputValidationError

from ..models import SummaryStatus
from ..services import run_reconciliation

pytestmark = pytest.mark.django_db


def test_run_reconciliation_resolved_status(compound_failure_payload):
    run = run_reconciliation(compound_failure_payload)
    assert run.summary_status == SummaryStatus.RESOLVED
    assert run.pk is not None


def test_run_reconciliation_requires_review_status(compound_unresolved_payload):
    run = run_reconciliation(compound_unresolved_payload)
    assert run.summary_status == SummaryStatus.REQUIRES_REVIEW


def test_run_reconciliation_raises_on_invalid_payload():
    with pytest.raises(InputValidationError):
        run_reconciliation({"return_id": "RET-BAD"})


def test_run_reconciliation_scenario_name_is_optional(compound_failure_payload):
    run = run_reconciliation(compound_failure_payload)
    assert run.scenario_name is None

    named_run = run_reconciliation(compound_failure_payload, scenario_name="compound_failure")
    assert named_run.scenario_name == "compound_failure"
