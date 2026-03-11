from __future__ import annotations

from typing import Any

import boto3


class S3Uploader:
    def __init__(self, s3_client: Any | None = None) -> None:
        self._s3 = s3_client or boto3.client("s3")

    def upload_bytes(self, bucket: str, key: str, body: bytes) -> None:
        self._s3.put_object(Bucket=bucket, Key=key, Body=body)
