from __future__ import annotations

import json
import logging
import sys

from charity_status.form990.monthly_processing import run_form990_monthly_processing_task

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def main() -> int:
    result = run_form990_monthly_processing_task()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
