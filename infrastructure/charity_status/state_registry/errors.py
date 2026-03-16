from __future__ import annotations


class StateRegistryError(RuntimeError):
    pass


class UnsupportedStateRegistryError(StateRegistryError):
    pass


class StateRegistryAdapterRegistrationError(StateRegistryError):
    pass


class StateRegistryAdapterOperationNotSupportedError(StateRegistryError):
    pass


class StateRegistryLookupFailedError(StateRegistryError):
    pass
