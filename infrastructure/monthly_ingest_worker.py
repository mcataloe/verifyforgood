from __future__ import annotations

import json
import logging
import sys

from charity_status.form990.monthly_processing import run_form990_monthly_processing_task
from nonprofit_ingest_persistence import build_form990_nonprofit_persistence_service

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def main() -> int:
    result = run_form990_monthly_processing_task(
        nonprofit_persistence_service=build_form990_nonprofit_persistence_service(),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
