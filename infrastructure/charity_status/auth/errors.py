from __future__ import annotations


class AuthenticationError(ValueError):
    status_code = 401


class AuthorizationError(ValueError):
    status_code = 403


class FeatureUnavailableError(AuthorizationError):
    def __init__(self, message: str, *, feature_flag: str | None = None, capability: str | None = None, upgrade_plan: str | None = None):
        super().__init__(message)
        self.feature_flag = feature_flag
        self.capability = capability
        self.upgrade_plan = upgrade_plan


class QuotaExceededError(ValueError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.code = str(code or self.code)
