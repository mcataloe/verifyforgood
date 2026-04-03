"""Backend-owned monthly staging runtime entrypoint."""

from __future__ import annotations

import logging

from charity_status.form990.monthly_staging import stage_form990_monthly_source


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def handler(event, context):
    del context
    return stage_form990_monthly_source(event)


__all__ = ["handler"]

