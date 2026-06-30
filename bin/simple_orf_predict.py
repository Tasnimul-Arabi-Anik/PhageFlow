#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path


STARTS = {"ATG", "GTG", "TTG"}
STOPS = {"TAA", "TAG", "TGA"}
RC_TABLE = str.maketrans("ACGTRYKMSWBDHVNacgtrykmswbdhvn", "TGCAYRMKSWVHDBNtgcayrmkswvhdbn")
GENETIC_CODE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


@dataclass
class Orf:
    contig: str
    start: int
    end: int
    strand: str
    nt: str


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
                    yield header.split()[0], "".join(seq).upper()
                header = line[1:].strip()
                seq = []
            else:
                seq.append(line)
    if header is not None:
        yield header.split()[0], "".join(seq).upper()


def reverse_complement(sequence: str) -> str:
    return sequence.translate(RC_TABLE)[::-1].upper()


def translate(nt: str) -> str:
    aa = []
    for i in range(0, len(nt) - 2, 3):
        codon = nt[i : i + 3]
        aa.append(GENETIC_CODE.get(codon, "X"))
    return "".join(aa).rstrip("*")


def find_orfs_on_strand(contig: str, sequence: str, strand: str, min_nt: int) -> list[Orf]:
    search = sequence if strand == "+" else reverse_complement(sequence)
    seq_len = len(sequence)
    orfs = []
    for frame in range(3):
        i = frame
        while i <= len(search) - 3:
            codon = search[i : i + 3]
            if codon not in STARTS:
                i += 3
                continue
            j = i + 3
            found_stop = False
            while j <= len(search) - 3:
                if search[j : j + 3] in STOPS:
                    nt = search[i : j + 3]
                    if len(nt) >= min_nt:
                        if strand == "+":
                            start, end = i + 1, j + 3
                        else:
                            start, end = seq_len - (j + 3) + 1, seq_len - i
                        orfs.append(Orf(contig=contig, start=start, end=end, strand=strand, nt=nt))
                    i = j + 3
                    found_stop = True
                    break
                j += 3
            if not found_stop:
                i += 3
    return orfs


def wrap(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[i : i + width] for i in range(0, len(sequence), width))


def covered_bases(orfs: list[Orf]) -> int:
    intervals_by_contig = {}
    for orf in orfs:
        intervals_by_contig.setdefault(orf.contig, []).append((orf.start, orf.end))

    total = 0
    for intervals in intervals_by_contig.values():
        merged = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1] + 1:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        total += sum(end - start + 1 for start, end in merged)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Small dependency-free ORF predictor for PhageFlow smoke tests.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--fasta", required=True, type=Path)
    parser.add_argument("--min-aa", required=True, type=int)
    parser.add_argument("--faa", required=True, type=Path)
    parser.add_argument("--ffn", required=True, type=Path)
    parser.add_argument("--gff", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    min_nt = args.min_aa * 3
    all_orfs = []
    genome_bp = 0
    for contig, sequence in parse_fasta(args.fasta):
        genome_bp += len(sequence)
        all_orfs.extend(find_orfs_on_strand(contig, sequence, "+", min_nt))
        all_orfs.extend(find_orfs_on_strand(contig, sequence, "-", min_nt))
    all_orfs.sort(key=lambda item: (item.contig, item.start, item.end, item.strand))

    with args.faa.open("w") as faa, args.ffn.open("w") as ffn, args.gff.open("w") as gff:
        gff.write("##gff-version 3\n")
        for index, orf in enumerate(all_orfs, start=1):
            gene_id = f"{args.sample_id}_orf{index:05d}"
            aa = translate(orf.nt)
            faa.write(f">{args.sample_id}|{gene_id} length_aa={len(aa)}\n{wrap(aa)}\n")
            ffn.write(f">{args.sample_id}|{gene_id} length_nt={len(orf.nt)}\n{wrap(orf.nt)}\n")
            attributes = f"ID={gene_id};Name={gene_id};product=hypothetical protein"
            gff.write(
                f"{orf.contig}\tPhageFlow\tCDS\t{orf.start}\t{orf.end}\t.\t{orf.strand}\t0\t{attributes}\n"
            )

    coding_bp = covered_bases(all_orfs)
    plus_orfs = sum(1 for orf in all_orfs if orf.strand == "+")
    minus_orfs = sum(1 for orf in all_orfs if orf.strand == "-")
    aa_lengths = [max((len(orf.nt) // 3) - 1, 0) for orf in all_orfs]
    mean_aa = statistics.mean(aa_lengths) if aa_lengths else 0
    median_aa = statistics.median(aa_lengths) if aa_lengths else 0
    with args.summary.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "sample_id",
                "orfs",
                "plus_strand_orfs",
                "minus_strand_orfs",
                "coding_bp",
                "genome_bp",
                "coding_density_pct",
                "orfs_per_kb",
                "mean_orf_aa",
                "median_orf_aa",
                "longest_orf_aa",
                "min_orf_aa",
            ]
        )
        writer.writerow(
            [
                args.sample_id,
                len(all_orfs),
                plus_orfs,
                minus_orfs,
                coding_bp,
                genome_bp,
                f"{(100 * coding_bp / genome_bp):.3f}" if genome_bp else "0.000",
                f"{(1000 * len(all_orfs) / genome_bp):.3f}" if genome_bp else "0.000",
                f"{mean_aa:.3f}",
                f"{median_aa:.3f}",
                max(aa_lengths) if aa_lengths else 0,
                args.min_aa,
            ]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
