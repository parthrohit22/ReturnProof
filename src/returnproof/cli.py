"""Typer CLI. Renders the same ReturnAuditReport as Rich text or raw JSON,
there is exactly one decision pipeline, this module only presents it.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from returnproof import __version__
from returnproof.audit import ItemAuditRecord, ReturnAuditReport
from returnproof.exceptions import InputValidationError
from returnproof.reconciler import reconcile
from returnproof.validation import parse_shipment

app = typer.Typer(add_completion=False, help="ReturnProof: evidence-driven stock return reconciliation.")
console = Console()
error_console = Console(stderr=True)

_STATUS_STYLE = {
    "ACCEPTED": "green",
    "CORROBORATED": "green",
    "SUSPECT": "yellow",
    "CORRUPTED": "red",
    "SUPERSEDED": "dim",
    "UNRESOLVED": "yellow",
    "REJECTED": "red",
}

_ROUTE_STYLE = {
    "RESTOCK": "green",
    "SCRAP": "red",
    "QUARANTINE": "yellow",
}


def _status_text(status: str) -> str:
    style = _STATUS_STYLE.get(status, "white")
    return f"[{style}]{status}[/{style}]"


@app.command(name="version")
def version_command() -> None:
    """Print the installed ReturnProof version."""
    console.print(f"returnproof {__version__}")


@app.command(name="reconcile")
def reconcile_command(
    input_path: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to a return shipment JSON file."
    ),
    output: str = typer.Option("human", "--output", "-o", help="Output format: human or json."),
    as_json: bool = typer.Option(False, "--json", help="Shortcut for --output json."),
) -> None:
    """Reconcile a return shipment and print the audit report."""
    if as_json:
        output = "json"
    if output not in ("human", "json"):
        error_console.print(f"[red]Unknown output format: {output!r}, expected 'human' or 'json'.[/red]")
        raise typer.Exit(code=2)

    try:
        raw = json.loads(input_path.read_text())
    except json.JSONDecodeError as exc:
        error_console.print(f"[red]Invalid JSON in {input_path}: {exc}[/red]")
        raise typer.Exit(code=2) from exc

    try:
        shipment = parse_shipment(raw)
    except InputValidationError as exc:
        error_console.print(f"[red]Invalid input in {input_path}:[/red]\n{exc}")
        raise typer.Exit(code=2) from exc

    report = reconcile(shipment)

    if output == "json":
        console.print_json(report.model_dump_json())
    else:
        _render_human(report)

    if not report.summary.invariants_passed:
        error_console.print("[red]One or more items failed the quantity conservation invariant.[/red]")
        raise typer.Exit(code=1)


def _render_human(report: ReturnAuditReport) -> None:
    console.print(
        Panel(
            f"Return: {report.return_id}\n"
            f"Items: {report.summary.item_count}\n"
            f"Conflicts detected: {report.summary.conflict_count}",
            title="ReturnProof",
            border_style="cyan",
        )
    )
    for item in report.items:
        _render_item(item)


def _render_item(item: ItemAuditRecord) -> None:
    console.rule(f"ITEM: {item.item_id}  (SKU {item.sku})", style="cyan")

    warehouse_claims = [c for c in item.evidence if c.source == "WAREHOUSE"]
    table = Table(title="Warehouse Evidence", show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")
    table.add_column("Status")
    for claim in warehouse_claims:
        table.add_row(claim.field.value, str(claim.value), _status_text(claim.status))
    console.print(table)

    supplier_claims = [c for c in item.evidence if c.source == "SUPPLIER"]
    if supplier_claims:
        by_event: dict[str, list] = {}
        for claim in supplier_claims:
            by_event.setdefault(claim.source_reference, []).append(claim)
        table = Table(title="Supplier Timeline", show_header=True, header_style="bold")
        table.add_column("Event")
        table.add_column("Timestamp")
        table.add_column("Fields")
        table.add_column("Status")
        for event_id, event_claims in by_event.items():
            fields = ", ".join(f"{c.field.value}={c.value}" for c in event_claims)
            timestamp = event_claims[0].timestamp
            status = event_claims[0].status
            table.add_row(event_id, timestamp.isoformat() if timestamp else "-", fields, _status_text(status))
        console.print(table)

    if item.conflicts:
        console.print("[bold]CONFLICTS[/bold]")
        for conflict in item.conflicts:
            console.print(f"  [yellow]![/yellow] {conflict.type.value}: {conflict.description}")

    table = Table(title="Resolved Fields", show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")
    table.add_column("Provenance")
    table.add_column("Source")
    table.add_column("Reason")
    for field in item.resolved_fields:
        table.add_row(
            field.field.value,
            str(field.value),
            field.provenance.value,
            field.winning_source.value if field.winning_source else "-",
            field.reason,
        )
    console.print(table)

    table = Table(title="Final Allocation", show_header=True, header_style="bold")
    table.add_column("Qty")
    table.add_column("Route")
    table.add_column("Bucket")
    table.add_column("Reason")
    for allocation in item.allocations:
        style = _ROUTE_STYLE.get(allocation.route, "white")
        table.add_row(
            str(allocation.quantity),
            f"[{style}]{allocation.route}[/{style}]",
            allocation.best_before_bucket or "-",
            allocation.reason,
        )
    console.print(table)

    console.print(
        f"[bold]COMMERCIAL[/bold]  credit_eligible={item.commercial_decision.credit_eligible}  "
        f"credit_quantity={item.commercial_decision.credit_quantity}"
    )
    console.print(f"  {item.commercial_decision.reason}")

    console.print("[bold]INTEGRITY[/bold]")
    for check in item.invariants:
        verdict = "[green]PASS[/green]" if check.passed else "[red]FAIL[/red]"
        console.print(f"  {check.detail}  {verdict}")

    console.print(f"[bold]RULES APPLIED[/bold]  {', '.join(item.rules_applied)}")
    console.print()


if __name__ == "__main__":
    app()
