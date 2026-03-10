import json
import boto3
import os

athena = boto3.client("athena")

DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")

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

    response = athena.start_query_execution(**execution_args)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "queryExecutionId": response["QueryExecutionId"]
        })
    }
