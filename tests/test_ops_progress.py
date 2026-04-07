from __future__ import annotations

import io
import threading

from charity_status.ops.progress import ConsoleProgressSession, ProgressField, build_progress_reporter, prepare_stream_for_external_write


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


def test_console_progress_session_renders_last_item_and_truncates_it(monkeypatch):
    stream = _FakeStream(is_tty=True)
    monotonic_values = iter([0.0, 60.0, 120.0])
    monkeypatch.setattr("charity_status.ops.progress.time.monotonic", lambda: next(monotonic_values))
    session = ConsoleProgressSession(
        stream=stream,
        total_items=10,
        fields=[ProgressField(key="parsed", label="parsed", color="green")],
        update_every=1,
    )

    session.item_completed({"parsed": 1}, last_item="very-long-xml-member-name-" * 3 + ".xml")
    session.complete()

    rendered = stream.getvalue()
    assert "last:" in rendered
    assert "..." in rendered


def test_console_progress_session_item_completed_is_thread_safe():
    stream = _FakeStream(is_tty=True)
    session = ConsoleProgressSession(
        stream=stream,
        total_items=40,
        fields=[ProgressField(key="parsed", label="parsed", color="green")],
        update_every=5,
    )

    def _worker(start: int) -> None:
        for idx in range(10):
            session.item_completed({"parsed": 1}, last_item=f"obj-{start + idx}.xml")

    threads = [threading.Thread(target=_worker, args=(offset,)) for offset in (0, 10, 20, 30)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    session.complete()

    rendered = stream.getvalue()
    assert "\033[32m40\033[0m" in rendered
    assert "last:" in rendered


def test_console_progress_session_supports_dynamic_total_and_external_write(monkeypatch):
    stream = _FakeStream(is_tty=True)
    monotonic_values = iter([0.0, 60.0, 120.0, 180.0])
    monkeypatch.setattr("charity_status.ops.progress.time.monotonic", lambda: next(monotonic_values))
    session = ConsoleProgressSession(
        stream=stream,
        total_items=0,
        fields=[ProgressField(key="processed", label="processed", color="green")],
        update_every=1,
    )

    session.set_total_items(4)
    session.item_completed({"processed": 2}, last_item="eo1.csv:rows:1-2", completed_items=2)
    prepare_stream_for_external_write(stream)
    stream.write('{"component":"test"}\n')
    session.item_completed({"processed": 2}, last_item="eo2.csv:rows:1-2", completed_items=2)
    session.complete()

    rendered = stream.getvalue()
    assert '{"component":"test"}\n' in rendered
    assert "remaining:" in rendered
    assert "last:" in rendered
