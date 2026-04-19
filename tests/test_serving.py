from verification.serving.hash import calculate_source_hash
from verification.serving.keys import profile_pk, profile_sk
from infrastructure.verification.scoring import SCORING_MODEL_VERSION


def test_dynamodb_key_generation():
    assert profile_pk("123456789") == "EIN#123456789"
    assert profile_sk() == "PROFILE#LATEST"


def test_source_hash_deterministic_ordering():
    a = {"model_version": SCORING_MODEL_VERSION, "verification": {"irs_status": "active", "tax_deductible": True}}
    b = {"verification": {"tax_deductible": True, "irs_status": "active"}, "model_version": SCORING_MODEL_VERSION}

    assert calculate_source_hash(a) == calculate_source_hash(b)

