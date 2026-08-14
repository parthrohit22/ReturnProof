"""Read-only access to the repository's `examples/*.json` fixtures.

Deliberately not a generic file server. `name` is only ever resolved
against an allowlist built by listing the real directory, never
concatenated into a path from user input, and the resolved path is
double-checked as a defense-in-depth measure against traversal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings


class ExampleNotFoundError(Exception):
    """Raised for any example name that isn't in the allowlist, including
    a name that looks like a path traversal attempt. The message is just
    the requested name, safe to surface to a caller.
    """


def _examples_dir() -> Path:
    return settings.EXAMPLES_DIR


def list_example_names() -> list[str]:
    directory = _examples_dir()
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.json") if path.is_file())


def load_example(name: str) -> dict[str, Any]:
    allowed = set(list_example_names())
    if name not in allowed:
        raise ExampleNotFoundError(name)

    directory = _examples_dir()
    path = (directory / f"{name}.json").resolve()
    if directory.resolve() not in path.parents:
        raise ExampleNotFoundError(name)

    return json.loads(path.read_text())
