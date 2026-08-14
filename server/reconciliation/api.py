"""Django Ninja API: the entire HTTP surface of the Operator Console.

This module transports and persists decisions, it does not make them.
Every endpoint either reads persisted `ReconciliationRun` rows or calls
`services.run_reconciliation`, which itself only calls the existing
`returnproof` engine.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.http import HttpRequest
from ninja import Body, NinjaAPI, Query, Status

from returnproof.exceptions import InputValidationError

from . import examples as examples_module
from . import selectors
from .models import ReconciliationRun
from .schemas import ExampleListSchema, RunDetailSchema, RunSummarySchema
from .services import run_reconciliation

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="ReturnProof API",
    version="1.0.0",
    description="Application boundary over the ReturnProof reconciliation engine.",
    urls_namespace="reconciliation",
)


@api.exception_handler(InputValidationError)
def handle_input_validation_error(request: HttpRequest, exc: InputValidationError):
    return api.create_response(
        request,
        {
            "error": "validation_error",
            "message": "The return payload is invalid.",
            "details": exc.errors,
        },
        status=422,
    )


@api.exception_handler(examples_module.ExampleNotFoundError)
def handle_example_not_found(request: HttpRequest, exc: examples_module.ExampleNotFoundError):
    return api.create_response(
        request,
        {"error": "not_found", "message": f"Unknown example: {exc}", "details": []},
        status=404,
    )


@api.exception_handler(ReconciliationRun.DoesNotExist)
def handle_run_not_found(request: HttpRequest, exc: Exception):
    return api.create_response(
        request,
        {"error": "not_found", "message": "Reconciliation run not found.", "details": []},
        status=404,
    )


@api.exception_handler(Exception)
def handle_unexpected_error(request: HttpRequest, exc: Exception):
    # Logged in full for the developer console, never returned to the
    # caller, an unexpected error here is a bug, not something the caller
    # can act on with a traceback.
    logger.exception("Unhandled error in %s %s", request.method, request.path)
    return api.create_response(
        request,
        {"error": "internal_error", "message": "An unexpected error occurred.", "details": []},
        status=500,
    )


@api.get("/health", tags=["health"])
def health(request: HttpRequest) -> dict:
    return {"status": "ok"}


@api.get("/examples", response=ExampleListSchema, tags=["examples"])
def list_examples(request: HttpRequest):
    return {"examples": examples_module.list_example_names()}


@api.get("/examples/{name}", tags=["examples"])
def get_example(request: HttpRequest, name: str):
    return examples_module.load_example(name)


def _to_summary(run: ReconciliationRun) -> dict[str, Any]:
    report = run.audit_report
    allocations = [allocation for item in report["items"] for allocation in item["allocations"]]
    quantity_received = sum(allocation["quantity"] for allocation in allocations)
    route_totals: dict[str, int] = {}
    for allocation in allocations:
        route_totals[allocation["route"]] = route_totals.get(allocation["route"], 0) + allocation["quantity"]
    return {
        "id": run.id,
        "return_id": run.return_id,
        "scenario_name": run.scenario_name,
        "summary_status": run.summary_status,
        "item_count": report["summary"]["item_count"],
        "conflict_count": report["summary"]["conflict_count"],
        "quantity_received": quantity_received,
        "route_totals": route_totals,
        "created_at": run.created_at.isoformat(),
    }


def _to_detail(run: ReconciliationRun) -> dict[str, Any]:
    return {
        **_to_summary(run),
        "input_payload": run.input_payload,
        "audit_report": run.audit_report,
    }


@api.get("/reconciliations", response=list[RunSummarySchema], tags=["reconciliations"])
def list_reconciliations(request: HttpRequest):
    return [_to_summary(run) for run in selectors.list_runs()]


@api.get("/reconciliations/{run_id}", response=RunDetailSchema, tags=["reconciliations"])
def get_reconciliation(request: HttpRequest, run_id: uuid.UUID):
    run = selectors.get_run(run_id)
    return _to_detail(run)


@api.post("/reconciliations", response={201: RunDetailSchema}, tags=["reconciliations"])
def create_reconciliation(
    request: HttpRequest,
    payload: dict[str, Any] = Body(...),
    scenario_name: str | None = Query(None),
):
    run = run_reconciliation(payload, scenario_name=scenario_name)
    return Status(201, _to_detail(run))


@api.delete("/reconciliations/{run_id}", response={204: None}, tags=["reconciliations"])
def delete_reconciliation(request: HttpRequest, run_id: uuid.UUID):
    run = selectors.get_run(run_id)
    run.delete()
    return Status(204, None)
