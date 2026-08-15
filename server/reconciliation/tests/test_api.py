"""API tests. The central claim these enforce: the API is an adapter, not
another engine, its output for a given input must match the engine's
direct output field for field.
"""

from __future__ import annotations

import json

import pytest

from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

from ..models import ReconciliationRun

pytestmark = pytest.mark.django_db

API = "/api/v1"


def test_health(client):
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_examples_returns_real_files(client):
    response = client.get(f"{API}/examples")
    assert response.status_code == 200
    names = response.json()["examples"]
    assert "compound_failure" in names
    assert "compound_unresolved" in names
    assert names == sorted(names)


def test_get_example_returns_file_contents(client, compound_failure_payload):
    response = client.get(f"{API}/examples/compound_failure")
    assert response.status_code == 200
    assert response.json() == compound_failure_payload


def test_get_unknown_example_is_404(client):
    response = client.get(f"{API}/examples/does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


@pytest.mark.parametrize(
    "attempt",
    [
        "..%2f..%2f..%2fetc%2fpasswd",
        "..%2Fexamples%2Fcompound_failure",
        "%2e%2e%2f%2e%2e%2fpyproject.toml",
    ],
)
def test_get_example_path_traversal_is_rejected(client, attempt):
    response = client.get(f"{API}/examples/{attempt}")
    assert response.status_code == 404


def test_create_reconciliation_matches_direct_engine_output(client, compound_failure_payload):
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()

    direct_report = reconcile(parse_shipment(compound_failure_payload))
    direct_item = direct_report.items[0]
    api_item = body["audit_report"]["items"][0]

    assert api_item["resolved"] == direct_item.resolved.model_dump(mode="json")
    assert [(a["quantity"], a["route"]) for a in api_item["allocations"]] == [
        (a.quantity, a.route.value) for a in direct_item.allocations
    ]
    assert api_item["rules_applied"] == direct_item.rules_applied
    assert (
        api_item["commercial_decision"]["credit_quantity"]
        == direct_item.commercial_decision.credit_quantity
    )
    assert body["summary_status"] == "RESOLVED"


def test_create_reconciliation_compound_failure_values(client, compound_failure_payload):
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    body = response.json()
    item = body["audit_report"]["items"][0]

    assert item["resolved"]["batch_code"] == "BA1902"
    assert item["resolved"]["best_before_bucket"] == "2026-10"
    routes = {(a["quantity"], a["route"]) for a in item["allocations"]}
    assert routes == {(6, "SCRAP"), (18, "RESTOCK")}
    assert item["commercial_decision"]["credit_quantity"] == 4
    assert body["summary_status"] == "RESOLVED"
    assert body["quantity_received"] == 24


def test_create_reconciliation_compound_unresolved_requires_review(
    client, compound_unresolved_payload
):
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_unresolved_payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    item = body["audit_report"]["items"][0]

    assert item["resolved"]["batch_code"] is None
    assert [(a["quantity"], a["route"]) for a in item["allocations"]] == [(15, "QUARANTINE")]
    assert body["summary_status"] == "REQUIRES_REVIEW"


def test_create_reconciliation_persists_input_and_report(client, compound_failure_payload):
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    run_id = response.json()["id"]
    run = ReconciliationRun.objects.get(id=run_id)

    assert run.input_payload == compound_failure_payload
    assert run.audit_report["return_id"] == compound_failure_payload["return_id"]
    assert run.summary_status == "RESOLVED"


def test_create_reconciliation_records_scenario_name(client, compound_failure_payload):
    response = client.post(
        f"{API}/reconciliations?scenario_name=compound_failure",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    assert response.json()["scenario_name"] == "compound_failure"


def test_create_reconciliation_invalid_payload_returns_structured_422(client):
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps({"return_id": "RET-BAD"}),
        content_type="application/json",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]
    assert any("warehouse_report" in d["path"] for d in body["details"])


def test_create_reconciliation_negative_quantity_returns_field_path(client, compound_failure_payload):
    broken = json.loads(json.dumps(compound_failure_payload))
    broken["warehouse_report"]["items"][0]["quantity_received"] = -1
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(broken),
        content_type="application/json",
    )
    assert response.status_code == 422
    paths = [d["path"] for d in response.json()["details"]]
    assert any("quantity_received" in p for p in paths)


def test_list_reconciliations_returns_persisted_runs(client, compound_failure_payload):
    client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    response = client.get(f"{API}/reconciliations")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["return_id"] == compound_failure_payload["return_id"]
    assert runs[0]["conflict_count"] == 3


def test_list_reconciliations_includes_route_totals(client, compound_failure_payload):
    client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    response = client.get(f"{API}/reconciliations")
    assert response.json()[0]["route_totals"] == {"SCRAP": 6, "RESTOCK": 18}


def test_retrieve_reconciliation_by_id(client, compound_failure_payload):
    create = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    run_id = create.json()["id"]

    response = client.get(f"{API}/reconciliations/{run_id}")
    assert response.status_code == 200
    assert response.json()["id"] == run_id
    assert "audit_report" in response.json()


def test_retrieve_unknown_reconciliation_is_404(client):
    response = client.get(f"{API}/reconciliations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_delete_reconciliation(client, compound_failure_payload):
    create = client.post(
        f"{API}/reconciliations",
        data=json.dumps(compound_failure_payload),
        content_type="application/json",
    )
    run_id = create.json()["id"]

    delete_response = client.delete(f"{API}/reconciliations/{run_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"{API}/reconciliations/{run_id}")
    assert get_response.status_code == 404


def test_create_reconciliation_malformed_batch_pattern_returns_structured_422(client):
    """HIGH-1 regression: a malformed custom batch_pattern must surface as the
    application's normal structured validation response, never as a bare 500
    internal_error, and never as a silent QUARANTINE. Deliberately does not
    assert on Python's exact re.error wording, only on the shape of the
    response and that it names the offending field.
    """
    payload = {
        "return_id": "RET-BAD-PATTERN",
        "warehouse_report": {
            "items": [
                {
                    "item_id": "X1",
                    "sku": "BAD-SKU",
                    "quantity_received": 5,
                    "condition": "GOOD",
                    "damaged_quantity": 0,
                    "batch_code": "AB1234",
                }
            ]
        },
        "supplier_events": [],
        "product_metadata": [{"sku": "BAD-SKU", "batch_pattern": "(unclosed["}],
    }
    response = client.post(
        f"{API}/reconciliations",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["message"]
    assert body["details"]
    assert any("batch_pattern" in d["path"] for d in body["details"])
    assert any(d["message"] for d in body["details"])
    assert not ReconciliationRun.objects.exists()


def test_openapi_docs_available(client):
    docs = client.get(f"{API}/docs")
    schema = client.get(f"{API}/openapi.json")
    assert docs.status_code == 200
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert f"{API}/health" in paths
    assert f"{API}/reconciliations" in paths
