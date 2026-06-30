#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def parse_fasta_headers(path: Path) -> list[str]:
    headers = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"): 
                headers.append(line[1:].strip().split()[0])
    return headers


def genome_id(protein_id: str) -> str:
    return protein_id.split("|", 1)[0]


def protein_name(protein_id: str) -> str:
    return protein_id.split("|", 1)[1] if "|" in protein_id else protein_id


def load_clusters(path: Path) -> dict[str, set[str]]:
    clusters = defaultdict(set)
    with path.open() as handle:
        for raw in handle:
            if not raw.strip():
                continue
            rep, member = raw.rstrip("\n").split("\t")[:2]
            clusters[rep].add(rep)
            clusters[rep].add(member)
    return clusters


def category(genomes_present: set[str], total_genomes: int) -> str:
    if total_genomes and len(genomes_present) == total_genomes:
        return "core"
    if len(genomes_present) == 1:
        return "singleton"
    return "accessory"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize MMseqs protein clusters as phage pangenome tables.")
    parser.add_argument("--clusters", required=True, type=Path)
    parser.add_argument("--faa-files", required=True, nargs="+", type=Path)
    parser.add_argument("--orthogroups", required=True, type=Path)
    parser.add_argument("--presence-absence", required=True, type=Path)
    parser.add_argument("--genome-metadata", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    proteins = []
    sample_order = []
    protein_counts = Counter()
    for faa in args.faa_files:
        for header in parse_fasta_headers(faa):
            proteins.append(header)
            gid = genome_id(header)
            protein_counts[gid] += 1
            if gid not in sample_order:
                sample_order.append(gid)

    clusters = load_clusters(args.clusters)
    clustered = set().union(*clusters.values()) if clusters else set()
    for protein in proteins:
        if protein not in clustered:
            clusters[protein].add(protein)

    rows = []
    for index, members in enumerate(sorted(clusters.values(), key=lambda m: (-len(m), sorted(m)[0])), start=1):
        members_sorted = sorted(members)
        genomes_present = {genome_id(member) for member in members_sorted}
        rows.append(
            {
                "orthogroup": f"OG{index:05d}",
                "category": category(genomes_present, len(sample_order)),
                "consensus_product": "hypothetical protein",
                "query_module": "",
                "n_genomes": len(genomes_present),
                "n_proteins": len(members_sorted),
                "members": members_sorted,
                "genomes_present": genomes_present,
            }
        )

    with args.orthogroups.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["orthogroup", "category", "consensus_product", "query_module", "n_genomes", "n_proteins", "members"])
        for row in rows:
            writer.writerow(
                [
                    row["orthogroup"],
                    row["category"],
                    row["consensus_product"],
                    row["query_module"],
                    row["n_genomes"],
                    row["n_proteins"],
                    ",".join(row["members"]),
                ]
            )

    with args.presence_absence.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["orthogroup", "category", "consensus_product", "query_module", "n_genomes"] + sample_order)
        for row in rows:
            by_genome = defaultdict(list)
            for member in row["members"]:
                by_genome[genome_id(member)].append(protein_name(member))
            writer.writerow(
                [row["orthogroup"], row["category"], row["consensus_product"], row["query_module"], row["n_genomes"]]
                + [",".join(sorted(by_genome.get(sample, []))) for sample in sample_order]
            )

    with args.genome_metadata.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["genome_id", "genome_name", "protein_count"])
        for sample in sample_order:
            writer.writerow([sample, sample, protein_counts[sample]])

    counts = Counter(row["category"] for row in rows)
    with args.summary.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["method", "mmseqs"])
        writer.writerow(["genomes", len(sample_order)])
        writer.writerow(["proteins", len(proteins)])
        writer.writerow(["orthogroups", len(rows)])
        writer.writerow(["core_orthogroups", counts["core"]])
        writer.writerow(["accessory_orthogroups", counts["accessory"]])
        writer.writerow(["singleton_orthogroups", counts["singleton"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
