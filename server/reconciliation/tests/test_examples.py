from __future__ import annotations

import pytest

from .. import examples


def test_list_example_names_matches_real_directory():
    names = examples.list_example_names()
    assert "compound_failure" in names
    assert "compound_unresolved" in names
    assert names == sorted(names)


def test_load_example_returns_parsed_json():
    payload = examples.load_example("compound_failure")
    assert payload["return_id"] == "RET-2026-001"


@pytest.mark.parametrize(
    "name",
    [
        "does_not_exist",
        "../pyproject",
        "../../etc/passwd",
        "..",
        "compound_failure/../../pyproject",
    ],
)
def test_load_example_rejects_anything_not_allowlisted(name):
    with pytest.raises(examples.ExampleNotFoundError):
        examples.load_example(name)
