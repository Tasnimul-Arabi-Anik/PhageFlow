#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


STOPS = {"TAA", "TAG", "TGA"}
CODONS = [a + b + c for a in "TCAG" for b in "TCAG" for c in "TCAG"]


def parse_fasta(path: Path):
    header = None
    seq = []
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq).upper()
                header = line[1:].strip()
                seq = []
            else:
                seq.append(line)
    if header is not None:
        yield header, "".join(seq).upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate codon usage from coding nucleotide FASTA.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--ffn", required=True, type=Path)
    parser.add_argument("--counts", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    codon_counts = Counter()
    genes = 0
    coding_bp = 0
    gc = 0
    gc3 = 0
    codons_total = 0
    for _, sequence in parse_fasta(args.ffn):
        genes += 1
        usable_len = len(sequence) - (len(sequence) % 3)
        coding_bp += usable_len
        for i in range(0, usable_len, 3):
            codon = sequence[i : i + 3]
            if len(codon) != 3 or any(base not in "ACGT" for base in codon):
                continue
            if codon in STOPS:
                continue
            codon_counts[codon] += 1
            codons_total += 1
            gc += codon.count("G") + codon.count("C")
            if codon[2] in {"G", "C"}:
                gc3 += 1

    with args.counts.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["sample_id", "codon", "count", "per_thousand"])
        for codon in CODONS:
            count = codon_counts[codon]
            per_thousand = 1000 * count / codons_total if codons_total else 0
            writer.writerow([args.sample_id, codon, count, f"{per_thousand:.3f}"])

    top_codons = ",".join(codon for codon, _ in codon_counts.most_common(5))
    with args.summary.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["sample_id", "genes", "coding_nt_counted", "codons", "gc_pct", "gc3_pct", "top_codons"])
        writer.writerow(
            [
                args.sample_id,
                genes,
                coding_bp,
                codons_total,
                f"{(100 * gc / (codons_total * 3)):.3f}" if codons_total else "0.000",
                f"{(100 * gc3 / codons_total):.3f}" if codons_total else "0.000",
                top_codons,
            ]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

