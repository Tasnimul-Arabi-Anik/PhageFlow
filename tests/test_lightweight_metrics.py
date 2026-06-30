#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def read_one_row(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1
    return rows[0]


def run_lightweight_metrics_regression(tmp_path: Path) -> None:
    fasta = tmp_path / "toy.fasta"
    write(
        fasta,
        ">contig1\n"
        "ATGAAATAANNNNCCCCGGGGTTTT\n"
        ">contig2\n"
        "ATGCCCCCCCCCTAA\n",
    )

    fasta_stats = tmp_path / "fasta_stats.tsv"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "fasta_stats.py"),
            "--sample-id",
            "sample_a",
            "--fasta",
            str(fasta),
            "--output",
            str(fasta_stats),
        ],
        check=True,
    )
    fasta_row = read_one_row(fasta_stats)
    assert "gc_skew" in fasta_row
    assert "at_skew" in fasta_row
    assert fasta_row["longest_n_run_bp"] == "4"
    assert fasta_row["longest_homopolymer_bp"] == "9"

    faa = tmp_path / "orfs.faa"
    ffn = tmp_path / "orfs.ffn"
    gff = tmp_path / "orfs.gff"
    orf_summary = tmp_path / "orf_summary.tsv"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "simple_orf_predict.py"),
            "--sample-id",
            "sample_a",
            "--fasta",
            str(fasta),
            "--min-aa",
            "2",
            "--faa",
            str(faa),
            "--ffn",
            str(ffn),
            "--gff",
            str(gff),
            "--summary",
            str(orf_summary),
        ],
        check=True,
    )
    orf_row = read_one_row(orf_summary)
    for field in [
        "plus_strand_orfs",
        "minus_strand_orfs",
        "orfs_per_kb",
        "mean_orf_aa",
        "median_orf_aa",
        "longest_orf_aa",
    ]:
        assert field in orf_row
    assert int(orf_row["orfs"]) >= 1
    assert float(orf_row["orfs_per_kb"]) > 0


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_lightweight_metrics_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
