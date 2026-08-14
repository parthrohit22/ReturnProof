"""The second compound scenario: both mandatory failures, with insufficient
evidence to safely resolve identity. Proves the engine quarantines rather
than guesses when corroboration genuinely isn't available.
"""

import json
from pathlib import Path

from returnproof.enums import EvidenceStatus, Route
from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "compound_unresolved.json"


def _load_shipment():
    raw = json.loads(EXAMPLE_PATH.read_text())
    return parse_shipment(raw)


def test_batch_identity_is_unresolved_not_guessed():
    report = reconcile(_load_shipment())
    record = report.items[0]

    assert record.resolved.batch_code is None
    assert record.resolved.best_before_bucket is None


def test_all_stock_quarantined_when_evidence_is_insufficient():
    report = reconcile(_load_shipment())
    record = report.items[0]

    assert len(record.allocations) == 1
    assert record.allocations[0].route == Route.QUARANTINE
    assert record.allocations[0].quantity == 15


def test_out_of_order_events_still_correctly_resolved_despite_unresolved_batch():
    report = reconcile(_load_shipment())
    record = report.items[0]

    stale_claims = [c for c in record.evidence if c.source_reference == "evt-1"]
    assert stale_claims and all(c.status == EvidenceStatus.SUPERSEDED for c in stale_claims)
    assert "R004" in record.rules_applied


def test_conservation_invariant_still_passes():
    report = reconcile(_load_shipment())
    assert report.summary.invariants_passed is True


def test_reasoning_does_not_fabricate_certainty():
    report = reconcile(_load_shipment())
    record = report.items[0]
    joined = " ".join(record.reasoning)
    assert "unresolved" in joined.lower() or "UNRESOLVED" in joined
