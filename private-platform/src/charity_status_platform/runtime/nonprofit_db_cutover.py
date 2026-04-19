from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.engine import Engine

from charity_status.platform import (
    has_dedicated_nonprofit_postgres_config,
    resolve_nonprofit_postgres_sqlalchemy_url,
    resolve_postgres_sqlalchemy_url,
)
from charity_status_platform.nonprofits import NONPROFIT_TABLES, create_nonprofit_tables, drop_nonprofit_tables


@dataclass(frozen=True)
class NonprofitDatabaseCutoverReport:
    source_tables_scanned: int
    target_tables_loaded: int
    rows_copied_by_table: dict[str, int]
    reset_target: bool


def cutover_nonprofit_database(
    env: Mapping[str, str] | None = None,
    *,
    source_sqlalchemy_url: str | None = None,
    target_sqlalchemy_url: str | None = None,
    reset_target: bool = True,
    batch_size: int = 1_000,
    secrets_client: Any | None = None,
) -> NonprofitDatabaseCutoverReport:
    source_env = env or os.environ
    if not has_dedicated_nonprofit_postgres_config(source_env):
        raise ValueError(
            "Dedicated nonprofit PostgreSQL config is required for nonprofit database cutover"
        )
    source_url = source_sqlalchemy_url or resolve_postgres_sqlalchemy_url(
        source_env,
        secrets_client=secrets_client,
    )
    target_url = target_sqlalchemy_url or resolve_nonprofit_postgres_sqlalchemy_url(
        source_env,
        secrets_client=secrets_client,
    )
    if source_url == target_url:
        raise ValueError(
            "Source and target PostgreSQL URLs are identical; refusing destructive nonprofit cutover"
        )

    source_engine = create_engine(source_url, future=True)
    target_engine = create_engine(target_url, future=True)

    create_nonprofit_tables(target_engine)
    if reset_target:
        drop_nonprofit_tables(target_engine, include_version_table=True)
        create_nonprofit_tables(target_engine)

    rows_copied_by_table: dict[str, int] = {}
    ordered_tables = list(NONPROFIT_TABLES)
    reflected_metadata = MetaData()
    reflected_tables = {
        table.name: reflected_metadata.reflect(bind=source_engine, only=[table.name]) or reflected_metadata.tables[table.name]
        for table in ordered_tables
    }
    with source_engine.begin() as source_connection, target_engine.begin() as target_connection:
        for table in ordered_tables:
            source_table = reflected_tables[table.name]
            rows_copied_by_table[table.name] = _copy_table_rows(
                source_connection=source_connection,
                target_connection=target_connection,
                source_table=source_table,
                target_table=table,
                batch_size=max(1, int(batch_size)),
            )
        _sync_identity_sequences(target_connection, target_engine, ordered_tables)

    return NonprofitDatabaseCutoverReport(
        source_tables_scanned=len(ordered_tables),
        target_tables_loaded=len(ordered_tables),
        rows_copied_by_table=rows_copied_by_table,
        reset_target=reset_target,
    )


def _sync_identity_sequences(connection, engine: Engine, tables: list[Any]) -> None:
    if engine.dialect.name != "postgresql":
        return
    for table in tables:
        primary_key_columns = list(table.primary_key.columns)
        if len(primary_key_columns) != 1:
            continue
        pk_column = primary_key_columns[0]
        if not getattr(pk_column.type, "python_type", None):
            continue
        if pk_column.type.python_type is not int:
            continue
        sequence_name = connection.execute(
            text(
                "SELECT pg_get_serial_sequence(:table_name, :column_name)"
            ),
            {
                "table_name": table.name,
                "column_name": pk_column.name,
            },
        ).scalar_one_or_none()
        if not sequence_name:
            continue
        max_value = connection.execute(
            text(f"SELECT COALESCE(MAX({pk_column.name}), 0) FROM {table.name}")
        ).scalar_one()
        connection.execute(
            text("SELECT setval(:sequence_name, :max_value, :is_called)"),
            {
                "sequence_name": sequence_name,
                "max_value": int(max_value or 0),
                "is_called": bool(max_value),
            },
        )


def _copy_table_rows(
    *,
    source_connection,
    target_connection,
    source_table,
    target_table,
    batch_size: int,
) -> int:
    copied = 0
    result = source_connection.execution_options(stream_results=True).execute(select(source_table)).mappings()
    try:
        while True:
            batch = result.fetchmany(batch_size)
            if not batch:
                break
            payload = [dict(row.items()) for row in batch]
            target_connection.execute(target_table.insert(), payload)
            copied += len(payload)
            print(
                f"[nonprofit-cutover] copied {copied} rows into {target_table.name}",
                file=sys.stderr,
                flush=True,
            )
    finally:
        result.close()
    return copied


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Destructively cut over nonprofit tables from the platform database into the dedicated nonprofit database."
    )
    parser.add_argument(
        "--source-sqlalchemy-url",
        default=os.environ.get("PLATFORM_POSTGRES_URL", ""),
    )
    parser.add_argument(
        "--target-sqlalchemy-url",
        default=os.environ.get("PLATFORM_NONPROFIT_POSTGRES_URL", ""),
    )
    parser.add_argument(
        "--skip-reset",
        action="store_true",
        help="Do not clear the target nonprofit database before copying rows.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1_000,
        help="Row batch size used while streaming nonprofit tables from source to target.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = cutover_nonprofit_database(
        os.environ,
        source_sqlalchemy_url=(str(args.source_sqlalchemy_url).strip() or None),
        target_sqlalchemy_url=(str(args.target_sqlalchemy_url).strip() or None),
        reset_target=not bool(args.skip_reset),
        batch_size=max(1, int(args.batch_size)),
    )
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
