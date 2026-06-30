#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Protein:
    seq_id: str
    genome_id: str
    protein_id: str
    sequence: str


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
                    yield header.split()[0], "".join(seq).rstrip("*")
                header = line[1:].strip()
                seq = []
            else:
                seq.append(line)
    if header is not None:
        yield header.split()[0], "".join(seq).rstrip("*")


def genome_id(seq_id: str) -> str:
    return seq_id.split("|", 1)[0]


def protein_id(seq_id: str) -> str:
    return seq_id.split("|", 1)[1] if "|" in seq_id else seq_id


def load_proteins(paths: list[Path]) -> tuple[list[Protein], list[str]]:
    proteins = []
    genome_order = []
    for path in paths:
        for header, sequence in parse_fasta(path):
            gid = genome_id(header)
            if gid not in genome_order:
                genome_order.append(gid)
            proteins.append(Protein(seq_id=header, genome_id=gid, protein_id=protein_id(header), sequence=sequence))
    return proteins, genome_order


def write_combined_fasta(proteins: list[Protein], path: Path) -> None:
    with path.open("w") as handle:
        for protein in proteins:
            handle.write(f">{protein.seq_id}\n")
            for i in range(0, len(protein.sequence), 80):
                handle.write(protein.sequence[i : i + 80] + "\n")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def run_blast(combined_fasta: Path, makeblastdb_bin: str, blastp_bin: str, hits_path: Path, threads: int) -> None:
    run([makeblastdb_bin, "-in", str(combined_fasta), "-dbtype", "prot", "-out", "pangenome_blastdb"])
    run(
        [
            blastp_bin,
            "-query",
            str(combined_fasta),
            "-db",
            "pangenome_blastdb",
            "-outfmt",
            "6 qseqid sseqid pident length qlen slen evalue bitscore",
            "-seg",
            "no",
            "-num_threads",
            str(max(1, threads)),
            "-out",
            str(hits_path),
        ]
    )


def filtered_hits(path: Path, min_identity: float, min_query_cov: float, min_subject_cov: float, max_evalue: float):
    hits = []
    with path.open() as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            qseqid, sseqid, pident, length, qlen, slen, evalue, bitscore = parts[:8]
            if qseqid == sseqid:
                continue
            pident = float(pident)
            length = int(length)
            qlen = int(qlen)
            slen = int(slen)
            evalue = float(evalue)
            bitscore = float(bitscore)
            qcov = 100.0 * length / qlen if qlen else 0.0
            scov = 100.0 * length / slen if slen else 0.0
            if pident < min_identity or qcov < min_query_cov or scov < min_subject_cov or evalue > max_evalue:
                continue
            hits.append({"qseqid": qseqid, "sseqid": sseqid, "pident": pident, "qcov": qcov, "scov": scov, "bitscore": bitscore})
    return hits


def choose_best_hits(hits, proteins_by_id):
    best = {}
    for hit in hits:
        qseqid = hit["qseqid"]
        sseqid = hit["sseqid"]
        if proteins_by_id[qseqid].genome_id == proteins_by_id[sseqid].genome_id:
            continue
        key = (qseqid, proteins_by_id[sseqid].genome_id)
        score = (hit["bitscore"], hit["pident"], min(hit["qcov"], hit["scov"]))
        if key not in best or score > best[key][0]:
            best[key] = (score, sseqid)
    return {key: value[1] for key, value in best.items()}


def build_components(nodes, edges):
    parent = {node: node for node in nodes}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left, right in edges:
        union(left, right)
    groups = defaultdict(list)
    for node in nodes:
        groups[find(node)].append(node)
    return list(groups.values())


def make_clusters(proteins, hits):
    proteins_by_id = {protein.seq_id: protein for protein in proteins}
    best = choose_best_hits(hits, proteins_by_id)
    edges = set()
    for (qseqid, subject_genome), sseqid in best.items():
        reciprocal = best.get((sseqid, proteins_by_id[qseqid].genome_id))
        if reciprocal == qseqid:
            edges.add(tuple(sorted((qseqid, sseqid))))
    return build_components(proteins_by_id.keys(), edges), proteins_by_id, edges


