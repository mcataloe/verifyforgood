import pytest

from charity_status.platform import (
    DEFAULT_NAMESPACE,
    DEFAULT_PLATFORM,
    DEFAULT_REGION,
    build_resource_name,
    buildResourceName,
    validate_resource_name,
    validateResourceName,
)


def test_build_resource_name_uses_configured_defaults():
    assert build_resource_name(purpose="profiles", environment="dev") == "n8x4-verification-profiles-dev-use1"


def test_build_resource_name_supports_explicit_parts():
    assert build_resource_name(
        namespace="team1",
        platform="screening",
        purpose="source-data-bucket",
        environment="staging",
        region="usw2",
    ) == "team1-screening-source-data-bucket-staging-usw2"


def test_camel_case_builder_alias_matches_snake_case_builder():
    assert buildResourceName(purpose="query-api", environment="prod") == build_resource_name(
        purpose="query-api",
        environment="prod",
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"purpose": "QueryApi", "environment": "dev"}, "lowercase"),
        ({"purpose": "profiles", "environment": ""}, "provided"),
        ({"purpose": "profile_bucket", "environment": "dev"}, "lowercase"),
        ({"purpose": "-profiles", "environment": "dev"}, "leading"),
        ({"purpose": "profiles-", "environment": "dev"}, "trailing"),
        ({"purpose": "profiles", "environment": "dev!"}, "lowercase"),
    ],
)
def test_build_resource_name_rejects_invalid_parts(kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_resource_name(**kwargs)


def test_build_resource_name_rejects_values_that_break_s3_length_rules():
    with pytest.raises(ValueError, match="S3-compatible length constraints"):
        build_resource_name(
            namespace="n8x4",
            platform="verification",
            purpose="x" * 40,
            environment="development",
            region="use1",
        )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("n8x4-verification-profiles-dev-use1", True),
        ("abc1-screening-source-data-bucket-prod-use1", True),
        ("n8x4-verification-query-api-prod-use1", True),
        ("N8x4-verification-profiles-dev-use1", False),
        ("n8x4-verification-profiles-dev-use1-", False),
        ("-n8x4-verification-profiles-dev-use1", False),
        ("n8x4_verification_profiles_dev_use1", False),
        ("192.168.0.1", False),
        ("ab", False),
        ("a" * 64, False),
    ],
)
def test_validate_resource_name_covers_valid_and_invalid_cases(name, expected):
    assert validate_resource_name(name) is expected
    assert validateResourceName(name) is expected


def test_default_constants_are_stable():
    assert DEFAULT_NAMESPACE == "n8x4"
    assert DEFAULT_PLATFORM == "verification"
    assert DEFAULT_REGION == "use1"
