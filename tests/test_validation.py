import pytest
from pydantic import ValidationError

from returnproof.enums import BatchValidity
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
