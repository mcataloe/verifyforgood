import json
import boto3

athena = boto3.client("athena")

DATABASE = "irs_nonprofits"
TABLE = "eo_bmf"
OUTPUT = "s3://athena-query-results/"

def handler(event, context):

    ein = event["pathParameters"]["ein"]

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
        "body": json.dumps({"queryExecutionId": response["QueryExecutionId"]})
    }