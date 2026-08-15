import json

import pytest
from django.conf import settings


def _load_example(name: str) -> dict:
    path = settings.EXAMPLES_DIR / f"{name}.json"
    return json.loads(path.read_text())


@pytest.fixture
def compound_failure_payload() -> dict:
    return _load_example("compound_failure")


@pytest.fixture
def compound_unresolved_payload() -> dict:
    return _load_example("compound_unresolved")


@pytest.fixture
def batch_corruption_payload() -> dict:
    return _load_example("batch_corruption")


@pytest.fixture
def multi_item_return_payload() -> dict:
    return _load_example("multi_item_return")
