from __future__ import annotations

import asyncio
import urllib.request

from charity_status.ingest.irs_files import source_url_for


def _download_file_sync(filename: str, timeout_seconds: int = 60) -> bytes:
    request = urllib.request.Request(source_url_for(filename), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"download failed with status {response.status}")
        return response.read()


async def download_file(filename: str) -> bytes:
    return await asyncio.to_thread(_download_file_sync, filename)
