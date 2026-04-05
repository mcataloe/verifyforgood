from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Mapping, Sequence, TextIO


@dataclass(frozen=True)
class ProgressField:
    key: str
    label: str
    color: str | None = None


class ProgressSession:
    def item_completed(self, increments: Mapping[str, int] | None = None) -> None:
        raise NotImplementedError

    def complete(self) -> None:
        raise NotImplementedError


class ProgressReporter:
    def start(
        self,
        *,
        total_items: int,
        fields: Sequence[ProgressField],
        update_every: int = 10,
    ) -> ProgressSession:
        raise NotImplementedError


@dataclass(frozen=True)
class _AnsiPalette:
    green: str = "\033[32m"
    red: str = "\033[31m"
    blue: str = "\033[34m"
    yellow: str = "\033[33m"
    reset: str = "\033[0m"


class NoOpProgressSession(ProgressSession):
    def item_completed(self, increments: Mapping[str, int] | None = None) -> None:
        return

    def complete(self) -> None:
        return


class NoOpProgressReporter(ProgressReporter):
    def start(
        self,
        *,
        total_items: int,
        fields: Sequence[ProgressField],
        update_every: int = 10,
    ) -> ProgressSession:
        return NoOpProgressSession()


class ConsoleProgressSession(ProgressSession):
    def __init__(
        self,
        *,
        stream: TextIO,
        total_items: int,
        fields: Sequence[ProgressField],
        update_every: int,
        palette: _AnsiPalette | None = None,
    ) -> None:
        self._stream = stream
        self._total_items = max(0, int(total_items))
        self._fields = list(fields)
        self._update_every = max(1, int(update_every))
        self._palette = palette or _AnsiPalette()
        self._counts = {field.key: 0 for field in self._fields}
        self._completed_items = 0
        self._started_at = time.monotonic()
        self._last_render_length = 0
        self._closed = False

    def item_completed(self, increments: Mapping[str, int] | None = None) -> None:
        if self._closed:
            return
        self._completed_items += 1
        for key, value in dict(increments or {}).items():
            self._counts[str(key)] = self._counts.get(str(key), 0) + int(value or 0)
        if self._completed_items % self._update_every == 0:
            self._render(final=False)

    def complete(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._render(final=True)
        self._stream.write("\n")
        self._stream.flush()

    @property
    def completed_items(self) -> int:
        return self._completed_items

    def _render(self, *, final: bool) -> None:
        line = self._line(final=final)
        padding = max(0, self._last_render_length - len(line))
        self._stream.write(f"\r{line}{' ' * padding}")
        self._stream.flush()
        self._last_render_length = len(line)

    def _line(self, *, final: bool) -> str:
        segments = [
            f"{field.label}: {self._format_value(field.color, self._counts.get(field.key, 0))}"
            for field in self._fields
        ]
        segments.append(f"remaining: {self._format_value('blue', self._remaining_items)}")
        eta = self._eta_text(final=final)
        if eta is not None:
            segments.append(f"eta: {self._format_value('yellow', eta)}")
        return " ".join(segments)

    @property
    def _remaining_items(self) -> int:
        return max(0, self._total_items - self._completed_items)

    def _eta_text(self, *, final: bool) -> str | None:
        if final:
            return "00:00"
        if self._completed_items < self._update_every:
            return None
        elapsed_seconds = max(0.0, time.monotonic() - self._started_at)
        average_seconds = elapsed_seconds / max(1, self._completed_items)
        eta_seconds = int(round(average_seconds * self._remaining_items))
        return _format_duration_mmss(eta_seconds)

    def _format_value(self, color_name: str | None, value: int | str) -> str:
        if not color_name:
            return str(value)
        color = getattr(self._palette, color_name, "")
        if not color:
            return str(value)
        return f"{color}{value}{self._palette.reset}"


class ConsoleProgressReporter(ProgressReporter):
    def __init__(self, *, stream: TextIO, palette: _AnsiPalette | None = None) -> None:
        self._stream = stream
        self._palette = palette or _AnsiPalette()

    def start(
        self,
        *,
        total_items: int,
        fields: Sequence[ProgressField],
        update_every: int = 10,
    ) -> ProgressSession:
        return ConsoleProgressSession(
            stream=self._stream,
            total_items=total_items,
            fields=fields,
            update_every=update_every,
            palette=self._palette,
        )


def build_progress_reporter(*, stream: TextIO | None = None) -> ProgressReporter:
    target = stream or sys.stdout
    if callable(getattr(target, "isatty", None)) and target.isatty():
        return ConsoleProgressReporter(stream=target)
    return NoOpProgressReporter()


def _format_duration_mmss(total_seconds: int) -> str:
    normalized = max(0, int(total_seconds))
    minutes, seconds = divmod(normalized, 60)
    return f"{minutes:02d}:{seconds:02d}"


__all__ = [
    "ConsoleProgressReporter",
    "ConsoleProgressSession",
    "NoOpProgressReporter",
    "NoOpProgressSession",
    "ProgressField",
    "ProgressReporter",
    "ProgressSession",
    "build_progress_reporter",
]
