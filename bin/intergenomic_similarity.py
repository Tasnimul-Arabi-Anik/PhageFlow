#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import tempfile
from itertools import combinations
from pathlib import Path


PAIR_FIELDS = [
    "sample_a",
    "sample_b",
    "mean_identity_pct",
    "aligned_fraction_min",
    "aligned_fraction_mean",
    "similarity_score_pct",
    "a_to_b_query_aligned_fraction",
    "b_to_a_query_aligned_fraction",
    "a_to_b_weighted_identity_pct",
    "b_to_a_weighted_identity_pct",
    "a_to_b_hsp_count",
    "b_to_a_hsp_count",
    "status",
]

BLAST_FIELDS = [
    "qseqid",
    "sseqid",
    "pident",
    "length",
    "mismatch",
    "gapopen",
    "qstart",
    "qend",
    "sstart",
    "send",
    "evalue",
    "bitscore",
    "qlen",
    "slen",
]


class Sample:
    def __init__(self, sample_id: str, fasta: Path, acgt_bp: int, total_bp: int) -> None:
        self.sample_id = sample_id
        self.fasta = fasta
        self.acgt_bp = acgt_bp
        self.total_bp = total_bp


def load_samplesheet(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def resolve_fasta(raw: str, samplesheet: Path) -> Path:
    fasta = Path(raw)
    if not fasta.is_absolute():
        fasta = samplesheet.parent / fasta
    return fasta.resolve()


def fasta_lengths(path: Path) -> tuple[int, int]:
    total = 0
    acgt = 0
    with path.open() as handle:
        for raw in handle:
            line = raw.strip().upper()
            if not line or line.startswith(">"):
                continue
            total += len(line)
            acgt += sum(1 for base in line if base in "ACGT")
    return acgt, total


def load_samples(path: Path) -> list[Sample]:
    samples = []
    for row in load_samplesheet(path):
        sample_id = row.get("sample_id", "").strip()
        fasta = resolve_fasta(row.get("fasta", ""), path)
        acgt_bp, total_bp = fasta_lengths(fasta)
        samples.append(Sample(sample_id, fasta, acgt_bp, total_bp))
    return samples


def merge_intervals(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    normalized = [(min(start, end), max(start, end)) for start, end in intervals]
    normalized.sort()
    merged: list[tuple[int, int]] = []
    for start, end in normalized:
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return sum(end - start + 1 for start, end in merged)


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, text=True, capture_output=True)


def make_databases(samples: list[Sample], makeblastdb_bin: str, workdir: Path) -> dict[str, Path]:
    db_dir = workdir / "blastdb"
    db_dir.mkdir(parents=True, exist_ok=True)
    dbs = {}
    for sample in samples:
        db_prefix = db_dir / sample.sample_id
        run_command([makeblastdb_bin, "-in", str(sample.fasta), "-dbtype", "nucl", "-out", str(db_prefix)])
        dbs[sample.sample_id] = db_prefix
    return dbs


def blast_direction(
    query: Sample,
    subject: Sample,
    db_prefix: Path,
    blastn_bin: str,
    threads: int,
    min_identity: float,
    min_aln_len: int,
    max_evalue: str,
) -> dict[str, float | int]:
    command = [
        blastn_bin,
        "-query",
        str(query.fasta),
        "-db",
        str(db_prefix),
        "-task",
        "blastn",
        "-dust",
        "no",
        "-soft_masking",
        "false",
        "-perc_identity",
        str(min_identity),
        "-evalue",
        str(max_evalue),
        "-num_threads",
        str(max(1, threads)),
        "-outfmt",
        "6 " + " ".join(BLAST_FIELDS),
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)

    hsp_count = 0
    aligned_bp = 0
    identity_weighted_sum = 0.0
    query_intervals: dict[str, list[tuple[int, int]]] = {}
    subject_intervals: dict[str, list[tuple[int, int]]] = {}
    for raw in completed.stdout.splitlines():
        if not raw.strip():
            continue
        values = raw.rstrip("\n").split("\t")
        if len(values) != len(BLAST_FIELDS):
            continue
        hit = dict(zip(BLAST_FIELDS, values))
        length = int(float(hit["length"]))
        pident = float(hit["pident"])
        if length < min_aln_len or pident < min_identity:
            continue
        hsp_count += 1
        aligned_bp += length
        identity_weighted_sum += pident * length
        query_intervals.setdefault(hit["qseqid"], []).append((int(hit["qstart"]), int(hit["qend"])))
        subject_intervals.setdefault(hit["sseqid"], []).append((int(hit["sstart"]), int(hit["send"])))

    query_covered_bp = sum(merge_intervals(items) for items in query_intervals.values())
    subject_covered_bp = sum(merge_intervals(items) for items in subject_intervals.values())
    query_denominator = max(query.acgt_bp, query.total_bp, 1)
    subject_denominator = max(subject.acgt_bp, subject.total_bp, 1)
    weighted_identity = identity_weighted_sum / aligned_bp if aligned_bp else 0.0
    return {
        "hsp_count": hsp_count,
        "aligned_bp": aligned_bp,
        "query_covered_bp": query_covered_bp,
        "subject_covered_bp": subject_covered_bp,
        "query_aligned_fraction": min(1.0, query_covered_bp / query_denominator),
        "subject_aligned_fraction": min(1.0, subject_covered_bp / subject_denominator),
        "weighted_identity_pct": weighted_identity,
    }


def pair_status(score: float) -> str:
    if score >= 95.0:
        return "high_intergenomic_similarity"
    if score >= 70.0:
        return "moderate_intergenomic_similarity"
    if score > 0.0:
        return "low_or_fragmentary_similarity"
    return "no_detectable_similarity"


def write_pairs(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIR_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_key_value(path: Path, values: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in values.items():
            writer.writerow([key, value])


def write_matrix(path: Path, samples: list[Sample], values: dict[tuple[str, str], float], diagonal: float, fmt: str) -> None:
    ids = [sample.sample_id for sample in samples]
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["sample_id"] + ids)
        for row_id in ids:
            row = [row_id]
            for col_id in ids:
                if row_id == col_id:
                    value = diagonal
                else:
                    value = values.get((row_id, col_id), values.get((col_id, row_id), 0.0))
                row.append(format(value, fmt))
            writer.writerow(row)


def write_note(path: Path, status: str) -> None:
    path.write_text(
        "# BLASTN Intergenomic Similarity\n\n"
        "PhageFlow estimates whole-genome relatedness with reciprocal all-vs-all BLASTN. "
        "For each genome pair, accepted local HSPs are summarized as weighted nucleotide identity "
        "and reciprocal aligned fractions. The report heatmap uses a conservative similarity score: "
        "mean reciprocal identity multiplied by the minimum reciprocal aligned fraction. This prevents "
        "short high-identity regions from being interpreted as high whole-genome similarity.\n\n"
        f"Status: `{status}`. This module is a lightweight local screening method, not a drop-in replacement "
        "for database-backed phage taxonomy tools or formal VIRIDIC-style classification.\n"
    )


def skipped_outputs(samples: list[Sample], args: argparse.Namespace, status: str, reason: str) -> None:
    write_pairs(args.pairs, [])
    write_matrix(args.similarity_matrix, samples, {}, 100.0, ".3f")
    write_matrix(args.distance_matrix, samples, {}, 0.0, ".6f")
    write_key_value(
        args.summary,
        {
            "method": "blastn_intergenomic_similarity",
            "status": status,
            "reason": reason,
            "genomes": str(len(samples)),
            "pairwise_comparisons": "0",
            "min_identity_pct": str(args.min_identity),
            "min_aln_len": str(args.min_aln_len),
            "max_evalue": str(args.max_evalue),
        },
    )
    write_note(args.note, status)


def run_analysis(samples: list[Sample], args: argparse.Namespace) -> None:
    pair_rows: list[dict[str, str]] = []
    similarity_values: dict[tuple[str, str], float] = {}
    distance_values: dict[tuple[str, str], float] = {}
    scores = []

    with tempfile.TemporaryDirectory(prefix="phageflow_blastn_") as tmp:
        workdir = Path(tmp)
        dbs = make_databases(samples, args.makeblastdb_bin, workdir)
        by_id = {sample.sample_id: sample for sample in samples}
        for left, right in combinations(samples, 2):
            forward = blast_direction(
                left,
                right,
                dbs[right.sample_id],
                args.blastn_bin,
                args.threads,
                args.min_identity,
                args.min_aln_len,
                args.max_evalue,
            )
            reverse = blast_direction(
                right,
                left,
                dbs[left.sample_id],
                args.blastn_bin,
                args.threads,
                args.min_identity,
                args.min_aln_len,
                args.max_evalue,
            )
            identities = [
                float(forward["weighted_identity_pct"]),
                float(reverse["weighted_identity_pct"]),
            ]
            fractions = [
                float(forward["query_aligned_fraction"]),
                float(reverse["query_aligned_fraction"]),
            ]
            mean_identity = statistics.mean(identities) if any(identities) else 0.0
            aligned_fraction_min = min(fractions) if all(value > 0 for value in fractions) else 0.0
            aligned_fraction_mean = statistics.mean(fractions)
            score = mean_identity * aligned_fraction_min
            distance = 1.0 - (score / 100.0)
            scores.append(score)
            similarity_values[(left.sample_id, right.sample_id)] = score
            distance_values[(left.sample_id, right.sample_id)] = max(0.0, min(1.0, distance))
            pair_rows.append(
                {
                    "sample_a": left.sample_id,
                    "sample_b": right.sample_id,
                    "mean_identity_pct": f"{mean_identity:.3f}",
                    "aligned_fraction_min": f"{aligned_fraction_min:.6f}",
                    "aligned_fraction_mean": f"{aligned_fraction_mean:.6f}",
                    "similarity_score_pct": f"{score:.3f}",
                    "a_to_b_query_aligned_fraction": f"{float(forward['query_aligned_fraction']):.6f}",
                    "b_to_a_query_aligned_fraction": f"{float(reverse['query_aligned_fraction']):.6f}",
                    "a_to_b_weighted_identity_pct": f"{float(forward['weighted_identity_pct']):.3f}",
                    "b_to_a_weighted_identity_pct": f"{float(reverse['weighted_identity_pct']):.3f}",
                    "a_to_b_hsp_count": str(int(forward["hsp_count"])),
                    "b_to_a_hsp_count": str(int(reverse["hsp_count"])),
                    "status": pair_status(score),
                }
            )

    write_pairs(args.pairs, pair_rows)
    write_matrix(args.similarity_matrix, samples, similarity_values, 100.0, ".3f")
    write_matrix(args.distance_matrix, samples, distance_values, 0.0, ".6f")
    write_key_value(
        args.summary,
        {
            "method": "blastn_intergenomic_similarity",
            "status": "completed",
            "genomes": str(len(samples)),
            "pairwise_comparisons": str(len(pair_rows)),
            "mean_similarity_score_pct": f"{statistics.mean(scores):.3f}" if scores else "0.000",
            "median_similarity_score_pct": f"{statistics.median(scores):.3f}" if scores else "0.000",
            "max_similarity_score_pct": f"{max(scores):.3f}" if scores else "0.000",
            "high_similarity_pairs_95": str(sum(1 for score in scores if score >= 95.0)),
            "high_similarity_pairs_70": str(sum(1 for score in scores if score >= 70.0)),
            "min_identity_pct": str(args.min_identity),
            "min_aln_len": str(args.min_aln_len),
            "max_evalue": str(args.max_evalue),
        },
    )
    write_note(args.note, "completed")


def main() -> int:
    parser = argparse.ArgumentParser(description="BLASTN-based intergenomic similarity for phage cohorts.")
    parser.add_argument("--samplesheet", required=True, type=Path)
    parser.add_argument("--blastn-bin", default="blastn")
    parser.add_argument("--makeblastdb-bin", default="makeblastdb")
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--min-identity", default=70.0, type=float)
    parser.add_argument("--min-aln-len", default=100, type=int)
    parser.add_argument("--max-evalue", default="1e-5")
    parser.add_argument("--max-genomes", default=100, type=int)
    parser.add_argument("--skip-reason", default="")
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--similarity-matrix", required=True, type=Path)
    parser.add_argument("--distance-matrix", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--note", required=True, type=Path)
    args = parser.parse_args()

    samples = load_samples(args.samplesheet)
    if args.skip_reason:
        skipped_outputs(samples, args, "skipped", args.skip_reason)
        return 0
    if len(samples) <= 1:
        skipped_outputs(samples, args, "single_genome_skipped", "intergenomic comparisons require at least two genomes")
        return 0
    if len(samples) > args.max_genomes:
        skipped_outputs(samples, args, "max_genomes_skipped", f"{len(samples)} genomes exceeds --max-genomes {args.max_genomes}")
        return 0
    run_analysis(samples, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
