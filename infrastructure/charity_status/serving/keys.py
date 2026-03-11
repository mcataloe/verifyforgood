from __future__ import annotations


def profile_pk(ein: str) -> str:
    return f"EIN#{ein}"


def profile_sk() -> str:
    return "PROFILE#LATEST"
