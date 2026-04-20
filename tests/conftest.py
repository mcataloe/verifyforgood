import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_PATH = ROOT / "infrastructure"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"
BACKEND_API_SRC = ROOT / "backend" / "api" / "src"
BACKEND_WORKER_SRC = ROOT / "backend" / "worker" / "src"
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

if str(INFRA_PATH) not in sys.path:
    sys.path.insert(0, str(INFRA_PATH))

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))

for path in (BACKEND_API_SRC, BACKEND_WORKER_SRC, BACKEND_INGEST_SRC, BACKEND_SHARED_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
