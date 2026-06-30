#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

BASES = "ACGT"
STARTS = {"ATG", "GTG", "TTG"}
STOPS = {"TAA", "TAG", "TGA"}
CODONS = [a + b + c for a in "TCAG" for b in "TCAG" for c in "TCAG"]
SENSE_CODONS = [codon for codon in CODONS if codon not in STOPS]
RC_TABLE = str.maketrans("ACGTRYKMSWBDHVNacgtrykmswbdhvn", "TGCAYRMKSWVHDBNtgcayrmkswvhdbn")
GENETIC_CODE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L", "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*", "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L", "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q", "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M", "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K", "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V", "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E", "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}
CODONS_BY_AA: dict[str, list[str]] = {}
for codon, aa in GENETIC_CODE.items():
    if aa != "*":
        CODONS_BY_AA.setdefault(aa, []).append(codon)


def truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "y", "on"}


def parse_samplesheet(path: Path, required_id: str) -> list[dict[str, str]]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"Empty samplesheet: {path}")
        rows = []
        for row in reader:
            if required_id not in row and required_id == "host_id" and "sample_id" in row:
                row["host_id"] = row["sample_id"]
            if required_id not in row:
                raise ValueError(f"Missing required column '{required_id}' in {path}")
            if "fasta" not in row:
                raise ValueError(f"Missing required column 'fasta' in {path}")
            cleaned = {key: (value or "").strip() for key, value in row.items()}
            for column in ["fasta", "cds_ffn", "spacers_fasta"]:
                value = cleaned.get(column, "")
                if value:
                    candidate = Path(value)
                    if not candidate.is_absolute():
                        candidate = path.parent / candidate
                    cleaned[column] = str(candidate.resolve())
            rows.append(cleaned)
        return rows


def parse_fasta(path: Path):
    header = None
    sequence: list[str] = []
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(sequence).upper()
                header = line[1:].strip()
                sequence = []
            else:
                sequence.append(line)
    if header is not None:
        yield header, "".join(sequence).upper()


def read_sequence(path: Path) -> str:
    return "".join(seq for _, seq in parse_fasta(path))


def clean_sequence(sequence: str) -> str:
    return "".join(base for base in sequence.upper() if base in BASES)


def reverse_complement(sequence: str) -> str:
    return sequence.translate(RC_TABLE)[::-1].upper()


def gc_pct(sequence: str) -> float:
    clean = clean_sequence(sequence)
    return 100 * sum(1 for base in clean if base in {"G", "C"}) / len(clean) if clean else 0.0


def kmer_profile(sequence: str, k: int = 4) -> Counter[str]:
    clean = clean_sequence(sequence)
    counts: Counter[str] = Counter()
    for index in range(0, len(clean) - k + 1):
        counts[clean[index : index + k]] += 1
    return counts


def cosine_values(left: dict[str, float] | Counter[str], right: dict[str, float] | Counter[str], keys: list[str]) -> float:
    dot = sum(float(left.get(key, 0)) * float(right.get(key, 0)) for key in keys)
    left_norm = math.sqrt(sum(float(left.get(key, 0)) ** 2 for key in keys))
    right_norm = math.sqrt(sum(float(right.get(key, 0)) ** 2 for key in keys))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def cosine(left: Counter[str], right: Counter[str]) -> float:
    keys = sorted(set(left) | set(right))
    return cosine_values(left, right, keys) if keys else 0.0


def fallback_frame(sequence: str, min_nt: int) -> list[str]:
    clean = clean_sequence(sequence)
    usable = len(clean) - (len(clean) % 3)
    return [clean[:usable]] if usable >= min_nt else []


def find_orfs(sequence: str, min_nt: int) -> list[str]:
    coding: list[str] = []
    for strand_sequence in [clean_sequence(sequence), reverse_complement(clean_sequence(sequence))]:
        for frame in range(3):
            index = frame
            while index <= len(strand_sequence) - 3:
                if strand_sequence[index : index + 3] not in STARTS:
                    index += 3
                    continue
                stop_index = index + 3
                while stop_index <= len(strand_sequence) - 3:
                    if strand_sequence[stop_index : stop_index + 3] in STOPS:
                        nt = strand_sequence[index : stop_index + 3]
                        if len(nt) >= min_nt:
                            coding.append(nt)
                        index = stop_index + 3
                        break
                    stop_index += 3
                else:
                    index += 3
    return coding


