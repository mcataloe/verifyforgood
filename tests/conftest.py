import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_PATH = ROOT / "infrastructure"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(INFRA_PATH) not in sys.path:
    sys.path.insert(0, str(INFRA_PATH))

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))
