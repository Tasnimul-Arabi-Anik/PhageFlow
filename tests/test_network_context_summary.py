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


def make_run(root: Path) -> None:
    write(root / "99_report" / "index.html", "<html><body>ok</body></html>\n")
    write(root / "99_report" / "important_files.tsv", "category\tpath\tdescription\nreport\tindex.html\tHTML dashboard\n")
    write(root / "00_inputs" / "validation_summary.tsv", "metric\tvalue\ngenomes\t2\n")
    write(root / "00_inputs" / "samplesheet.normalized.tsv", "sample_id\tfasta\trole\thost_id\taccession\nsample_a\t/a.fa\tquery\t\t\n")


def run_network_context_regression(tmp_path: Path) -> None:
    vcontact = tmp_path / "vcontact"
    write(
        vcontact / "genome_by_genome_overview.csv",
        "Genome,VC,Cluster status\nsample_a,VC_1,assigned\nsample_b,VC_1,assigned\n",
    )
    write(vcontact / "viral_cluster_overview.csv", "VC,Size\nVC_1,2\n")
    write(vcontact / "c1.ntw", "sample_a sample_b 0.8\nsample_b sample_c 0.5\n")

    run_root = tmp_path / "run"
    make_run(run_root)
    output = tmp_path / "network_context_summary.tsv"
    summary_json = tmp_path / "network_context_summary.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "network_context_summary.py"),
            "--vcontact-dir",
            str(vcontact),
            "--output",
            str(output),
            "--summary-json",
            str(summary_json),
            "--import-to-report",
            str(run_root),
        ],
        check=True,
    )

    imported = run_root / "99_report" / "tables" / "network_context_summary.tsv"
    assert imported.exists()
    rows = list(csv.DictReader(imported.open(), delimiter="\t"))
    metrics = {row["metric"]: row for row in rows}
    assert metrics["genome_overview_records"]["value"] == "2"
    assert metrics["genome_overview_unique_cluster_values_detected"]["value"] == "1"
    assert metrics["network_edges"]["value"] == "2"
    assert metrics["network_nodes_detected"]["value"] == "3"
    summary = json.loads(summary_json.read_text())
    assert summary["available_rows"] > 0

    summary_out = tmp_path / "summary.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "summarize_run.py"),
            "--outdir",
            str(run_root),
            "--output",
            str(summary_out),
        ],
        check=True,
    )
    completed_summary = json.loads(summary_out.read_text())
    assert completed_summary["network_context_summary"]["detected"] is True
    assert completed_summary["network_context_summary"]["available_rows"] > 0

    package_tar = tmp_path / "package.tar.gz"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "package_run.py"),
            "--outdir",
            str(run_root),
            "--output",
            str(package_tar),
            "--force",
        ],
        check=True,
    )
    with tarfile.open(package_tar, "r:gz") as tar:
        names = set(tar.getnames())
    assert "phageflow_package/99_report/tables/network_context_summary.tsv" in names
    assert "phageflow_package/99_report/network_context_report.md" in names


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_network_context_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
