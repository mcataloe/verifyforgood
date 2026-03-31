from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationEntityValidation:
    expected: int = 0
    present: int = 0
    missing: int = 0
    sample_missing_keys: tuple[str, ...] = ()


def build_entity_validation(
    *,
    expected_keys: set[str],
    present_keys: set[str],
    sample_limit: int = 20,
) -> MigrationEntityValidation:
    missing_keys = sorted(expected_keys - present_keys)
    return MigrationEntityValidation(
        expected=len(expected_keys),
        present=len(present_keys & expected_keys),
        missing=len(missing_keys),
        sample_missing_keys=tuple(missing_keys[:sample_limit]),
    )


__all__ = ["MigrationEntityValidation", "build_entity_validation"]
