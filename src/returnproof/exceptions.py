"""Error taxonomy. Expected uncertainty is a QUARANTINE decision, not an exception.

These are only raised for input that cannot be reconciled at all: malformed
JSON, a schema violation, or a genuine programming error. A conflict between
sources, a corrupted batch, or unresolved identity are handled outcomes, not
errors, and never reach these classes.
"""

from __future__ import annotations

from typing import Any


class ReturnProofError(Exception):
    """Base class for all errors raised by the engine."""


class InputValidationError(ReturnProofError):
    """The input document is malformed or fails schema/domain validation.

    `errors` carries pydantic's structured per-field error list (its
    `.errors()` output) when available, alongside the flattened string
    message every caller already gets from `str(exc)`. The CLI only needs
    the string. A caller building a structured HTTP response (see
    server/reconciliation/api.py) needs the per-field detail too, and
    shouldn't have to re-parse the string to get it.
    """

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class InvariantViolationError(ReturnProofError):
    """A safety invariant (e.g. quantity conservation) failed after allocation.

    This should be unreachable in normal operation since allocation is built
    to satisfy the invariant by construction. If it fires, that is a
    programming error in allocation.py, not bad input.
    """
