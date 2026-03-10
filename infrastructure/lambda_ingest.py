import requests
import boto3
import os

S3_BUCKET = os.environ["BUCKET"]
IRS_URL = "https://www.irs.gov/pub/irs-soi/eo1.csv"

s3 = boto3.client("s3")

def handler(event, context):

    r = requests.get(IRS_URL)

    s3.put_object(
        Bucket=S3_BUCKET,
        Key="eo_bmf/eo1.csv",
        Body=r.content
    )

    return {"status": "downloaded"}