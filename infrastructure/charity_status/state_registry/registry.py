from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from charity_status.state_registry.contracts import StateRegistryAdapter
from charity_status.state_registry.errors import StateRegistryAdapterRegistrationError, UnsupportedStateRegistryError
from charity_status.state_registry.normalization import normalize_state_code


@dataclass
class StateRegistryAdapterRegistry:
    _adapters: dict[str, StateRegistryAdapter] = field(default_factory=dict)

    def register(self, adapter: StateRegistryAdapter) -> None:
        state_code = normalize_state_code(adapter.state_code)
        if not state_code or len(state_code) != 2:
            raise StateRegistryAdapterRegistrationError("adapter.state_code must be a two-letter state code")
        if state_code in self._adapters:
            raise StateRegistryAdapterRegistrationError(f"adapter already registered for state {state_code}")
        self._adapters[state_code] = adapter

    def resolve(self, state_code: str) -> StateRegistryAdapter:
        normalized = normalize_state_code(state_code)
        adapter = self._adapters.get(normalized or "")
        if adapter is None:
            raise UnsupportedStateRegistryError(f"state registry adapter not configured for state {state_code}")
        return adapter

    def supported_states(self) -> list[str]:
        return sorted(self._adapters)


def build_state_registry_adapter_registry(
    adapters: Iterable[StateRegistryAdapter] | None = None,
) -> StateRegistryAdapterRegistry:
    registry = StateRegistryAdapterRegistry()
    for adapter in adapters or ():
        registry.register(adapter)
    return registry
