#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DB_SCRIPT = REPO / "bin" / "phageflow_db.py"


def run_db(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DB_SCRIPT), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def touch_db(root: Path, tool: str, label: str = "manual_db") -> Path:
    path = root / tool / label
    path.mkdir(parents=True, exist_ok=True)
    (path / "marker.txt").write_text(f"{tool}\n")
    return path


def run_status_and_args_regression(tmp_path: Path) -> None:
    db_root = tmp_path / "db"
    checkv = touch_db(db_root, "checkv")
    pharokka = touch_db(db_root, "pharokka")
    phold = touch_db(db_root, "phold")

    status = run_db(["status", "--db-root", str(db_root), "--tools", "checkv,genomad,phold", "--json"])
    data = json.loads(status.stdout)
    rows = {row["tool"]: row for row in data["databases"]}
    assert rows["checkv"]["status"] == "available"
    assert rows["genomad"]["status"] == "missing"
    assert rows["phold"]["files"] == 1

    args = run_db(["run-args", "--db-root", str(db_root), "--tools", "structure"])
    assert "--run_pharokka true" in args.stdout
    assert f"--pharokka_db {pharokka}" in args.stdout
    assert "--run_phold true" in args.stdout
    assert f"--phold_db {phold}" in args.stdout

    command = run_db(
        [
            "heavy-command",
            "--db-root",
            str(db_root),
            "--tools",
            "checkv",
            "--input",
            "samples.tsv",
            "--outdir",
            "results/heavy",
        ]
    )
    assert "nextflow \\\n  run \\\n  main.nf" in command.stdout
    assert f"--checkv_db \\\n  {checkv}" in command.stdout


def run_dry_run_regression(tmp_path: Path) -> None:
    db_root = tmp_path / "db"
    result = run_db(
        [
            "prepare",
            "--db-root",
            str(db_root),
            "--tools",
            "checkv,phabox",
            "--dry-run",
        ]
    )
    assert "DRY_RUN\tcheckv download_database" in result.stdout
    assert "DRY_RUN\tdownload https://github.com/KennthShang/PhaBOX/releases/download/v2/phabox_db_v2_2.zip" in result.stdout
    assert "DRY_RUN\tdiamond makedb --in" in result.stdout
    assert "phabox_db_v2_2/RefVirus.faa" in result.stdout
    assert "phabox_db_v2_2/contamination.fasta" in result.stdout
    assert not db_root.exists()

    iphop = run_db(
        [
            "prepare",
            "--db-root",
            str(db_root),
            "--tools",
            "iphop",
            "--dry-run",
        ]
    )
    assert "DRY_RUN\tiphop download" in iphop.stdout
    assert "-dbv iPHoP.latest_rw --split" in iphop.stdout

    placeholder = run_db(["run-args", "--db-root", str(db_root), "--tools", "genomad", "--allow-missing"])
    assert "--run_genomad true --genomad_db /path/to/genomad_db" in placeholder.stdout

    missing = run_db(["run-args", "--db-root", str(db_root), "--tools", "genomad"], check=False)
    assert missing.returncode != 0
    assert "database for genomad is missing" in missing.stderr


def run_iphop_resume_staging_regression(tmp_path: Path) -> None:
    db_root = tmp_path / "db"
    stage = db_root / "iphop" / "staging" / "20260701_000000_123"
    stage.mkdir(parents=True)
    (stage / "partial_chunk.tar.gz").write_text("partial\n")

    result = run_db(
        [
            "update",
            "--db-root",
            str(db_root),
            "--tools",
            "iphop",
            "--dry-run",
        ]
    )
    assert f"DRY_RUN\treuse staging {stage}" in result.stdout
    assert f"--db_dir {stage}" in result.stdout

    fresh = run_db(
        [
            "update",
            "--db-root",
            str(db_root),
            "--tools",
            "iphop",
            "--dry-run",
            "--no-resume-staging",
        ]
    )
    assert "DRY_RUN\treuse staging" not in fresh.stdout
    assert "DRY_RUN\tmkdir -p" in fresh.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_status_and_args_regression(root / "status")
        run_dry_run_regression(root / "dry_run")
        run_iphop_resume_staging_regression(root / "resume")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
