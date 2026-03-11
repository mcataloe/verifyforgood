import importlib
import json
import sys
from types import SimpleNamespace


def _load_module():
    sys.modules.pop("infrastructure.lambda_query", None)
    return importlib.import_module("infrastructure.lambda_query")


def test_handler_invalid_ein_returns_400(monkeypatch):
    module = _load_module()

    event = {"pathParameters": {"ein": "12-34A6789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "invalid characters" in body["message"]


def test_handler_not_found_returns_404(monkeypatch):
    module = _load_module()

    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-1", None))

    event = {"pathParameters": {"ein": "12-3456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["ein"] == "123456789"


def test_handler_success_shape(monkeypatch):
    module = _load_module()

    record = {
        "name": "Test Org",
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
    module.athena_client = SimpleNamespace(lookup_nonprofit=lambda ein, subsection=None: ("qid-2", record))

    event = {"pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert set(["organization", "verification", "scores", "model"]).issubset(body.keys())
    assert body["organization"]["ein"] == "12-3456789"
    assert body["verification"]["country"] == "US"
    assert "score_explanation" in body
