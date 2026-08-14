from returnproof.enums import EvidenceStatus
from returnproof.evidence import extract_supplier_claims
from returnproof.temporal import resolve_supplier_state
from tests.conftest import make_event, ts


def test_received_at_order_does_not_determine_state():
    # Event A: logically newer (later event_timestamp) but arrives first.
    event_a = make_event(event_id="A", instruction="RESTOCK", event_timestamp=ts(14, 2), received_at=ts(13, 58))
    # Event B: logically older but arrives last.
    event_b = make_event(event_id="B", instruction="SCRAP", event_timestamp=ts(13, 55), received_at=ts(14, 5))

    resolution = resolve_supplier_state([event_a, event_b])

    assert resolution.current.event_id == "A"
    assert resolution.superseded[0].event_id == "B"


def test_effective_timestamp_ordering_ascending_case():
    early = make_event(event_id="early", event_timestamp=ts(9, 0))
    late = make_event(event_id="late", event_timestamp=ts(10, 0))

    resolution = resolve_supplier_state([early, late])

    assert resolution.current.event_id == "late"


def test_stale_events_marked_superseded_in_evidence():
    early = make_event(event_id="early", instruction="SCRAP", event_timestamp=ts(9, 0))
    late = make_event(event_id="late", instruction="RESTOCK", event_timestamp=ts(10, 0))

    resolution = resolve_supplier_state([early, late])
    claims = extract_supplier_claims(resolution)

    stale_claims = [c for c in claims if c.source_reference == "early"]
    current_claims = [c for c in claims if c.source_reference == "late"]

    assert stale_claims and all(c.status == EvidenceStatus.SUPERSEDED for c in stale_claims)
    assert current_claims and all(c.status == EvidenceStatus.ACCEPTED for c in current_claims)


def test_ordering_is_independent_of_input_array_order():
    early = make_event(event_id="early", event_timestamp=ts(9, 0))
    late = make_event(event_id="late", event_timestamp=ts(10, 0))

    forward = resolve_supplier_state([early, late])
    reversed_order = resolve_supplier_state([late, early])

    assert forward.current.event_id == reversed_order.current.event_id == "late"


def test_version_takes_precedence_over_event_timestamp_when_all_versioned():
    # v2 has an earlier event_timestamp than v1, but version is the declared
    # tiebreak when every event carries one.
    v1 = make_event(event_id="v1", version=1, event_timestamp=ts(11, 0))
    v2 = make_event(event_id="v2", version=2, event_timestamp=ts(9, 0))

    resolution = resolve_supplier_state([v1, v2])

    assert resolution.current.event_id == "v2"
    assert resolution.ordering_basis == "version"


def test_mixed_versioned_and_unversioned_falls_back_to_event_timestamp():
    versioned = make_event(event_id="versioned", version=1, event_timestamp=ts(9, 0))
    unversioned = make_event(event_id="unversioned", version=None, event_timestamp=ts(10, 0))

    resolution = resolve_supplier_state([versioned, unversioned])

    assert resolution.ordering_basis == "event_timestamp"
    assert resolution.current.event_id == "unversioned"


def test_no_events_returns_none_current():
    resolution = resolve_supplier_state([])
    assert resolution.current is None
    assert resolution.superseded == []
