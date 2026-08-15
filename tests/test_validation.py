import pytest
from pydantic import ValidationError

from returnproof.enums import BatchValidity
from returnproof.models import ProductMetadata
from returnproof.validation import classify_batch
from tests.conftest import make_item


def test_valid_batch_accepted():
    result = classify_batch("BA1902")
    assert result.validity == BatchValidity.VALID
    assert result.normalized_value == "BA1902"


def test_missing_batch_detected_for_none():
    result = classify_batch(None)
    assert result.validity == BatchValidity.MISSING


def test_missing_batch_detected_for_empty_string():
    result = classify_batch("   ")
    assert result.validity == BatchValidity.MISSING


def test_corrupted_batch_with_symbol_noise():
    result = classify_batch("BA?9O2")
    assert result.validity == BatchValidity.CORRUPTED
    assert result.normalized_candidate is None


def test_corrupted_batch_multiple_symbols():
    result = classify_batch("B72$9#")
    assert result.validity == BatchValidity.CORRUPTED


def test_suspect_batch_proposes_unconfirmed_candidate():
    result = classify_batch("BA729I")
    assert result.validity == BatchValidity.SUSPECT
    assert result.normalized_candidate == "BA7291"
    # the raw value is preserved untouched
    assert result.raw_value == "BA729I"


def test_suspect_batch_without_plausible_repair():
    result = classify_batch("BA19")
    assert result.validity == BatchValidity.SUSPECT
    assert result.normalized_candidate is None


def test_original_value_never_mutated_on_normalization():
    result = classify_batch("  ba1902  ")
    assert result.raw_value == "  ba1902  "
    assert result.normalized_value == "BA1902"


def test_malformed_best_before_rejected():
    with pytest.raises(ValidationError):
        make_item(best_before="not-a-date")


def test_negative_quantity_received_rejected():
    with pytest.raises(ValidationError):
        make_item(quantity_received=-1)


def test_negative_damaged_quantity_rejected():
    with pytest.raises(ValidationError):
        make_item(damaged_quantity=-1)


def test_damaged_quantity_exceeding_received_rejected():
    with pytest.raises(ValidationError):
        make_item(quantity_received=5, damaged_quantity=6)


def test_damaged_quantity_equal_to_received_is_valid():
    item = make_item(quantity_received=5, damaged_quantity=5)
    assert item.damaged_quantity == 5


# --- HIGH-1: malformed batch_pattern is rejected as bad input, not a crash --


def test_malformed_batch_pattern_rejected_at_model_boundary():
    """A syntactically invalid regex is bad input, this must fail here, at
    parse time, not reach classify_batch() and raise re.error mid-reconciliation.
    """
    with pytest.raises(ValidationError, match="batch_pattern"):
        ProductMetadata(sku="SKU-1", batch_pattern="(unclosed[")


def test_valid_batch_pattern_is_accepted_at_model_boundary():
    metadata = ProductMetadata(sku="SKU-1", batch_pattern=r"\d{4}-[A-Z]-\d{3}")
    assert metadata.batch_pattern == r"\d{4}-[A-Z]-\d{3}"


def test_classify_batch_defensive_guard_against_a_bad_pattern_called_directly():
    """classify_batch() is a public function a caller could reach with a
    pattern that never passed through ProductMetadata's own validator. It
    must not crash, and it must not silently treat the unjudgeable code as
    a match: an unusable pattern reports CORRUPTED, not VALID.
    """
    result = classify_batch("AB1234", pattern="(unclosed[")
    assert result.validity == BatchValidity.CORRUPTED
    assert "not a valid regular expression" in result.transformation
