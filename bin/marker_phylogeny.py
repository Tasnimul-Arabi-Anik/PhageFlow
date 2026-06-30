#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import statistics
import subprocess
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


MARKER_ALIASES = {
    "terminase_large": ["terminase_large", "terminase large", "large terminase", "terminase large subunit", "terl", "large terminase subunit"],
    "portal": ["portal", "portal protein"],
    "major_capsid": ["major_capsid", "major capsid", "major head", "head protein", "capsid protein", "major capsid protein"],
}

PRESENCE_FIELDS = ["sample_id", "marker_kind", "status", "gene_id", "length_aa", "source", "candidate_count", "selected_reason"]
TOPOLOGY_FIELDS = ["marker_kind", "status", "shared_pairs", "pearson_correlation", "tree_engine", "note"]
PROVENANCE_FIELDS = [
    "marker_kind",
    "records_selected",
    "marker_min_genomes",
    "alignment_status",
    "tree_status",
    "tree_engine_requested",
    "tree_engine_used",
    "bootstrap",
    "marker_fasta",
    "alignment_file",
    "tree_file",
    "note",
]


@dataclass
class ProteinRecord:
    sample_id: str
    marker_kind: str
    gene_id: str
    sequence: str
    source: str
    description: str


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
                    yield header, "".join(seq).replace("*", "").upper()
                header = line[1:].strip()
                seq = []
            else:
                seq.append(line)
    if header is not None:
        yield header, "".join(seq).replace("*", "").upper()


def wrap(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[i : i + width] for i in range(0, len(sequence), width))


def write_fasta(records: list[ProteinRecord], path: Path) -> None:
    with path.open("w") as handle:
        for record in records:
            header = f"{record.sample_id}|{record.marker_kind}|{record.gene_id} source={record.source}"
            handle.write(f">{header}\n{wrap(record.sequence)}\n")


def load_samples(samplesheet: Path) -> list[str]:
    with samplesheet.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [row["sample_id"].strip() for row in reader if row.get("sample_id", "").strip()]


def normalize_kind(value: str, marker_kinds: list[str]) -> str | None:
    value_norm = re.sub(r"[_\-]+", " ", value.lower()).strip()
    compact = value_norm.replace(" ", "_")
    for kind in marker_kinds:
        if compact == kind:
            return kind
        for alias in MARKER_ALIASES.get(kind, []):
            alias_norm = re.sub(r"[_\-]+", " ", alias.lower()).strip()
            if value_norm == alias_norm or alias_norm in value_norm:
                return kind
    return None


def infer_sample_id(header: str, sample_ids: set[str]) -> str | None:
    token = header.split()[0]
    parts = token.split("|")
    if parts and parts[0] in sample_ids:
        return parts[0]
    for sample_id in sorted(sample_ids, key=len, reverse=True):
        if token == sample_id or token.startswith(sample_id + "|") or token.startswith(sample_id + "_") or f"|{sample_id}|" in header:
            return sample_id
    return None


def parse_record(header: str, sequence: str, sample_ids: set[str], marker_kinds: list[str], source: str) -> ProteinRecord | None:
    if not sequence:
        return None
    token = header.split()[0]
    parts = token.split("|")
    sample_id = infer_sample_id(header, sample_ids)
    marker_kind = None
    gene_id = token
    if len(parts) >= 3 and parts[0] in sample_ids:
        sample_id = parts[0]
        marker_kind = normalize_kind(parts[1], marker_kinds)
        gene_id = parts[2]
    if marker_kind is None:
        marker_kind = normalize_kind(header, marker_kinds)
    if sample_id is None or marker_kind is None:
        return None
    return ProteinRecord(sample_id=sample_id, marker_kind=marker_kind, gene_id=gene_id, sequence=sequence, source=source, description=header)


