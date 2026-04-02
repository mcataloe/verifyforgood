"""Lambda-compatible entrypoint for the backend-owned monthly staging runtime."""

from charity_status.form990.monthly_staging import stage_form990_monthly_source


def handler(event, context):
    del context
    return stage_form990_monthly_source(event)


__all__ = ["handler"]