def classify_group(genome_count: int, total_genomes: int) -> str:
    if total_genomes and genome_count == total_genomes:
        return "core"
    if genome_count == 1:
        return "singleton"
    return "accessory"


def write_outputs(proteins, genome_order, components, edges, orthogroups_path, presence_path, metadata_path, summary_path, method):
    proteins_by_id = {protein.seq_id: protein for protein in proteins}
    protein_counts = Counter(protein.genome_id for protein in proteins)
    rows = []
    for idx, members in enumerate(sorted(components, key=lambda group: (-len(group), sorted(group)[0])), start=1):
        member_proteins = [proteins_by_id[member] for member in sorted(members)]
        genome_presence = Counter(protein.genome_id for protein in member_proteins)
        rows.append(
            {
                "orthogroup": f"OG{idx:05d}",
                "category": classify_group(len(genome_presence), len(genome_order)),
                "consensus_product": "hypothetical protein",
                "query_module": "",
                "n_genomes": len(genome_presence),
                "n_proteins": len(member_proteins),
                "members": member_proteins,
                "genome_presence": genome_presence,
            }
        )

    with orthogroups_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["orthogroup", "category", "consensus_product", "query_module", "n_genomes", "n_proteins", "members"])
        for row in rows:
            writer.writerow([
                row["orthogroup"], row["category"], row["consensus_product"], row["query_module"], row["n_genomes"], row["n_proteins"], ",".join(protein.seq_id for protein in row["members"])
            ])

    with presence_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["orthogroup", "category", "consensus_product", "query_module", "n_genomes"] + genome_order)
        for row in rows:
            by_genome = defaultdict(list)
            for protein in row["members"]:
                by_genome[protein.genome_id].append(protein.protein_id)
            writer.writerow([row["orthogroup"], row["category"], row["consensus_product"], row["query_module"], row["n_genomes"]] + [",".join(sorted(by_genome.get(genome, []))) for genome in genome_order])

    with metadata_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["genome_id", "genome_name", "protein_count"])
        for genome in genome_order:
            writer.writerow([genome, genome, protein_counts[genome]])

    counts = Counter(row["category"] for row in rows)
    with summary_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["method", method])
        writer.writerow(["genomes", len(genome_order)])
        writer.writerow(["proteins", len(proteins)])
        writer.writerow(["orthogroups", len(rows)])
        writer.writerow(["core_orthogroups", counts["core"]])
        writer.writerow(["accessory_orthogroups", counts["accessory"]])
        writer.writerow(["singleton_orthogroups", counts["singleton"]])
        writer.writerow(["rbh_edges", len(edges)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Native RBH-BLASTP pangenome inference for PhageFlow.")
    parser.add_argument("--faa-files", required=True, nargs="+", type=Path)
    parser.add_argument("--blastp-bin", required=True)
    parser.add_argument("--makeblastdb-bin", required=True)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--min-identity", required=True, type=float)
    parser.add_argument("--min-query-cov", required=True, type=float)
    parser.add_argument("--min-subject-cov", required=True, type=float)
    parser.add_argument("--max-evalue", required=True, type=float)
    parser.add_argument("--hits", required=True, type=Path)
    parser.add_argument("--orthogroups", required=True, type=Path)
    parser.add_argument("--presence-absence", required=True, type=Path)
    parser.add_argument("--genome-metadata", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    proteins, genome_order = load_proteins(args.faa_files)
    combined = Path("combined_proteins.faa")
    write_combined_fasta(proteins, combined)
    run_blast(combined, args.makeblastdb_bin, args.blastp_bin, args.hits, args.threads)
    hits = filtered_hits(args.hits, args.min_identity, args.min_query_cov, args.min_subject_cov, args.max_evalue)
    components, _, edges = make_clusters(proteins, hits)
    write_outputs(proteins, genome_order, components, edges, args.orthogroups, args.presence_absence, args.genome_metadata, args.summary, "rbh_blastp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
