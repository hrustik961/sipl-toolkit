import json
from pathlib import Path

from sipl.cli import main

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_cli_check_valid_and_invalid(tmp_path: Path, capsys) -> None:
    valid_file = EXAMPLES_DIR / "power.sipl"
    rc_ok = main(["check", str(valid_file), "--json"])
    assert rc_ok == 0
    out_ok = json.loads(capsys.readouterr().out)
    assert out_ok["status"] == "ok"

    bad_file = tmp_path / "bad.sipl"
    bad_file.write_text("begin X = 1 end", encoding="utf-8")
    rc_err = main(["check", str(bad_file), "--json"])
    assert rc_err == 1
    out_err = json.loads(capsys.readouterr().out)
    assert out_err["status"] == "syntax_error"
    assert out_err["span"]["start_line"] == 1


def test_cli_run_power_json(capsys) -> None:
    rc = main(["run", str(EXAMPLES_DIR / "power.sipl"), "-s", "X=2", "Y=5", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ok"
    assert data["final_state"]["R"] == 32
    assert data["final_state"]["Y"] == 0


def test_cli_sem_and_viz_html(tmp_path: Path, capsys) -> None:
    rc_sem = main(["sem", str(EXAMPLES_DIR / "power.sipl"), "--json"])
    assert rc_sem == 0
    sem_data = json.loads(capsys.readouterr().out)
    assert "WH(" in sem_data["semantic_term"]
    assert len(sem_data["steps"]) > 0

    out_html = tmp_path / "compare.html"
    rc_viz = main(["viz", str(EXAMPLES_DIR / "gcd.sipl"), "--tree", "compare", "-o", str(out_html)])
    assert rc_viz == 0
    assert out_html.is_file()
    assert "<svg" in out_html.read_text(encoding="utf-8")