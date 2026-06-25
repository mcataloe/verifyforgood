"""Deterministic streaming XML content hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path


ASCII_TRIMMABLE_WHITESPACE = b" \t\r\n\f\v"


def sha256_xml_content_hash(path: str | Path, *, chunk_size: int = 64 * 1024) -> str:
    digest = hashlib.sha256()
    pending = b""
    first_chunk = True
    target_path = Path(path)
    with target_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            if first_chunk:
                first_chunk = False
                chunk = _strip_utf8_bom(chunk)
            pending += chunk
            pending = pending.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if not pending:
                continue
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                digest.update(line.rstrip(ASCII_TRIMMABLE_WHITESPACE))
                digest.update(b"\n")
    if pending:
        digest.update(pending.rstrip(ASCII_TRIMMABLE_WHITESPACE))
    return digest.hexdigest()


def _strip_utf8_bom(chunk: bytes) -> bytes:
    if chunk.startswith(b"\xef\xbb\xbf"):
        return chunk[3:]
    return chunk


__all__ = ["sha256_xml_content_hash"]
