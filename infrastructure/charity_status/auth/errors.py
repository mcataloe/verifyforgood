from __future__ import annotations


class AuthenticationError(ValueError):
    status_code = 401


class AuthorizationError(ValueError):
    status_code = 403


class QuotaExceededError(ValueError):
    status_code = 429
