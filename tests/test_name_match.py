from infrastructure.verification.backend.shared.normalization.name_match import compare_names


def test_compare_names_true_with_suffix_normalization():
    result = compare_names("Helping Hands", "Helping Hands Inc.")

    assert result["name_match"] is True
    assert result["match_confidence"] == "normalized"


def test_compare_names_false():
    result = compare_names("Helping Hands", "Different Charity")

    assert result["name_match"] is False
    assert result["match_confidence"] in {"weak", "none"}

