from __future__ import annotations

from decimal import Decimal

from verification.backend.shared.serving.dynamodb_store import DynamoProfileStore


class _FakeTable:
    def __init__(self) -> None:
        self.last_item = None

    def put_item(self, Item):  # noqa: N803
        self.last_item = Item

    def get_item(self, Key):  # noqa: N803
        return {"Item": None}


class _FakeResource:
    def __init__(self, table: _FakeTable) -> None:
        self._table = table

    def Table(self, name: str):  # noqa: N802
        return self._table


def test_put_profile_converts_nested_floats_to_decimal():
    table = _FakeTable()
    store = DynamoProfileStore("profiles", dynamodb_resource=_FakeResource(table))

    store.put_profile(
        {
            "pk": "EIN#123456789",
            "sk": "PROFILE#LATEST",
            "scores": {"overall": 88.5, "dimensions": [0.25, 0.5]},
            "audit": {"thresholds": {"min": 1.0}},
        }
    )

    assert table.last_item["scores"]["overall"] == Decimal("88.5")
    assert table.last_item["scores"]["dimensions"] == [Decimal("0.25"), Decimal("0.5")]
    assert table.last_item["audit"]["thresholds"]["min"] == Decimal("1.0")

