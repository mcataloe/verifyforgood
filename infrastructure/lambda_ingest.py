import asyncio
import boto3
import os
import urllib.request

S3_BUCKET = os.environ["BUCKET"]
IRS_BASE_URL = "https://www.irs.gov/pub/irs-soi"
IRS_FILES = [
    "eo1.csv",
    "eo2.csv",
    "eo3.csv",
    "eo4.csv",
    "eo_pr.csv",
    "eo_xx.csv",
]

s3 = boto3.client("s3")


def _download_file_sync(filename):
    url = f"{IRS_BASE_URL}/{filename}"
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status >= 400:
            raise RuntimeError(f"download failed with status {response.status}")
        return response.read()


async def _download_file(_session, filename):
    return await asyncio.to_thread(_download_file_sync, filename)


async def _process_file(filename):
    try:
        content = await _download_file(None, filename)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"eo_bmf/{filename}",
            Body=content
        )
        return {"filename": filename, "success": True}
    except Exception as exc:
        return {"filename": filename, "success": False, "error": str(exc)}


async def _ingest_files():
    tasks = [_process_file(filename) for filename in IRS_FILES]
    return await asyncio.gather(*tasks)


def handler(event, context):
    results = asyncio.run(_ingest_files())
    downloaded = [result["filename"] for result in results if result["success"]]
    failed = [
        {"filename": result["filename"], "error": result["error"]}
        for result in results
        if not result["success"]
    ]

    if downloaded and failed:
        status = "partial_success"
    elif downloaded:
        status = "success"
    else:
        status = "failed"

    return {
        "status": status,
        "downloaded": downloaded,
        "failed": failed,
    }
