import json
import boto3
import os

athena = boto3.client("athena")

DATABASE = os.environ["DATABASE"]
TABLE = os.environ["TABLE"]
OUTPUT = os.environ["OUTPUT"]

def handler(event, context):
    path_params = event.get("pathParameters") or {}
    ein = path_params.get("ein")

    if not ein:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing path parameter: ein"})
        }

    query = f"""
        SELECT *
        FROM {TABLE}
        WHERE ein = '{ein}'
          AND subsection = '03'
        LIMIT 1
    """

    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": OUTPUT}
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "queryExecutionId": response["QueryExecutionId"]
        })
    }