def load_cds_ffn(path: Path) -> list[str]:
    coding = []
    for _, sequence in parse_fasta(path):
        clean = clean_sequence(sequence)
        usable = len(clean) - (len(clean) % 3)
        if usable >= 3:
            coding.append(clean[:usable])
    return coding


def prodigal_cds(fasta: Path, prodigal_bin: str, sample_id: str, workdir: Path) -> tuple[list[str], str]:
    executable = shutil.which(prodigal_bin)
    if not executable:
        return [], "prodigal_not_found"
    out_ffn = workdir / f"{sample_id}.prodigal.ffn"
    completed = subprocess.run([executable, "-i", str(fasta), "-d", str(out_ffn), "-p", "single", "-q"], check=False, text=True, capture_output=True)
    if completed.returncode != 0 or not out_ffn.exists() or out_ffn.stat().st_size == 0:
        return [], "prodigal_failed"
    coding = load_cds_ffn(out_ffn)
    return coding, "prodigal" if coding else "prodigal_empty"


def coding_for_genome(row: dict[str, str], id_field: str, min_aa: int, use_prodigal: bool, prodigal_bin: str, workdir: Path) -> tuple[list[str], str]:
    if row.get("cds_ffn") and Path(row["cds_ffn"]).exists():
        coding = load_cds_ffn(Path(row["cds_ffn"]))
        if coding:
            return coding, "provided_cds_ffn"
    if use_prodigal:
        coding, source = prodigal_cds(Path(row["fasta"]), prodigal_bin, row.get(id_field, "genome"), workdir)
        if coding:
            return coding, source
    sequence = read_sequence(Path(row["fasta"]))
    min_nt = min_aa * 3
    coding = find_orfs(sequence, min_nt)
    if coding:
        return coding, "internal_orf"
    return fallback_frame(sequence, min_nt), "whole_sequence_frame_fallback"


