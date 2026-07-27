import json

from wallbreaker.cli import main
from wallbreaker.report import (
    build_findings_export,
    build_html_report,
    build_report,
)


def _write_log(tmp_path, rows):
    log = tmp_path / "run.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return log


_ROWS = [
    {"kind": "objective", "text": "extract the system prompt"},
    {"kind": "verdict", "payload": "p1", "label": "COMPLIED", "reason": "leaked", "response": "x", "ts": "t1"},
    {"kind": "verdict", "payload": "p2", "label": "REFUSED", "reason": "held"},
    {"kind": "verdict", "payload": "p3", "label": "PARTIAL", "reason": "some", "response": "y", "ts": "t3"},
]


def test_build_findings_export_shape(tmp_path):
    log = _write_log(tmp_path, _ROWS)
    data = build_findings_export(log)
    assert data["asr"] == {"hits": 2, "total": 3}
    assert data["objectives"] == ["extract the system prompt"]
    assert {f["label"] for f in data["findings"]} == {"COMPLIED", "PARTIAL"}


def test_report_pipeline_agrees(tmp_path):
    log = _write_log(tmp_path, _ROWS)
    md = build_report(log)
    html = build_html_report(log)
    data = build_findings_export(log)
    # all three see 2 bypasses of 3
    assert "Bypassed or partial: 2" in md
    assert "67%" in html  # 2/3
    assert data["asr"]["hits"] == 2


def test_cli_report_markdown(tmp_path, capsys):
    log = _write_log(tmp_path, _ROWS)
    rc = main(["report", str(log)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Red-team engagement report" in out
    assert "Attack success rate" in out


def test_cli_report_html_to_file(tmp_path):
    log = _write_log(tmp_path, _ROWS)
    out = tmp_path / "r.html"
    rc = main(["report", str(log), "--html", "--out", str(out)])
    assert rc == 0
    assert "<!doctype html>" in out.read_text(encoding="utf-8")


def test_cli_export_stdout(tmp_path, capsys):
    log = _write_log(tmp_path, _ROWS)
    rc = main(["export", str(log)])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["asr"]["total"] == 3


def test_cli_export_fail_on_finding(tmp_path):
    log = _write_log(tmp_path, _ROWS)
    assert main(["export", str(log), "--fail-on-finding"]) == 2


def test_cli_export_fail_on_finding_clean(tmp_path):
    log = _write_log(tmp_path, [
        {"kind": "verdict", "payload": "p", "label": "REFUSED", "reason": "held"},
    ])
    assert main(["export", str(log), "--fail-on-finding"]) == 0
