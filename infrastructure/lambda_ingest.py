from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import boto3

from charity_status.ingest.downloader import download_file
from charity_status.ingest.irs_files import IRS_FILES, ingest_bucket, s3_key_for
from charity_status.ingest.result import build_ingest_result
from charity_status.ingest.uploader import S3Uploader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


async def _download_file(_session, filename: str) -> bytes:
    return await download_file(filename)


async def _process_file(filename: str, uploader: S3Uploader, bucket: str) -> dict[str, str]:
    s3_key = s3_key_for(filename)
    try:
        content = await _download_file(None, filename)
        uploader.upload_bytes(bucket=bucket, key=s3_key, body=content)
        logger.info("ingest_file", extra={"file": filename, "status": "downloaded", "s3_key": s3_key})
        return {"name": filename, "status": "downloaded", "s3_key": s3_key}
    except Exception as exc:
        logger.exception("ingest_file_failed", extra={"file": filename, "status": "failed", "s3_key": s3_key})
        return {"name": filename, "status": "failed", "error": str(exc)}


async def _ingest_files() -> list[dict[str, str]]:
    uploader = S3Uploader(s3_client=s3)
    bucket = ingest_bucket()
    tasks = [_process_file(filename, uploader=uploader, bucket=bucket) for filename in IRS_FILES]
    return await asyncio.gather(*tasks)


def handler(event, context):
    started_at = datetime.now(timezone.utc)
    logger.info("ingest_started", extra={"started_at": started_at.isoformat(), "files": IRS_FILES})

    files = asyncio.run(_ingest_files())
    result = build_ingest_result(started_at=started_at, files=files)

    logger.info(
        "ingest_completed",
        extra={
            "status": result["status"],
            "downloaded_count": result["downloaded_count"],
            "failed_count": result["failed_count"],
            "duration_ms": result["duration_ms"],
        },
    )
    return result
