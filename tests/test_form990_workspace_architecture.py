from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"

if str(BACKEND_INGEST_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_INGEST_SRC))

from verification_backend.ingest_task.hashing import sha256_digest_file
from verification_backend.ingest_task.orchestration.workspace import (
    DEFAULT_FORM990_WORKSPACE_MAX_BYTES,
    build_workspace_layout,
    resolve_workspace_root,
)


def test_workspace_layout_uses_deterministic_subdirectories(tmp_path):
    layout = build_workspace_layout(root=tmp_path / "workspace").ensure()

    assert layout.archives_dir == layout.root / "archives"
    assert layout.extracted_dir == layout.root / "extracted"
    assert layout.logs_dir == layout.root / "logs"
    assert layout.state_dir == layout.root / "state"
    assert layout.max_bytes == DEFAULT_FORM990_WORKSPACE_MAX_BYTES

    archive = layout.for_archive("2025_TEOS_XML_11A").ensure()

    assert archive.archive_path == layout.archives_dir / "2025_TEOS_XML_11A.zip"
    assert archive.extracted_dir == layout.extracted_dir / "2025_TEOS_XML_11A"
    assert archive.log_path == layout.logs_dir / "2025_TEOS_XML_11A.log"
    assert archive.state_path == layout.state_dir / "2025_TEOS_XML_11A.json"
    assert archive.extracted_dir.exists()


def test_archive_workspace_cleanup_removes_extracted_xml_and_zip(tmp_path):
    layout = build_workspace_layout(root=tmp_path / "workspace").ensure()
    archive = layout.for_archive("2025_TEOS_XML_11B").ensure()
    archive.archive_path.write_bytes(b"zip")
    xml_file = archive.extracted_dir / "return.xml"
    xml_file.write_text("<Return/>", encoding="utf-8")

    archive.finalize_processed_archive()

    assert not archive.archive_path.exists()
    assert not archive.extracted_dir.exists()


def test_workspace_root_and_max_bytes_can_be_driven_by_env(tmp_path):
    env = {
        "FORM990_WORKSPACE_DIR": str(tmp_path / "custom-root"),
        "FORM990_WORKSPACE_MAX_BYTES": "12345",
    }

    root = resolve_workspace_root(env)
    layout = build_workspace_layout(env).ensure()

    assert root == (tmp_path / "custom-root").resolve()
    assert layout.root == root
    assert layout.max_bytes == 12345


def test_hashing_helper_returns_stable_sha256(tmp_path):
    payload = tmp_path / "archive.zip"
    payload.write_bytes(b"abc123")

    assert sha256_digest_file(payload) == sha256_digest_file(payload)

