#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

RC_TABLE = str.maketrans("ACGTRYKMSWBDHVNacgtrykmswbdhvn", "TGCAYRMKSWVHDBNtgcayrmkswbdhvn")


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


def n50(lengths: list[int]) -> int:
    if not lengths:
        return 0
    target = sum(lengths) / 2
    running = 0
    for length in sorted(lengths, reverse=True):
        running += length
        if running >= target:
            return length
    return 0


def reverse_complement(sequence: str) -> str:
    return sequence.translate(RC_TABLE)[::-1].upper()


def clean_sequence(sequence: str) -> str:
    return "".join(base for base in sequence.upper() if base in {"A", "C", "G", "T"})


def longest_terminal_match(left: str, right: str, min_bp: int = 20, max_bp: int = 5000) -> int:
    comparable = min(len(left), len(right))
    limit = min(comparable // 2, max_bp)
    for size in range(limit, min_bp - 1, -1):
        if left[:size] == right[-size:]:
            return size
    return 0


def termini_heuristics(contigs: list[str]) -> dict[str, str | int]:
    if len(contigs) != 1:
        return {
            "terminal_repeat_length_bp": 0,
            "inverted_terminal_repeat_length_bp": 0,
            "termini_heuristic": "not_evaluated_multi_contig",
        }
    sequence = clean_sequence(contigs[0])
    if len(sequence) < 40:
        return {
            "terminal_repeat_length_bp": 0,
            "inverted_terminal_repeat_length_bp": 0,
            "termini_heuristic": "sequence_too_short",
        }
    direct = longest_terminal_match(sequence, sequence)
    inverted = longest_terminal_match(sequence, reverse_complement(sequence))
    if direct:
        heuristic = "exact_terminal_repeat_detected"
    elif inverted:
        heuristic = "exact_inverted_terminal_repeat_detected"
    else:
        heuristic = "no_exact_terminal_repeat_detected"
    return {
        "terminal_repeat_length_bp": direct,
        "inverted_terminal_repeat_length_bp": inverted,
        "termini_heuristic": heuristic,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate FASTA assembly statistics.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--fasta", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    lengths = []
    gc = 0
    ambiguous = 0
    total = 0
    contig_sequences = []
    for _, sequence in parse_fasta(args.fasta):
        contig_sequences.append(sequence)
        lengths.append(len(sequence))
        total += len(sequence)
        gc += sequence.count("G") + sequence.count("C")
        ambiguous += sum(1 for base in sequence if base not in {"A", "C", "G", "T"})

    row = {
        "sample_id": args.sample_id,
        "contigs": len(lengths),
        "total_bp": total,
        "max_contig_bp": max(lengths) if lengths else 0,
        "n50_bp": n50(lengths),
        "gc_pct": f"{(100 * gc / total):.3f}" if total else "0.000",
        "ambiguous_pct": f"{(100 * ambiguous / total):.3f}" if total else "0.000",
        **termini_heuristics(contig_sequences),
    }

    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row.keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
