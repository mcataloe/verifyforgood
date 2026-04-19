import pytest

from infrastructure.verification.normalization.ein import EINValidationError, format_ein, normalize_ein


def test_normalize_ein_valid_formats():
    assert normalize_ein("12-3456789") == "123456789"
    assert normalize_ein("123456789") == "123456789"
    assert normalize_ein(" 12 3456789 ") == "123456789"
    assert format_ein("123456789") == "12-3456789"


def test_normalize_ein_invalid_length():
    with pytest.raises(EINValidationError, match="exactly 9 digits"):
        normalize_ein("12345678")


def test_normalize_ein_invalid_characters():
    with pytest.raises(EINValidationError, match="invalid characters"):
        normalize_ein("12-34A6789")


def test_normalize_ein_empty_input():
    with pytest.raises(EINValidationError, match="required"):
        normalize_ein("   ")

