import json
from pathlib import Path

from typer.testing import CliRunner

from returnproof.cli import app

runner = CliRunner()
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_reconcile_human_output_on_compound_failure():
    result = runner.invoke(app, ["reconcile", str(EXAMPLES_DIR / "compound_failure.json")])
    assert result.exit_code == 0
    assert "SCRAP" in result.stdout
    assert "RESTOCK" in result.stdout
    assert "PASS" in result.stdout


def test_reconcile_json_output_is_valid_json():
    result = runner.invoke(app, ["reconcile", str(EXAMPLES_DIR / "compound_failure.json"), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["return_id"] == "RET-2026-001"
    assert payload["items"][0]["resolved"]["batch_code"] == "BA1902"


def test_reconcile_output_option_json():
    result = runner.invoke(
        app, ["reconcile", str(EXAMPLES_DIR / "compound_failure.json"), "--output", "json"]
    )
    assert result.exit_code == 0
    json.loads(result.stdout)


def test_reconcile_missing_file_fails_cleanly():
    result = runner.invoke(app, ["reconcile", str(EXAMPLES_DIR / "does_not_exist.json")])
    assert result.exit_code != 0


def test_reconcile_invalid_json_fails_cleanly(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    result = runner.invoke(app, ["reconcile", str(bad_file)])
    assert result.exit_code == 2
    assert "Invalid JSON" in result.output


def test_reconcile_schema_violation_fails_cleanly(tmp_path):
    bad_file = tmp_path / "bad_schema.json"
    bad_file.write_text(json.dumps({"return_id": "RET-X"}))  # missing warehouse_report
    result = runner.invoke(app, ["reconcile", str(bad_file)])
    assert result.exit_code == 2
    assert "Invalid input" in result.output


def test_all_bundled_examples_run_without_error():
    for example in EXAMPLES_DIR.glob("*.json"):
        result = runner.invoke(app, ["reconcile", str(example), "--json"])
        assert result.exit_code == 0, f"{example.name} failed: {result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["summary"]["invariants_passed"] is True


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "returnproof" in result.stdout


def test_reconcile_malformed_batch_pattern_fails_cleanly(tmp_path):
    """HIGH-1 regression: a malformed custom batch_pattern must exit through
    the same clean validation-error path as any other bad input, never as an
    uncontrolled re.error traceback.
    """
    bad_file = tmp_path / "bad_pattern.json"
    bad_file.write_text(
        json.dumps(
            {
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
        )
    )
    result = runner.invoke(app, ["reconcile", str(bad_file)])
    assert result.exit_code == 2
    assert "Invalid input" in result.output
    assert "batch_pattern" in result.output
    assert "Traceback" not in result.output
    assert "re.error" not in result.output
