#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_run(root: Path, method: str, orthogroups: int) -> None:
    write(
        root / "99_report" / "tables" / "pangenome_summary.tsv",
        "\n".join(
            [
                "metric\tvalue",
                f"method\t{method}",
                "genomes\t2",
                "proteins\t10",
                f"orthogroups\t{orthogroups}",
                "core_orthogroups\t1",
                "accessory_orthogroups\t2",
                "singleton_orthogroups\t3",
                "",
            ]
        ),
    )
    write(root / "99_report" / "index.html", "<html><body>ok</body></html>\n")
    write(root / "99_report" / "important_files.tsv", "category\tpath\tdescription\nreport\tindex.html\tHTML dashboard\n")
    write(root / "00_inputs" / "validation_summary.tsv", "metric\tvalue\ngenomes\t2\n")
    write(root / "00_inputs" / "samplesheet.normalized.tsv", "sample_id\tfasta\trole\thost_id\taccession\nsample_a\t/a.fa\tquery\t\t\n")


def run_pangenome_sensitivity_regression(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    make_run(left, "mmseqs", 4)
    make_run(right, "rbh_blastp", 5)

    comparison = tmp_path / "comparison.tsv"
    summary_tsv = tmp_path / "comparison_summary.tsv"
    summary_json = tmp_path / "comparison_summary.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "pangenome_sensitivity.py"),
            "--left",
            str(left),
            "--right",
            str(right),
            "--output",
            str(comparison),
            "--summary-output",
            str(summary_tsv),
            "--summary-json",
            str(summary_json),
            "--import-to-report",
            str(left),
        ],
        check=True,
    )

    imported_table = left / "99_report" / "tables" / "pangenome_sensitivity.tsv"
    imported_summary = left / "99_report" / "tables" / "pangenome_sensitivity_summary.tsv"
    imported_md = left / "99_report" / "pangenome_sensitivity_report.md"
    assert imported_table.exists()
    assert imported_summary.exists()
    assert imported_md.exists()

    rows = list(csv.DictReader(imported_table.open(), delimiter="\t"))
    by_metric = {row["metric"]: row for row in rows}
    assert by_metric["orthogroups"]["status"] == "different"
    assert by_metric["orthogroups"]["delta_right_minus_left"] == "1.0"

    summary = json.loads(summary_json.read_text())
    assert summary["detected"] is True
    assert summary["status_counts"]["different"] >= 1

    important = list(csv.DictReader((left / "99_report" / "important_files.tsv").open(), delimiter="\t"))
    important_paths = {row["path"] for row in important}
    assert "tables/pangenome_sensitivity.tsv" in important_paths
    assert "tables/pangenome_sensitivity_summary.tsv" in important_paths

    reimport = tmp_path / "reimport"
    make_run(reimport, "mmseqs", 4)
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "pangenome_sensitivity.py"),
            "--input",
            str(comparison),
            "--import-to-report",
            str(reimport),
        ],
        check=True,
    )
    assert (reimport / "99_report" / "tables" / "pangenome_sensitivity.tsv").exists()

    summary_out = tmp_path / "summary.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "summarize_run.py"),
            "--outdir",
            str(left),
            "--output",
            str(summary_out),
        ],
        check=True,
    )
    completed_summary = json.loads(summary_out.read_text())
    assert completed_summary["pangenome_sensitivity_summary"]["detected"] is True
    assert completed_summary["pangenome_sensitivity_summary"]["rows"] == len(rows)

    package_tar = tmp_path / "package.tar.gz"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "package_run.py"),
            "--outdir",
            str(left),
            "--output",
            str(package_tar),
            "--force",
        ],
        check=True,
    )
    with tarfile.open(package_tar, "r:gz") as tar:
        names = set(tar.getnames())
    assert "phageflow_package/99_report/tables/pangenome_sensitivity.tsv" in names
    assert "phageflow_package/99_report/tables/pangenome_sensitivity_summary.tsv" in names
    assert "phageflow_package/phageflow_pangenome_sensitivity_summary.tsv" in names


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_pangenome_sensitivity_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
