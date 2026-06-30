#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from itertools import combinations
from pathlib import Path


RC_TABLE = str.maketrans("ACGTacgt", "TGCAtgca")


def reverse_complement(sequence: str) -> str:
    return sequence.translate(RC_TABLE)[::-1].upper()


def parse_fasta(path: Path) -> str:
    seq = []
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith(">"):
                continue
            seq.append(line.upper())
    return "".join(seq)


def load_samplesheet(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def canonical_kmers(sequence: str, k: int) -> set[str]:
    kmers = set()
    for i in range(0, len(sequence) - k + 1):
        kmer = sequence[i : i + k]
        if any(base not in "ACGT" for base in kmer):
            continue
        rc = reverse_complement(kmer)
        kmers.add(kmer if kmer <= rc else rc)
    return kmers


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left & right) / len(left | right)


def interpretation(same_hash: bool, score: float, duplicate_threshold: float) -> str:
    if same_hash:
        return "exact_duplicate"
    if score >= duplicate_threshold:
        return "near_duplicate"
    if score >= 0.50:
        return "highly_similar"
    if score >= 0.10:
        return "related_or_shared_regions"
    return "low_similarity"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pairwise duplicate and k-mer similarity screen for phage cohorts.")
    parser.add_argument("--samplesheet", required=True, type=Path)
    parser.add_argument("--kmer-size", required=True, type=int)
    parser.add_argument("--duplicate-jaccard", required=True, type=float)
    parser.add_argument("--pairwise", required=True, type=Path)
    parser.add_argument("--duplicates", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    rows = load_samplesheet(args.samplesheet)
    genomes = []
    for row in rows:
        sequence = parse_fasta(Path(row["fasta"]))
        digest = hashlib.sha256(sequence.encode()).hexdigest()
        genomes.append(
            {
                "sample_id": row["sample_id"],
                "bases": len(sequence),
                "sha256": digest,
                "kmers": canonical_kmers(sequence, args.kmer_size),
            }
        )

    exact_duplicate_pairs = 0
    near_duplicate_pairs = 0
    pairwise_rows = []
    for left, right in combinations(genomes, 2):
        same_hash = left["sha256"] == right["sha256"]
        score = jaccard(left["kmers"], right["kmers"])
        label = interpretation(same_hash, score, args.duplicate_jaccard)
        if same_hash:
            exact_duplicate_pairs += 1
        if label in {"exact_duplicate", "near_duplicate"}:
            near_duplicate_pairs += 1
        pairwise_rows.append(
            {
                "sample_a": left["sample_id"],
                "sample_b": right["sample_id"],
                "bp_a": left["bases"],
                "bp_b": right["bases"],
                "same_sequence_sha256": "true" if same_hash else "false",
                f"kmer{args.kmer_size}_jaccard": f"{score:.6f}",
                "interpretation": label,
            }
        )

    pairwise_fields = [
        "sample_a",
        "sample_b",
        "bp_a",
        "bp_b",
        "same_sequence_sha256",
        f"kmer{args.kmer_size}_jaccard",
        "interpretation",
    ]
    with args.pairwise.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=pairwise_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairwise_rows)

    groups_by_hash = defaultdict(list)
    for genome in genomes:
        groups_by_hash[genome["sha256"]].append(genome["sample_id"])
    with args.duplicates.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["duplicate_group", "sample_ids", "group_type"])
        group_index = 1
        for members in groups_by_hash.values():
            if len(members) > 1:
                writer.writerow([f"DG{group_index:04d}", ",".join(sorted(members)), "exact_sequence_sha256"])
                group_index += 1

    with args.summary.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["genomes", len(genomes)])
        writer.writerow(["pairwise_comparisons", len(pairwise_rows)])
        writer.writerow(["exact_duplicate_pairs", exact_duplicate_pairs])
        writer.writerow(["duplicate_or_near_duplicate_pairs", near_duplicate_pairs])
        writer.writerow(["kmer_size", args.kmer_size])
        writer.writerow(["duplicate_jaccard_threshold", args.duplicate_jaccard])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

