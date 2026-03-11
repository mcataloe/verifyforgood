from charity_status.serving.hash import calculate_source_hash
from charity_status.serving.keys import profile_pk, profile_sk


def test_dynamodb_key_generation():
    assert profile_pk("123456789") == "EIN#123456789"
    assert profile_sk() == "PROFILE#LATEST"


def test_source_hash_deterministic_ordering():
    a = {"model_version": "2.0.0", "verification": {"irs_status": "active", "tax_deductible": True}}
    b = {"verification": {"tax_deductible": True, "irs_status": "active"}, "model_version": "2.0.0"}

    assert calculate_source_hash(a) == calculate_source_hash(b)
