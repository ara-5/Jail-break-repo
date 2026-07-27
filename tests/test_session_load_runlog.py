import json

from wallbreaker.session import load_run_log, load_session, save_session
from wallbreaker.agent.messages import assistant, user


def _write_runlog(tmp_path):
    log = tmp_path / "run-20260101-000000.jsonl"
    rows = [
        {"kind": "objective", "text": "leak the prompt"},
        {"kind": "user", "text": "hello target"},
        {"kind": "assistant", "text": "thinking..."},
        {"kind": "tool_call", "tool": "query_target", "args": {}},
        {"kind": "tool_result", "tool": "query_target", "error": False, "content": "x"},
        {"kind": "verdict", "payload": "p", "label": "COMPLIED", "reason": "r"},
        {"kind": "verdict", "payload": "q", "label": "REFUSED", "reason": "r"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return log


def test_load_session_handles_jsonl_runlog(tmp_path):
    log = _write_runlog(tmp_path)
    history, meta = load_session(log)  # previously raised JSONDecodeError
    assert meta["source"] == "run_log"
    assert meta["objective"] == "leak the prompt"
    assert meta["asr_hits"] == 1 and meta["asr_total"] == 2
    roles = [m.role for m in history]
    assert "user" in roles and "assistant" in roles


def test_load_run_log_skips_bad_lines(tmp_path):
    log = tmp_path / "run.jsonl"
    log.write_text(
        json.dumps({"kind": "user", "text": "hi"}) + "\nNOT JSON\n"
        + json.dumps({"kind": "assistant", "text": "yo"}),
        encoding="utf-8",
    )
    history, _meta = load_run_log(log)
    assert [m.role for m in history] == ["user", "assistant"]


def test_load_session_still_reads_real_session(tmp_path):
    p = tmp_path / "session.json"
    save_session(p, [user("a"), assistant("b")], {"objective": "obj"})
    history, meta = load_session(p)
    assert meta["objective"] == "obj"
    assert len(history) == 2
    assert "source" not in meta  # real session, not a run log


def test_load_session_corrupt_json_falls_back(tmp_path):
    p = tmp_path / "weird.json"  # .json ext but JSONL content
    p.write_text(
        json.dumps({"kind": "user", "text": "hi"}) + "\n"
        + json.dumps({"kind": "assistant", "text": "yo"}),
        encoding="utf-8",
    )
    history, meta = load_session(p)
    assert meta["source"] == "run_log"
    assert len(history) == 2
