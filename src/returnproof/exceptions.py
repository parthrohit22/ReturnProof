"""Error taxonomy. Expected uncertainty is a QUARANTINE decision, not an exception.

These are only raised for input that cannot be reconciled at all: malformed
JSON, a schema violation, or a genuine programming error. A conflict between
sources, a corrupted batch, or unresolved identity are handled outcomes, not
errors, and never reach these classes.
"""

from __future__ import annotations


class ReturnProofError(Exception):
    """Base class for all errors raised by the engine."""


class InputValidationError(ReturnProofError):
    """The input document is malformed or fails schema/domain validation."""


class InvariantViolationError(ReturnProofError):
    """A safety invariant (e.g. quantity conservation) failed after allocation.

    This should be unreachable in normal operation since allocation is built
    to satisfy the invariant by construction. If it fires, that is a
    programming error in allocation.py, not bad input.
    """
