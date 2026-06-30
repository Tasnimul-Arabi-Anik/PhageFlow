#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run_optional_tool_summary_regression(tmp_path: Path) -> None:
    samplesheet = tmp_path / "samplesheet.normalized.tsv"
    write(
        samplesheet,
        "sample_id\tfasta\trole\thost_id\taccession\n"
        "sample_a\t/a.fa\tquery\t\t\n"
        "sample_b\t/b.fa\treference\t\t\n",
    )

    trnascan = tmp_path / "sample_a.trnascan.tsv"
    bacphlip = tmp_path / "sample_a.bacphlip.log"
    abricate = tmp_path / "sample_a.abricate.tsv"
    checkv = tmp_path / "sample_a.checkv"
    pharokka = tmp_path / "sample_a.pharokka"
    genomad = tmp_path / "sample_a.genomad"
    phold = tmp_path / "sample_a.phold"
    clinker = tmp_path / "clinker_synteny.html"
    gbk_files = tmp_path / "gbk_files.txt"

    write(trnascan, "seq\ttype\tstart\tend\ncontig1\ttRNA\t1\t10\n")
    write(bacphlip, "completed\n")
    write(abricate, "file\tsequence\tstart\tend\n")
    write(checkv / "quality_summary.tsv", "contig_id\tcontig_length\ncontig1\t1000\n")
    write(pharokka / "sample_a_cds_functions.tsv", "gene\tfunction\nx\ty\n")
    write(genomad / "sample_a_summary.tsv", "seq_name\tlength\ncontig1\t1000\n")
    write(phold / "sample_a_confidence.tsv", "cds\tconfidence\ncds1\t0.9\n")
    write(clinker, "<html><body>ok</body></html>\n")
    write(gbk_files, "sample_a.gbk\nsample_b.gbk\n")

    output = tmp_path / "optional_tool_summary.tsv"
    summary_json = tmp_path / "optional_tool_summary.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "optional_tool_summary.py"),
            "--samplesheet",
            str(samplesheet),
            "--trnascan-artifact",
            str(trnascan),
            "--bacphlip-artifact",
            str(bacphlip),
            "--abricate-artifact",
            str(abricate),
            "--checkv-artifact",
            str(checkv),
            "--pharokka-artifact",
            str(pharokka),
            "--genomad-artifact",
            str(genomad),
            "--phold-artifact",
            str(phold),
            "--clinker-artifact",
            str(clinker),
            "--clinker-artifact",
            str(gbk_files),
            "--output",
            str(output),
            "--summary-json",
            str(summary_json),
        ],
        check=True,
    )

    rows = list(csv.DictReader(output.open(), delimiter="\t"))
    by_tool_sample = {(row["tool"], row["sample_id"]): row for row in rows}

    for tool in ["trnascan", "bacphlip", "abricate", "checkv", "pharokka", "genomad", "phold"]:
        assert by_tool_sample[(tool, "sample_a")]["status"] == "available"
        assert by_tool_sample[(tool, "sample_b")]["status"] == "not_run"

    assert by_tool_sample[("trnascan", "sample_a")]["primary_artifact_type"] == "trna_table"
    assert by_tool_sample[("abricate", "sample_a")]["primary_artifact_type"] == "screen_table"
    assert by_tool_sample[("clinker", "COHORT")]["status"] == "available"
    assert by_tool_sample[("clinker", "COHORT")]["records"] == "2"

    summary = json.loads(summary_json.read_text())
    assert summary["available_tools"] == [
        "abricate",
        "bacphlip",
        "checkv",
        "clinker",
        "genomad",
        "pharokka",
        "phold",
        "trnascan",
    ]
    assert summary["status_counts"]["available"] == 8
    assert summary["status_counts"]["not_run"] == 7


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_optional_tool_summary_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
