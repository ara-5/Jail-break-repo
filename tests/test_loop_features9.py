import json

from wallbreaker.cli import main
from wallbreaker.report import latest_run_log, resolve_log_path


def _mk(path, label="COMPLIED"):
    path.write_text(
        json.dumps({"kind": "verdict", "payload": "p", "label": label, "reason": "r"}),
        encoding="utf-8",
    )
    return path


def test_latest_run_log_picks_newest(tmp_path):
    (tmp_path / "run-20260101-000000.jsonl").write_text("{}", encoding="utf-8")
    newest = tmp_path / "run-20260601-000000.jsonl"
    newest.write_text("{}", encoding="utf-8")
    assert latest_run_log(tmp_path) == newest


def test_latest_run_log_none_when_empty(tmp_path):
    assert latest_run_log(tmp_path) is None
    assert latest_run_log(tmp_path / "nope") is None


def test_resolve_log_path_variants(tmp_path):
    f = _mk(tmp_path / "run-20260101-000000.jsonl")
    # explicit file
    assert resolve_log_path(str(f)) == f
    # directory -> latest within
    assert resolve_log_path(str(tmp_path)) == f
    # missing -> None
    assert resolve_log_path(str(tmp_path / "ghost.jsonl")) is None


def test_cli_report_resolves_directory(tmp_path, capsys):
    _mk(tmp_path / "run-20260101-000000.jsonl")
    rc = main(["report", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Red-team engagement report" in out


def test_cli_export_missing_log_errors(tmp_path):
    rc = main(["export", str(tmp_path / "empty_dir")])
    assert rc == 1
