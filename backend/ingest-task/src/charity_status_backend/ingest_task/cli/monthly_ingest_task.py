"""Backend-owned CLI entrypoint for the monthly Form 990 ECS/local task."""

from __future__ import annotations

import json
import logging
import os
import sys

from charity_status.form990.monthly_processing import run_form990_monthly_processing_task
from charity_status.runtime_logging import configure_runtime_logging
from charity_status_backend.ingest_task.persistence.nonprofit_persistence import (
    build_form990_archive_metadata_service,
    build_form990_nonprofit_persistence_service,
)

LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)


def main() -> int:
    result = run_form990_monthly_processing_task(
        archive_metadata_service=build_form990_archive_metadata_service(),
        nonprofit_persistence_service=build_form990_nonprofit_persistence_service(),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
