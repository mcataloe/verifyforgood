"""Backend-owned monthly staging runtime entrypoint."""

from __future__ import annotations

import logging
import os

from charity_status.form990.monthly_staging import stage_form990_monthly_source
from charity_status.runtime_logging import configure_runtime_logging


LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)


def handler(event, context):
    del context
    return stage_form990_monthly_source(event)


__all__ = ["handler"]

