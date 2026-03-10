import json
import boto3
import os
import time

athena = boto3.client("athena")

DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")
POLL_INTERVAL_SECONDS = 1
MAX_WAIT_SECONDS = 25


def _wait_for_query(query_execution_id):
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        execution = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = execution["QueryExecution"]["Status"]["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return execution
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError("Athena query timed out before completion")


def _rows_to_json(result_set):
    rows = result_set.get("Rows", [])
    if not rows:
        return []

    headers = [
        col.get("VarCharValue", "")
        for col in rows[0].get("Data", [])
    ]

    records = []
    for row in rows[1:]:
        values = [col.get("VarCharValue") for col in row.get("Data", [])]
        # Align sparse row values with header length.
        if len(values) < len(headers):
            values.extend([None] * (len(headers) - len(values)))
        records.append(dict(zip(headers, values)))
    return records

def handler(event, context):
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    ein = path_params.get("ein")
    subsection = query_params.get("subsection")

    if not ein:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing path parameter: ein"})
        }

    where_clause = f"ein = '{ein}'"
    if subsection:
        where_clause += f" AND subsection = '{subsection}'"

    query = f"SELECT * FROM {TABLE} WHERE {where_clause} LIMIT 1"

    execution_args = {
        "QueryString": query,
        "QueryExecutionContext": {"Database": DATABASE},
    }
    if WORKGROUP:
        execution_args["WorkGroup"] = WORKGROUP

    start_response = athena.start_query_execution(**execution_args)
    query_execution_id = start_response["QueryExecutionId"]

    try:
        execution = _wait_for_query(query_execution_id)
    except TimeoutError as exc:
        return {
            "statusCode": 504,
            "body": json.dumps({
                "message": str(exc),
                "queryExecutionId": query_execution_id
            })
        }

    state = execution["QueryExecution"]["Status"]["State"]
    if state != "SUCCEEDED":
        reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "Unknown Athena failure")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Athena query did not succeed",
                "state": state,
                "reason": reason,
                "queryExecutionId": query_execution_id
            })
        }

    results = athena.get_query_results(QueryExecutionId=query_execution_id)
    records = _rows_to_json(results.get("ResultSet", {}))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "queryExecutionId": query_execution_id,
            "count": len(records),
            "records": records
        })
    }
