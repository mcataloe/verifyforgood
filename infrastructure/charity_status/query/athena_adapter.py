from __future__ import annotations

from typing import Any

import boto3

from charity_status.query.athena_service import AthenaQueryClient


def build_boto3_athena_client() -> Any:
    return boto3.client("athena")


def create_athena_query_client(
    *,
    database: str,
    table: str,
    workgroup: str | None = None,
    poll_interval_seconds: int = 1,
    max_wait_seconds: int = 25,
    form990_filings_table: str | None = None,
    form990_metrics_table: str | None = None,
    form990_governance_table: str | None = None,
    form990_quality_table: str | None = None,
    athena_client: Any | None = None,
) -> AthenaQueryClient:
    return AthenaQueryClient(
        database=database,
        table=table,
        athena_client=athena_client or build_boto3_athena_client(),
        workgroup=workgroup,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        form990_filings_table=form990_filings_table,
        form990_metrics_table=form990_metrics_table,
        form990_governance_table=form990_governance_table,
        form990_quality_table=form990_quality_table,
    )
