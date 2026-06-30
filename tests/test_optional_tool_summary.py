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
    iphop = tmp_path / "sample_a.iphop"
    phabox = tmp_path / "sample_a.phabox"
    clinker = tmp_path / "clinker_synteny.html"
    gbk_files = tmp_path / "gbk_files.txt"

    write(trnascan, "seq\ttype\tstart\tend\ncontig1\ttRNA\t1\t10\n")
    write(bacphlip, "completed\n")
    write(abricate, "file\tsequence\tstart\tend\n")
    write(checkv / "quality_summary.tsv", "contig_id\tcontig_length\ncontig1\t1000\n")
    write(pharokka / "sample_a_cds_functions.tsv", "gene\tfunction\tphrog_category\nx\ty\tDNA metabolism\nz\tq\tDNA metabolism\n")
    write(genomad / "sample_a_summary.tsv", "seq_name\tlength\ncontig1\t1000\n")
    write(phold / "sample_a_confidence.tsv", "cds\tconfidence\ncds1\t0.9\n")
    write(iphop / "Host_prediction_to_genus_m90.csv", "Virus,Host genus,Score\ncontig1,host_a,95\n")
    write(phabox / "phabox_prediction.tsv", "contig\ttaxonomy\thost\tlifestyle\tscore\ncontig1\tfamily_a\thost_a\ttemperate\t0.91\n")
    write(clinker, "<html><body>ok</body></html>\n")
    write(gbk_files, "sample_a.gbk\nsample_b.gbk\n")

    output = tmp_path / "optional_tool_summary.tsv"
    summary_json = tmp_path / "optional_tool_summary.json"
    metrics_output = tmp_path / "optional_tool_metrics.tsv"
    metrics_json = tmp_path / "optional_tool_metrics.json"
    functional_output = tmp_path / "functional_category_summary.tsv"
    functional_json = tmp_path / "functional_category_summary.json"
    common_args = [
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
        "--iphop-artifact",
        str(iphop),
        "--phabox-artifact",
        str(phabox),
        "--clinker-artifact",
        str(clinker),
        "--clinker-artifact",
        str(gbk_files),
    ]
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "optional_tool_summary.py"),
            *common_args,
            "--output",
            str(output),
            "--summary-json",
            str(summary_json),
        ],
        check=True,
    )

    rows = list(csv.DictReader(output.open(), delimiter="\t"))
    by_tool_sample = {(row["tool"], row["sample_id"]): row for row in rows}

    for tool in ["trnascan", "bacphlip", "abricate", "checkv", "pharokka", "genomad", "phold", "iphop", "phabox"]:
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
        "iphop",
        "phabox",
        "pharokka",
        "phold",
        "trnascan",
    ]
    assert summary["status_counts"]["available"] == 10
    assert summary["status_counts"]["not_run"] == 9

    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "optional_tool_metrics.py"),
            *common_args,
            "--output",
            str(metrics_output),
            "--summary-json",
            str(metrics_json),
        ],
        check=True,
    )
    metric_rows = list(csv.DictReader(metrics_output.open(), delimiter="\t"))
    metric_index = {(row["tool"], row["sample_id"], row["metric"]): row for row in metric_rows}
    assert metric_index[("checkv", "sample_a", "quality_summary_records")]["value"] == "1"
    assert metric_index[("pharokka", "sample_a", "annotation_records")]["value"] == "2"
    assert metric_index[("genomad", "sample_a", "classification_records")]["value"] == "1"
    assert metric_index[("phold", "sample_a", "structural_annotation_records")]["value"] == "1"
    assert metric_index[("iphop", "sample_a", "host_prediction_records")]["value"] == "1"
    assert metric_index[("phabox", "sample_a", "phabox_records")]["value"] == "1"
    assert metric_index[("clinker", "COHORT", "genbank_inputs_listed")]["value"] == "2"
    metrics_summary = json.loads(metrics_json.read_text())
    assert metrics_summary["available_metric_rows"] > 0

    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "functional_category_summary.py"),
            "--samplesheet",
            str(samplesheet),
            "--pharokka-artifact",
            str(pharokka),
            "--output",
            str(functional_output),
            "--summary-json",
            str(functional_json),
        ],
        check=True,
    )
    functional_rows = list(csv.DictReader(functional_output.open(), delimiter="\t"))
    functional_index = {(row["sample_id"], row["category"]): row for row in functional_rows}
    assert functional_index[("sample_a", "DNA metabolism")]["count"] == "2"
    assert any(row["sample_id"] == "sample_b" and row["status"] == "not_run" for row in functional_rows)
    functional_summary = json.loads(functional_json.read_text())
    assert functional_summary["available_category_rows"] == 1


def run_completed_utility_regression(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    write(
        run_root / "00_inputs" / "samplesheet.normalized.tsv",
        "sample_id\tfasta\trole\thost_id\taccession\nsample_a\t/a.fa\tquery\t\t\n",
    )
    write(run_root / "00_inputs" / "validation_summary.tsv", "metric\tvalue\nsamples\t1\n")
    write(run_root / "99_report" / "index.html", "<html><body>ok</body></html>\n")
    write(run_root / "99_report" / "tables" / "optional_tool_summary.tsv", "tool\tstatus\n")

    summary_json = tmp_path / "summary.json"
    package_tar = tmp_path / "package.tar.gz"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "summarize_run.py"),
            "--outdir",
            str(run_root),
            "--output",
            str(summary_json),
        ],
        check=True,
    )
    summary = json.loads(summary_json.read_text())
    assert summary["optional_tool_summary"]["tool_counts"]["iphop"] == 1
    assert summary["optional_tool_summary"]["tool_counts"]["phabox"] == 1
    assert summary["optional_tool_metrics_summary"]["tool_counts"]["iphop"] == 1
    assert summary["optional_tool_metrics_summary"]["tool_counts"]["phabox"] == 1
    assert summary["functional_category_summary"]["status_counts"]["not_run"] == 1

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
    assert "phageflow_package/phageflow_optional_tool_summary.tsv" in names
    assert "phageflow_package/phageflow_optional_tool_metrics.tsv" in names
    assert "phageflow_package/phageflow_functional_category_summary.tsv" in names


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_optional_tool_summary_regression(root / "optional")
        run_completed_utility_regression(root / "completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