def codon_counts(coding: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for sequence in coding:
        usable = len(sequence) - (len(sequence) % 3)
        for index in range(0, usable, 3):
            codon = sequence[index : index + 3]
            if codon in SENSE_CODONS:
                counts[codon] += 1
    return counts


def gc3(counts: Counter[str]) -> float:
    total = sum(counts.values())
    return 100 * sum(value for codon, value in counts.items() if codon[2] in {"G", "C"}) / total if total else 0.0


def rscu(counts: Counter[str]) -> dict[str, float]:
    values = {}
    for codons in CODONS_BY_AA.values():
        total = sum(counts.get(codon, 0) for codon in codons)
        expected = total / len(codons) if codons else 0
        for codon in codons:
            values[codon] = counts.get(codon, 0) / expected if expected else 0.0
    return values


def cai_like(phage_counts: Counter[str], host_counts: Counter[str]) -> float:
    weighted_logs = []
    for codons in CODONS_BY_AA.values():
        max_count = max(host_counts.get(codon, 0) for codon in codons)
        for codon in codons:
            count = phage_counts.get(codon, 0)
            if count:
                weight = (host_counts.get(codon, 0) + 0.5) / (max_count + 0.5) if max_count else 0.5
                weighted_logs.extend([math.log(max(weight, 0.01))] * count)
    return math.exp(sum(weighted_logs) / len(weighted_logs)) if weighted_logs else 0.0


def preferred_match_pct(phage_counts: Counter[str], host_counts: Counter[str]) -> float:
    total = sum(phage_counts.values())
    if not total:
        return 0.0
    preferred = set()
    for codons in CODONS_BY_AA.values():
        max_count = max(host_counts.get(codon, 0) for codon in codons)
        preferred.update(codon for codon in codons if max_count and host_counts.get(codon, 0) == max_count)
    return 100 * sum(count for codon, count in phage_counts.items() if codon in preferred) / total if preferred else 0.0


def load_spacers(paths: list[tuple[str, Path]]) -> list[dict[str, str]]:
    spacers = []
    for source, path in paths:
        if not path.exists():
            continue
        for header, sequence in parse_fasta(path):
            clean = clean_sequence(sequence)
            if clean:
                spacers.append({"spacer_id": header.split()[0], "source": source, "sequence": clean})
    return spacers


def best_window_match(query: str, target: str, min_coverage: float) -> tuple[int, int, str, int, int, int]:
    min_len = max(7, math.ceil(len(query) * min_coverage / 100))
    for length in range(len(query), min_len - 1, -1):
        for strand, oriented_query in [("+", query), ("-", reverse_complement(query))]:
            for q_start in range(0, len(oriented_query) - length + 1):
                segment = oriented_query[q_start : q_start + length]
                target_start = target.find(segment)
                if target_start >= 0:
                    return (target_start + 1, target_start + length, strand, length, length, 0)
    return (-1, -1, "+", 0, 0, len(query))


def spacer_matches(phage: dict[str, str], host_id: str, spacers: list[dict[str, str]], min_identity: float, min_coverage: float) -> list[dict[str, str]]:
    if not spacers:
        return []
    contigs = [(header.split()[0], clean_sequence(sequence)) for header, sequence in parse_fasta(Path(phage["fasta"]))]
    rows = []
    for spacer in spacers:
        query = spacer["sequence"]
        for contig, target in contigs:
            if not target:
                continue
            start, end, strand, matches, aligned_len, mismatches = best_window_match(query, target, min_coverage)
            if aligned_len <= 0:
                continue
            identity = 100 * matches / aligned_len
            coverage = 100 * aligned_len / len(query)
            if identity >= min_identity and coverage >= min_coverage:
                rows.append(
                    {
                        "sample_id": phage["sample_id"], "host_id": host_id, "spacer_id": spacer["spacer_id"],
                        "spacer_source": spacer["source"], "target_contig": contig, "match_start": str(start),
                        "match_end": str(end), "strand": strand, "spacer_length": str(len(query)),
                        "aligned_length": str(aligned_len), "identity_pct": f"{identity:.3f}",
                        "coverage_pct": f"{coverage:.3f}", "mismatches": str(mismatches),
                    }
                )
    return rows


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def write_key_values(path: Path, values: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in values.items():
            writer.writerow([key, value])


def interpretation(codon_distance: float, rscu_distance: float, crispr_hits: int) -> str:
    if crispr_hits:
        return "direct_crispr_match_plus_composition"
    if codon_distance <= 0.10 and rscu_distance <= 0.20:
        return "high_compositional_similarity"
    if codon_distance <= 0.20:
        return "moderate_compositional_similarity"
    return "weak_compositional_similarity"


def main() -> int:
    parser = argparse.ArgumentParser(description="Host-context comparison with codon adaptation and optional CRISPR spacer matching.")
    parser.add_argument("--phage-samplesheet", required=True, type=Path)
    parser.add_argument("--host-samplesheet", required=True, type=Path)
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--host-codon-adaptation", required=True, type=Path)
    parser.add_argument("--host-codon-rscu", required=True, type=Path)
    parser.add_argument("--crispr-matches", required=True, type=Path)
    parser.add_argument("--crispr-summary", required=True, type=Path)
    parser.add_argument("--run-crispr-spacer-match", default="false")
    parser.add_argument("--crispr-spacers", default="")
    parser.add_argument("--crispr-min-identity", type=float, default=95.0)
    parser.add_argument("--crispr-min-coverage", type=float, default=80.0)
    parser.add_argument("--host-min-orf-aa", type=int, default=60)
    parser.add_argument("--host-use-prodigal", default="true")
    parser.add_argument("--prodigal-bin", default="prodigal")
    args = parser.parse_args()

    phages = parse_samplesheet(args.phage_samplesheet, "sample_id")
    hosts = parse_samplesheet(args.host_samplesheet, "host_id")
    host_by_id = {row["host_id"]: row for row in hosts}
    run_crispr = truthy(args.run_crispr_spacer_match)
    global_spacers = Path(args.crispr_spacers).resolve() if args.crispr_spacers and args.crispr_spacers not in {"null", "None"} else None

    with tempfile.TemporaryDirectory(prefix="phageflow_host_") as tmp:
        workdir = Path(tmp)
        host_cache = {}
        for host_id, row in host_by_id.items():
            host_sequence = read_sequence(Path(row["fasta"]))
            host_coding, source = coding_for_genome(row, "host_id", args.host_min_orf_aa, truthy(args.host_use_prodigal), args.prodigal_bin, workdir)
            host_cache[host_id] = {
                "sequence": host_sequence,
                "gc_pct": gc_pct(host_sequence),
                "tetra": kmer_profile(host_sequence),
                "taxon": row.get("taxon", ""),
                "accession": row.get("accession", ""),
                "codons": codon_counts(host_coding),
                "cds_source": source,
                "spacers_fasta": row.get("spacers_fasta", ""),
            }

        host_rows: list[dict[str, str]] = []
        adaptation_rows: list[dict[str, str]] = []
        rscu_rows: list[dict[str, str]] = []
        crispr_rows: list[dict[str, str]] = []

        for phage in phages:
            sample_id = phage["sample_id"]
            host_id = phage.get("host_id", "")
            phage_sequence = read_sequence(Path(phage["fasta"]))
            base_row = {
                "sample_id": sample_id, "host_id": host_id, "host_found": "false", "phage_gc_pct": "",
                "host_gc_pct": "", "delta_gc_pct": "", "tetranucleotide_cosine": "", "host_taxon": "",
                "host_accession": "", "phage_cds_source": "", "host_cds_source": "", "phage_codons": "",
                "host_codons": "", "codon_cosine": "", "codon_distance": "", "rscu_cosine": "",
                "rscu_distance": "", "cai_like": "", "preferred_codon_match_pct": "", "crispr_spacer_hits": "0",
                "best_crispr_identity_pct": "",
            }
            if not host_id or host_id not in host_cache:
                host_rows.append(base_row)
                continue

            host = host_cache[host_id]
            phage_coding, phage_cds_source = coding_for_genome({**phage, "cds_ffn": phage.get("cds_ffn", "")}, "sample_id", args.host_min_orf_aa, False, args.prodigal_bin, workdir)
            phage_counts = codon_counts(phage_coding)
            host_counts = host["codons"]
            phage_rscu = rscu(phage_counts)
            host_rscu = rscu(host_counts)
            codon_cosine = cosine_values(phage_counts, host_counts, SENSE_CODONS)
            rscu_cosine = cosine_values(phage_rscu, host_rscu, SENSE_CODONS)

            spacer_paths = []
            if global_spacers:
                spacer_paths.append(("global", global_spacers))
            if host["spacers_fasta"]:
                spacer_paths.append((host_id, Path(host["spacers_fasta"])))
            sample_crispr_rows = spacer_matches(phage, host_id, load_spacers(spacer_paths), args.crispr_min_identity, args.crispr_min_coverage) if run_crispr else []
            crispr_rows.extend(sample_crispr_rows)
            best_identity = max([float(row["identity_pct"]) for row in sample_crispr_rows], default=0.0)
            codon_distance = 1 - codon_cosine
            rscu_distance = 1 - rscu_cosine

            row = {
                "sample_id": sample_id, "host_id": host_id, "host_found": "true", "phage_gc_pct": f"{gc_pct(phage_sequence):.3f}",
                "host_gc_pct": f"{host['gc_pct']:.3f}", "delta_gc_pct": f"{abs(gc_pct(phage_sequence) - host['gc_pct']):.3f}",
                "tetranucleotide_cosine": f"{cosine(kmer_profile(phage_sequence), host['tetra']):.6f}",
                "host_taxon": host["taxon"], "host_accession": host["accession"], "phage_cds_source": phage_cds_source,
                "host_cds_source": host["cds_source"], "phage_codons": str(sum(phage_counts.values())),
                "host_codons": str(sum(host_counts.values())), "phage_gc3_pct": f"{gc3(phage_counts):.3f}",
                "host_gc3_pct": f"{gc3(host_counts):.3f}", "delta_gc3_pct": f"{abs(gc3(phage_counts) - gc3(host_counts)):.3f}",
                "codon_cosine": f"{codon_cosine:.6f}", "codon_distance": f"{codon_distance:.6f}",
                "rscu_cosine": f"{rscu_cosine:.6f}", "rscu_distance": f"{rscu_distance:.6f}",
                "cai_like": f"{cai_like(phage_counts, host_counts):.6f}",
                "preferred_codon_match_pct": f"{preferred_match_pct(phage_counts, host_counts):.3f}",
                "crispr_spacer_hits": str(len(sample_crispr_rows)),
                "best_crispr_identity_pct": f"{best_identity:.3f}" if sample_crispr_rows else "",
                "interpretation": interpretation(codon_distance, rscu_distance, len(sample_crispr_rows)),
            }
            host_rows.append({**base_row, **row})
            adaptation_rows.append(row)
            for codon in SENSE_CODONS:
                rscu_rows.append(
                    {
                        "sample_id": sample_id, "host_id": host_id, "codon": codon, "amino_acid": GENETIC_CODE[codon],
                        "phage_count": str(phage_counts.get(codon, 0)), "host_count": str(host_counts.get(codon, 0)),
                        "phage_rscu": f"{phage_rscu.get(codon, 0.0):.6f}", "host_rscu": f"{host_rscu.get(codon, 0.0):.6f}",
                        "rscu_delta": f"{abs(phage_rscu.get(codon, 0.0) - host_rscu.get(codon, 0.0)):.6f}",
                    }
                )

    host_fields = ["sample_id", "host_id", "host_found", "phage_gc_pct", "host_gc_pct", "delta_gc_pct", "tetranucleotide_cosine", "host_taxon", "host_accession", "phage_cds_source", "host_cds_source", "phage_codons", "host_codons", "codon_cosine", "codon_distance", "rscu_cosine", "rscu_distance", "cai_like", "preferred_codon_match_pct", "crispr_spacer_hits", "best_crispr_identity_pct"]
    adaptation_fields = ["sample_id", "host_id", "host_found", "phage_cds_source", "host_cds_source", "phage_codons", "host_codons", "phage_gc3_pct", "host_gc3_pct", "delta_gc3_pct", "codon_cosine", "codon_distance", "rscu_cosine", "rscu_distance", "cai_like", "preferred_codon_match_pct", "crispr_spacer_hits", "best_crispr_identity_pct", "interpretation"]
    rscu_fields = ["sample_id", "host_id", "codon", "amino_acid", "phage_count", "host_count", "phage_rscu", "host_rscu", "rscu_delta"]
    crispr_fields = ["sample_id", "host_id", "spacer_id", "spacer_source", "target_contig", "match_start", "match_end", "strand", "spacer_length", "aligned_length", "identity_pct", "coverage_pct", "mismatches"]
    write_rows(args.table, host_rows, host_fields)
    write_rows(args.host_codon_adaptation, adaptation_rows, adaptation_fields)
    write_rows(args.host_codon_rscu, rscu_rows, rscu_fields)
    write_rows(args.crispr_matches, crispr_rows, crispr_fields)

    linked = sum(1 for row in host_rows if row.get("host_found") == "true")
    write_key_values(args.crispr_summary, {"status": "completed" if run_crispr else "disabled", "phages_evaluated": str(len(phages)), "host_links_evaluated": str(linked), "spacer_matches": str(len(crispr_rows)), "min_identity_pct": f"{args.crispr_min_identity:.3f}", "min_coverage_pct": f"{args.crispr_min_coverage:.3f}", "global_spacers": str(global_spacers or "")})
    with args.summary.open("w") as handle:
        handle.write("# Host Context Summary\n\n")
        handle.write(f"- Phages in samplesheet: {len(phages)}\n")
        handle.write(f"- Host genomes in samplesheet: {len(hosts)}\n")
        handle.write(f"- Phage-host links evaluated: {linked}\n")
        handle.write(f"- Host codon-adaptation rows: {len(adaptation_rows)}\n")
        handle.write(f"- CRISPR spacer matching: {'enabled' if run_crispr else 'disabled'}\n")
        handle.write(f"- CRISPR spacer/protospacer matches: {len(crispr_rows)}\n\n")
        handle.write("Host-context metrics are supporting in-silico evidence, not proof of host range or infectivity.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
