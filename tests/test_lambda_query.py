import importlib
import json
import sys
from types import SimpleNamespace


def _load_module():
    sys.modules.pop("infrastructure.lambda_query", None)
    return importlib.import_module("infrastructure.lambda_query")


def _sample_record(name="Test Org"):
    return {
        "name": name,
        "state": "IL",
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }


def test_get_handler_invalid_ein_returns_400():
    module = _load_module()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-34A6789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "invalid characters" in body["message"]


def test_get_handler_not_found_returns_404():
    module = _load_module()
    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-1", None))

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-3456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["ein"] == "123456789"


def test_post_verify_success_and_name_match_true():
    module = _load_module()
    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-2", _sample_record("Helping Hands Inc.")))

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "12-3456789", "name": "Helping Hands"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["name_verification"]["name_match"] is True
    assert body["name_verification"]["match_confidence"] in {"exact", "normalized"}
    assert body["score_explanation"]["factors"]["name_match"] is True


def test_post_verify_name_match_false():
    module = _load_module()
    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-3", _sample_record("Helping Hands Foundation")))

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "12-3456789", "name": "Different Org Name"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["name_verification"]["name_match"] is False
    assert body["name_verification"]["match_confidence"] in {"weak", "none"}
    assert body["score_explanation"]["factors"]["name_match"] is False


def test_post_verify_invalid_request_body():
    module = _load_module()

    event = {
        "httpMethod": "POST",
        "body": "{bad json",
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "valid JSON" in body["message"]


def test_get_and_post_response_shape_consistency():
    module = _load_module()
    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-4", _sample_record("Test Org")))

    get_event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    post_event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Test Org"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }

    get_body = json.loads(module.handler(get_event, None)["body"])
    post_body = json.loads(module.handler(post_event, None)["body"])

    expected_keys = {"organization", "verification", "scores", "model", "score_explanation", "name_verification"}
    assert expected_keys.issubset(get_body.keys())
    assert expected_keys.issubset(post_body.keys())

    assert set(get_body["scores"].keys()) == set(post_body["scores"].keys())
    assert set(get_body["score_explanation"].keys()) == set(post_body["score_explanation"].keys())
