import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_PATH = ROOT / "infrastructure"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(INFRA_PATH) not in sys.path:
    sys.path.insert(0, str(INFRA_PATH))
