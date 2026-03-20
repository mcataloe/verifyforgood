from __future__ import annotations

from charity_status.query.athena_service import AthenaQueryClient


class _FakeAthenaClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def start_query_execution(self, **kwargs):
        self.queries.append(kwargs["QueryString"])
        return {"QueryExecutionId": "qid-123"}

    def get_query_execution(self, QueryExecutionId):  # noqa: N803
        return {
            "QueryExecution": {
                "Status": {
                    "State": "SUCCEEDED",
                }
            }
        }

    def get_query_results(self, QueryExecutionId):  # noqa: N803
        return {
            "ResultSet": {
                "Rows": [
                    {"Data": [{"VarCharValue": "ein"}, {"VarCharValue": "name"}, {"VarCharValue": "status"}]},
                    {"Data": [{"VarCharValue": "123456789"}, {"VarCharValue": "Helping Hands"}, {"VarCharValue": "1"}]},
                ]
            }
        }


def test_athena_query_client_supports_injected_client_without_boto3_setup():
    fake = _FakeAthenaClient()
    client = AthenaQueryClient(
        database="db",
        table="eo_table",
        athena_client=fake,
        workgroup="wg",
    )

    execution_id, record = client.lookup_nonprofit("123456789")

    assert execution_id == "qid-123"
    assert record == {
        "ein": "123456789",
        "name": "Helping Hands",
        "status": "1",
    }
    assert "SELECT * FROM eo_table WHERE ein = '123456789' LIMIT 1" in fake.queries[0]
