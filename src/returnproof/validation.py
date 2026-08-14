"""Input validation and batch code classification.

Batch code format policy (documented here because it is a concrete, testable
rule, not a vague notion of "looks wrong"):

- The default grammar is two uppercase letters followed by four to six
  digits, e.g. ``BA1902``. This is a demo default for this exercise, not a
  real supplier's actual format, and it is not applied universally: a SKU's
  ``ProductMetadata.batch_pattern`` overrides it with a SKU-specific regex
  when one is supplied. A batch code is only judged against the default
  grammar when no contextual pattern is available for its SKU.
- A code is CORRUPTED if, once stripped and upper-cased, it contains any
  character that is not alphanumeric (``?``, ``$``, ``#``, etc). Scanner
  noise of that kind cannot be safely repaired by substitution, so no
  candidate is proposed. This alphanumeric assumption is itself part of
  the default grammar and is skipped when a contextual pattern is used,
  a custom grammar might legitimately allow punctuation.
- A code is SUSPECT if it is alphanumeric but does not match the default
  grammar, most commonly because a letter that looks like a digit under
  poor scanning conditions (``O``/``0``, ``I``/``1``, ``S``/``5``,
  ``B``/``8``, ``Z``/``2``, ``G``/``6``) landed in a digit position. In
  that case a normalised candidate is computed and recorded, but never
  trusted on its own, it must still be independently corroborated (see
  policies.py, R003) before it can win a decision. Substitution repair
  only runs under the default grammar, a code judged against a custom
  pattern is reported SUSPECT with no candidate, the digit positions of an
  arbitrary custom format aren't known. Repair can produce at most one
  candidate by construction: the fixed-shape pattern requires every
  character in the digit segment to be a digit, so every ambiguous letter
  in that segment must be substituted for the result to match at all,
  there is no partial-substitution reading that could also validly match.
- A code is MISSING if the raw value is null, empty, or whitespace only.

The original raw value is always preserved alongside any normalised value
or candidate. Nothing here mutates warehouse evidence silently.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, ValidationError

from returnproof.enums import BatchValidity
from returnproof.exceptions import InputValidationError
from returnproof.models import ReturnShipment

_BATCH_PATTERN = re.compile(r"^[A-Z]{2}\d{4,6}$")

_AMBIGUOUS_DIGIT_MAP = {
    "O": "0",
    "I": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
    "G": "6",
}


class BatchAssessment(BaseModel):
    """Result of classifying one raw batch code string."""

    model_config = ConfigDict(extra="forbid")

    raw_value: str | None
    normalized_value: str | None
    validity: BatchValidity
    normalized_candidate: str | None = None
    transformation: str | None = None


def _attempt_repair(normalized: str) -> str | None:
    """Try substituting OCR-ambiguous letters in the digit segment only.

    Only the two-letter prefix plus digit-segment shape is attempted. This
    never touches the prefix, a batch code with a corrupted prefix is left
    without a candidate rather than guessed at.
    """
    if len(normalized) < 3:
        return None
    prefix, rest = normalized[:2], normalized[2:]
    if not prefix.isalpha():
        return None
    candidate_rest = "".join(_AMBIGUOUS_DIGIT_MAP.get(char, char) for char in rest)
    candidate = prefix + candidate_rest
    if candidate != normalized and _BATCH_PATTERN.fullmatch(candidate):
        return candidate
    return None


def classify_batch(raw: str | None, pattern: str | None = None) -> BatchAssessment:
    """Classify a raw batch code without mutating or trusting it.

    `pattern`, when given, is a SKU-specific regex (from
    `ProductMetadata.batch_pattern`) that replaces the default grammar
    entirely, including its alphanumeric-only and repair-candidate
    assumptions, see the module docstring.
    """
    if raw is None or raw.strip() == "":
        return BatchAssessment(raw_value=raw, normalized_value=None, validity=BatchValidity.MISSING)

    stripped = raw.strip()

    if pattern is not None:
        if re.fullmatch(pattern, stripped):
            return BatchAssessment(raw_value=raw, normalized_value=stripped, validity=BatchValidity.VALID)
        return BatchAssessment(
            raw_value=raw,
            normalized_value=stripped,
            validity=BatchValidity.SUSPECT,
            transformation=(
                f"does not match this SKU's batch pattern {pattern!r}, "
                "no repair attempted for a custom pattern"
            ),
        )

    normalized = stripped.upper()

    if not normalized.isalnum():
        return BatchAssessment(
            raw_value=raw,
            normalized_value=normalized,
            validity=BatchValidity.CORRUPTED,
            transformation="contains non-alphanumeric characters, not recoverable by substitution",
        )

    if _BATCH_PATTERN.fullmatch(normalized):
        return BatchAssessment(raw_value=raw, normalized_value=normalized, validity=BatchValidity.VALID)

    candidate = _attempt_repair(normalized)
    transformation = (
        f"format does not match two letters + 4-6 digits. "
        f"candidate {candidate} via OCR-ambiguous digit substitution, unconfirmed"
        if candidate
        else "format does not match two letters + 4-6 digits, no plausible repair found"
    )
    return BatchAssessment(
        raw_value=raw,
        normalized_value=normalized,
        validity=BatchValidity.SUSPECT,
        normalized_candidate=candidate,
        transformation=transformation,
    )


def parse_shipment(raw: dict) -> ReturnShipment:
    """Parse and validate a raw dict into a ReturnShipment, or raise a clean error.

    Wraps pydantic's ValidationError so the CLI can show a short, readable
    message instead of a full traceback for expected bad input.
    """
    try:
        return ReturnShipment.model_validate(raw)
    except ValidationError as exc:
        raise InputValidationError(str(exc)) from exc