def collect_candidates(samples: list[str], marker_faa: Path | None, faa_files: list[Path], marker_kinds: list[str], marker_source: str) -> dict[tuple[str, str], list[ProteinRecord]]:
    sample_ids = set(samples)
    candidates: dict[tuple[str, str], list[ProteinRecord]] = {}
    sources: list[tuple[Path, str]] = []
    if marker_faa and marker_faa.exists() and marker_source in {"auto", "marker_faa", "manual"}:
        sources.append((marker_faa, "marker_faa"))
    if marker_source in {"auto", "faa_headers", "annotation"}:
        sources.extend((path, "faa_headers") for path in faa_files if path.exists())
    seen = set()
    for path, source in sources:
        for header, sequence in parse_fasta(path):
            record = parse_record(header, sequence, sample_ids, marker_kinds, source)
            if record is None:
                continue
            key = (record.sample_id, record.marker_kind, record.gene_id, record.sequence)
            if key in seen:
                continue
            seen.add(key)
            candidates.setdefault((record.sample_id, record.marker_kind), []).append(record)
    return candidates


def select_markers(samples: list[str], marker_kinds: list[str], candidates: dict[tuple[str, str], list[ProteinRecord]]) -> tuple[list[dict[str, str]], dict[str, list[ProteinRecord]]]:
    presence_rows: list[dict[str, str]] = []
    selected_by_kind: dict[str, list[ProteinRecord]] = {kind: [] for kind in marker_kinds}
    for sample_id in samples:
        for kind in marker_kinds:
            items = candidates.get((sample_id, kind), [])
            if not items:
                presence_rows.append({"sample_id": sample_id, "marker_kind": kind, "status": "missing", "gene_id": "", "length_aa": "0", "source": "", "candidate_count": "0", "selected_reason": "no_candidate"})
                continue
            selected = max(items, key=lambda item: len(item.sequence))
            selected_by_kind[kind].append(selected)
            presence_rows.append({"sample_id": sample_id, "marker_kind": kind, "status": "selected", "gene_id": selected.gene_id, "length_aa": str(len(selected.sequence)), "source": selected.source, "candidate_count": str(len(items)), "selected_reason": "longest_candidate"})
    return presence_rows, selected_by_kind


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_key_value(path: Path, values: dict[str, str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        for key, value in values.items():
            writer.writerow([key, value])


def run_command(command: list[str], stdout_path: Path | None = None) -> tuple[int, str]:
    if stdout_path:
        with stdout_path.open("w") as out:
            completed = subprocess.run(command, text=True, stdout=out, stderr=subprocess.PIPE, check=False)
    else:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    stderr = completed.stderr or ""
    return completed.returncode, stderr


def parse_alignment(path: Path) -> dict[str, str]:
    records = {}
    for header, sequence in parse_fasta(path):
        sample_id = header.split()[0].split("|")[0]
        records[sample_id] = sequence
    return records


def align_marker(input_faa: Path, output_faa: Path, mafft_bin: str, trimal_bin: str, workdir: Path) -> tuple[Path | None, str]:
    mafft = shutil.which(mafft_bin)
    if mafft:
        raw_alignment = workdir / (input_faa.stem + ".mafft.faa")
        code, stderr = run_command([mafft, "--auto", str(input_faa)], stdout_path=raw_alignment)
        if code != 0:
            return None, f"mafft_failed:{stderr.strip()[:160]}"
        trimal = shutil.which(trimal_bin)
        if trimal:
            code, stderr = run_command([trimal, "-automated1", "-in", str(raw_alignment), "-out", str(output_faa)])
            if code == 0 and output_faa.exists() and output_faa.stat().st_size > 0:
                return output_faa, "mafft_trimal"
        shutil.copyfile(raw_alignment, output_faa)
        return output_faa, "mafft_untrimmed"
    lengths = {len(seq) for _, seq in parse_fasta(input_faa)}
    if len(lengths) == 1:
        shutil.copyfile(input_faa, output_faa)
        return output_faa, "unaligned_equal_length"
    return None, "skipped_no_mafft_for_unequal_lengths"


def p_distance(left: str, right: str) -> float:
    comparable = 0
    mismatches = 0
    for a, b in zip(left, right):
        if a == "-" or b == "-" or a == "X" or b == "X":
            continue
        comparable += 1
        if a != b:
            mismatches += 1
    return mismatches / comparable if comparable else 1.0


def format_length(value: float) -> str:
    return f"{max(value, 0.0):.6f}"


def build_upgma_tree(alignment: dict[str, str]) -> tuple[str, dict[tuple[str, str], float]]:
    names = sorted(alignment)
    if len(names) == 1:
        return f"{names[0]}:0.000000;", {}
    base_dist = {}
    for a, b in combinations(names, 2):
        base_dist[frozenset([a, b])] = p_distance(alignment[a], alignment[b])
    clusters = {name: {"members": [name], "height": 0.0, "newick": name} for name in names}
    next_id = 1
    pair_tree_dist: dict[tuple[str, str], float] = {}
    while len(clusters) > 1:
        best_pair = None
        best_dist = None
        ids = sorted(clusters)
        for a, b in combinations(ids, 2):
            vals = []
            for left in clusters[a]["members"]:
                for right in clusters[b]["members"]:
                    vals.append(base_dist[frozenset([left, right])])
            dist = statistics.mean(vals) if vals else 0.0
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_pair = (a, b)
        assert best_pair is not None and best_dist is not None
        a, b = best_pair
        height = best_dist / 2.0
        left = clusters.pop(a)
        right = clusters.pop(b)
        left_len = height - float(left["height"])
        right_len = height - float(right["height"])
        newick = f"({left['newick']}:{format_length(left_len)},{right['newick']}:{format_length(right_len)})"
        members = sorted(left["members"] + right["members"])
        for x in left["members"]:
            for y in right["members"]:
                pair_tree_dist[tuple(sorted([x, y]))] = best_dist
        clusters[f"cluster_{next_id}"] = {"members": members, "height": height, "newick": newick}
        next_id += 1
    final = next(iter(clusters.values()))
    return f"{final['newick']}:0.000000;", pair_tree_dist


def build_tree(alignment_path: Path, tree_path: Path, engine: str, iqtree_bin: str, bootstrap: int) -> tuple[str, str, dict[tuple[str, str], float]]:
    engine_norm = engine.lower()
    if engine_norm == "auto":
        engine_norm = "iqtree2" if shutil.which(iqtree_bin) else "simple"
    if engine_norm in {"iqtree", "iqtree2"}:
        iqtree = shutil.which(iqtree_bin) or shutil.which(engine_norm)
        if not iqtree:
            return "skipped_missing_tree_engine", engine_norm, {}
        prefix = tree_path.with_suffix("")
        command = [iqtree, "-s", str(alignment_path), "-m", "MFP", "-nt", "AUTO", "-pre", str(prefix)]
        if bootstrap and bootstrap > 0:
            command.extend(["-B", str(bootstrap)])
        code, stderr = run_command(command)
        treefile = Path(str(prefix) + ".treefile")
        if code != 0 or not treefile.exists():
            return f"tree_failed:{stderr.strip()[:160]}", engine_norm, {}
        shutil.copyfile(treefile, tree_path)
        return "completed", engine_norm, {}
    if engine_norm == "simple":
        alignment = parse_alignment(alignment_path)
        newick, tree_dist = build_upgma_tree(alignment)
        tree_path.write_text(newick + "\n")
        return "completed", "simple_p_distance_upgma", tree_dist
    return f"unsupported_tree_engine:{engine}", engine_norm, {}


def read_distance_matrix(path: Path | None) -> dict[tuple[str, str], float]:
    if not path or not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    distances = {}
    for row in rows:
        row_id = row.get("sample_id", "")
        for col, value in row.items():
            if col == "sample_id" or not row_id or not value:
                continue
            if row_id < col:
                try:
                    distances[(row_id, col)] = float(value)
                except ValueError:
                    pass
    return distances


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(right) < 2:
        return None
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    num = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    den_left = math.sqrt(sum((a - mean_left) ** 2 for a in left))
    den_right = math.sqrt(sum((b - mean_right) ** 2 for b in right))
    if den_left == 0 or den_right == 0:
        return None
    return num / (den_left * den_right)


def topology_row(marker_kind: str, tree_dist: dict[tuple[str, str], float], intergenomic_dist: dict[tuple[str, str], float], engine: str) -> dict[str, str]:
    if not tree_dist:
        return {"marker_kind": marker_kind, "status": "not_computed", "shared_pairs": "0", "pearson_correlation": "", "tree_engine": engine, "note": "tree distances unavailable for this engine or marker"}
    x = []
    y = []
    for pair, tree_value in tree_dist.items():
        if pair in intergenomic_dist:
            x.append(tree_value)
            y.append(intergenomic_dist[pair])
    corr = pearson(x, y)
    if corr is None:
        return {"marker_kind": marker_kind, "status": "insufficient_variation", "shared_pairs": str(len(x)), "pearson_correlation": "", "tree_engine": engine, "note": "need at least two informative shared pairs"}
    return {"marker_kind": marker_kind, "status": "completed", "shared_pairs": str(len(x)), "pearson_correlation": f"{corr:.6f}", "tree_engine": engine, "note": "marker tree distances compared with BLASTN-derived intergenomic distances"}


def skipped_outputs(args: argparse.Namespace, samples: list[str], reason: str) -> None:
    args.markers_dir.mkdir(parents=True, exist_ok=True)
    args.alignments_dir.mkdir(parents=True, exist_ok=True)
    args.trees_dir.mkdir(parents=True, exist_ok=True)
    write_key_value(args.summary, {"method": "marker_gene_phylogeny", "status": "skipped", "reason": reason, "samples": str(len(samples)), "markers_requested": args.marker_kinds, "markers_built": "0", "tree_engine": args.tree_engine})
    write_rows(args.presence, [], PRESENCE_FIELDS)
    write_rows(args.topology, [], TOPOLOGY_FIELDS)
    write_rows(args.provenance, [], PROVENANCE_FIELDS)
    args.note.write_text(f"# Marker-Gene Phylogeny\n\nStatus: skipped. Reason: {reason}.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build marker-gene phylogenies for PhageFlow cohorts.")
    parser.add_argument("--samplesheet", required=True, type=Path)
    parser.add_argument("--faa-files", nargs="*", default=[], type=Path)
    parser.add_argument("--marker-faa", default=None, type=Path)
    parser.add_argument("--marker-source", default="auto", choices=["auto", "marker_faa", "manual", "faa_headers", "annotation"])
    parser.add_argument("--marker-kinds", default="terminase_large,portal,major_capsid")
    parser.add_argument("--marker-min-genomes", default=3, type=int)
    parser.add_argument("--tree-engine", default="iqtree2")
    parser.add_argument("--bootstrap", default=1000, type=int)
    parser.add_argument("--mafft-bin", default="mafft")
    parser.add_argument("--trimal-bin", default="trimal")
    parser.add_argument("--iqtree-bin", default="iqtree2")
    parser.add_argument("--intergenomic-distance-matrix", default=None, type=Path)
    parser.add_argument("--skip-reason", default="")
    parser.add_argument("--markers-dir", required=True, type=Path)
    parser.add_argument("--alignments-dir", required=True, type=Path)
    parser.add_argument("--trees-dir", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--presence", required=True, type=Path)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--note", required=True, type=Path)
    args = parser.parse_args()

    samples = load_samples(args.samplesheet)
    args.markers_dir.mkdir(parents=True, exist_ok=True)
    args.alignments_dir.mkdir(parents=True, exist_ok=True)
    args.trees_dir.mkdir(parents=True, exist_ok=True)
    marker_kinds = [kind.strip() for kind in args.marker_kinds.split(",") if kind.strip()]
    marker_kinds = [kind for kind in marker_kinds if kind in MARKER_ALIASES]
    if args.skip_reason:
        skipped_outputs(args, samples, args.skip_reason)
        return 0
    if not marker_kinds:
        skipped_outputs(args, samples, "no_supported_marker_kinds")
        return 0

    marker_faa = args.marker_faa if args.marker_faa and str(args.marker_faa) not in {"", "null", "None"} else None
    candidates = collect_candidates(samples, marker_faa, args.faa_files, marker_kinds, args.marker_source)
    presence_rows, selected_by_kind = select_markers(samples, marker_kinds, candidates)
    write_rows(args.presence, presence_rows, PRESENCE_FIELDS)

    intergenomic_dist = read_distance_matrix(args.intergenomic_distance_matrix)
    topology_rows: list[dict[str, str]] = []
    provenance_rows: list[dict[str, str]] = []
    marker_statuses = []
    built = 0
    for kind in marker_kinds:
        records = sorted(selected_by_kind.get(kind, []), key=lambda item: item.sample_id)
        if len(records) < args.marker_min_genomes:
            marker_statuses.append(f"{kind}:skipped_insufficient_genomes")
            topology_rows.append({"marker_kind": kind, "status": "skipped_insufficient_genomes", "shared_pairs": "0", "pearson_correlation": "", "tree_engine": args.tree_engine, "note": f"{len(records)} genomes with marker; need {args.marker_min_genomes}"})
            provenance_rows.append(
                {
                    "marker_kind": kind,
                    "records_selected": str(len(records)),
                    "marker_min_genomes": str(args.marker_min_genomes),
                    "alignment_status": "not_run",
                    "tree_status": "skipped_insufficient_genomes",
                    "tree_engine_requested": args.tree_engine,
                    "tree_engine_used": "",
                    "bootstrap": str(args.bootstrap),
                    "marker_fasta": "",
                    "alignment_file": "",
                    "tree_file": "",
                    "note": f"{len(records)} genomes with marker; need {args.marker_min_genomes}",
                }
            )
            continue
        marker_fasta = args.markers_dir / f"{kind}.faa"
        alignment = args.alignments_dir / f"{kind}.aligned.faa"
        tree = args.trees_dir / f"{kind}.nwk"
        write_fasta(records, marker_fasta)
        aligned_path, align_status = align_marker(marker_fasta, alignment, args.mafft_bin, args.trimal_bin, args.alignments_dir)
        if aligned_path is None:
            marker_statuses.append(f"{kind}:{align_status}")
            topology_rows.append({"marker_kind": kind, "status": align_status, "shared_pairs": "0", "pearson_correlation": "", "tree_engine": args.tree_engine, "note": "alignment unavailable"})
            provenance_rows.append(
                {
                    "marker_kind": kind,
                    "records_selected": str(len(records)),
                    "marker_min_genomes": str(args.marker_min_genomes),
                    "alignment_status": align_status,
                    "tree_status": "not_run",
                    "tree_engine_requested": args.tree_engine,
                    "tree_engine_used": "",
                    "bootstrap": str(args.bootstrap),
                    "marker_fasta": marker_fasta.name,
                    "alignment_file": "",
                    "tree_file": "",
                    "note": "alignment unavailable",
                }
            )
            continue
        tree_status, engine_used, tree_dist = build_tree(aligned_path, tree, args.tree_engine, args.iqtree_bin, args.bootstrap)
        marker_statuses.append(f"{kind}:{tree_status}")
        provenance_rows.append(
            {
                "marker_kind": kind,
                "records_selected": str(len(records)),
                "marker_min_genomes": str(args.marker_min_genomes),
                "alignment_status": align_status,
                "tree_status": tree_status,
                "tree_engine_requested": args.tree_engine,
                "tree_engine_used": engine_used,
                "bootstrap": str(args.bootstrap),
                "marker_fasta": marker_fasta.name,
                "alignment_file": aligned_path.name,
                "tree_file": tree.name if tree.exists() else "",
                "note": "tree built" if tree_status == "completed" else "tree was not built",
            }
        )
        if tree_status == "completed":
            built += 1
            topology_rows.append(topology_row(kind, tree_dist, intergenomic_dist, engine_used))
        else:
            topology_rows.append({"marker_kind": kind, "status": tree_status, "shared_pairs": "0", "pearson_correlation": "", "tree_engine": engine_used, "note": "tree was not built"})

    write_rows(args.topology, topology_rows, TOPOLOGY_FIELDS)
    write_rows(args.provenance, provenance_rows, PROVENANCE_FIELDS)
    status = "completed" if built else "skipped_no_trees_built"
    write_key_value(
        args.summary,
        {
            "method": "marker_gene_phylogeny",
            "status": status,
            "samples": str(len(samples)),
            "markers_requested": ",".join(marker_kinds),
            "markers_built": str(built),
            "markers_skipped": str(len(marker_kinds) - built),
            "marker_min_genomes": str(args.marker_min_genomes),
            "marker_source": args.marker_source,
            "tree_engine_requested": args.tree_engine,
            "marker_statuses": ";".join(marker_statuses),
        },
    )
    args.note.write_text(
        "# Marker-Gene Phylogeny\n\n"
        "Marker proteins were selected per genome and marker by longest candidate sequence. "
        "For manuscript use, prefer marker proteins from a consistent phage annotation backend such as Pharokka. "
        "The built-in simple engine is intended for lightweight validation; IQ-TREE2 is preferred for publication-grade inference.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
