from __future__ import annotations

import io

from charity_status.ops.progress import ConsoleProgressSession, ProgressField, build_progress_reporter


class _FakeStream(io.StringIO):
    def __init__(self, *, is_tty: bool) -> None:
        super().__init__()
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def test_build_progress_reporter_returns_noop_for_non_tty_stream():
    stream = _FakeStream(is_tty=False)
    reporter = build_progress_reporter(stream=stream)
    session = reporter.start(
        total_items=20,
        fields=[ProgressField(key="parsed", label="parsed", color="green")],
    )

    for _ in range(12):
        session.item_completed({"parsed": 1})
    session.complete()

    assert stream.getvalue() == ""


def test_console_progress_session_renders_every_tenth_item_with_eta_and_final_flush(monkeypatch):
    stream = _FakeStream(is_tty=True)
    monotonic_values = iter([0.0, 120.0, 240.0])
    monkeypatch.setattr("charity_status.ops.progress.time.monotonic", lambda: next(monotonic_values))
    session = ConsoleProgressSession(
        stream=stream,
        total_items=20,
        fields=[
            ProgressField(key="parsed", label="parsed", color="green"),
            ProgressField(key="failed", label="failed", color="red"),
        ],
        update_every=10,
    )

    for _ in range(9):
        session.item_completed({"parsed": 1})
    assert stream.getvalue() == ""

    session.item_completed({"failed": 1})
    rendered = stream.getvalue()
    assert "\r" in rendered
    assert "parsed:" in rendered
    assert "failed:" in rendered
    assert "remaining:" in rendered
    assert "eta:" in rendered
    assert "02:00" in rendered
    assert "\033[32m9\033[0m" in rendered
    assert "\033[31m1\033[0m" in rendered
    assert "\033[34m10\033[0m" in rendered
    assert "\033[33m02:00\033[0m" in rendered
    assert "\n" not in rendered

    for _ in range(10):
        session.item_completed({"parsed": 1})
    session.complete()
    final_rendered = stream.getvalue()
    assert final_rendered.endswith("\n")
    assert "\033[34m0\033[0m" in final_rendered
    assert "\033[33m00:00\033[0m" in final_rendered
