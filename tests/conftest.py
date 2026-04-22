import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_CUSTOMER_API_SRC = ROOT / "backend" / "customer-api" / "src"
BACKEND_PLATFORM_API_SRC = ROOT / "backend" / "platform-api" / "src"
BACKEND_WORKER_SRC = ROOT / "backend" / "worker" / "src"
BACKEND_INGEST_FEDERAL_SRC = ROOT / "backend" / "ingest" / "federal" / "src"
BACKEND_INGEST_STATE_SRC = ROOT / "backend" / "ingest" / "state" / "src"
BACKEND_INGEST_SHARED_SRC = ROOT / "backend" / "ingest" / "shared" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

for path in (
    BACKEND_CUSTOMER_API_SRC,
    BACKEND_PLATFORM_API_SRC,
    BACKEND_WORKER_SRC,
    BACKEND_INGEST_FEDERAL_SRC,
    BACKEND_INGEST_STATE_SRC,
    BACKEND_INGEST_SHARED_SRC,
    BACKEND_SHARED_SRC,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
