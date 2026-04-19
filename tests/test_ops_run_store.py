from verification.ops.run_store import InMemoryRunStore, safe_error_summary


def test_safe_error_summary_redaction():
    summary = safe_error_summary(
        [
            {"code": "parse_error", "error": "token=abcd"},
            {"code": "network_error", "error": "timeout"},
        ]
    )
    assert summary["count"] == 2
    assert summary["samples"][0]["message"] == "redacted_sensitive_error"
    assert summary["samples"][1]["message"] == "timeout"


def test_inmemory_run_store_basic_roundtrip():
    store = InMemoryRunStore()
    store.write_ingest_run("ing-1", {"ingest_run_id": "ing-1"})
    store.write_ingest_filings("ing-1", [{"ein": "123456789"}])
    store.write_refresh_run("ref-1", {"refresh_run_id": "ref-1"})
    store.write_refresh_eins("ref-1", [{"ein": "123456789"}])
    assert store.get_run("ingest", "ing-1") is not None
    assert store.get_run_items("ingest", "ing-1", "filings") is not None
    assert store.get_run("refresh", "ref-1") is not None
    assert store.get_run_items("refresh", "ref-1", "eins") is not None

