import json

from api.context import reset_session_context, set_session_context, set_thread_context
from api.monitor import monitor


def test_persist_trace_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEARCH_OUTPUT_ROOT", str(tmp_path))
    s_token = set_session_context("/sess/t-1")
    t_token = set_thread_context("t-1")
    try:
        monitor._emit("tool_start", "开始执行工具: x", {"tool_name": "x"})
    finally:
        reset_session_context(s_token, t_token)

    trace_file = tmp_path / "session_t-1" / "trace.jsonl"
    assert trace_file.exists()
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "tool_start"
    assert payload["data"]["tool_name"] == "x"


def test_no_thread_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEARCH_OUTPUT_ROOT", str(tmp_path))
    monitor._emit("task_result", "done", {"result": "ok"})
    assert not (tmp_path / "session_").exists() or not list(tmp_path.glob("session_*/trace.jsonl"))