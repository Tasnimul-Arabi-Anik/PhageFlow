#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REQUIRED_REPORT_FILES = [
    "index.html",
    "phageflow_report.md",
    "important_files.tsv",
    "validation_manifest.json",
    "software_versions.tsv",
    "params.json",
    "runtime_summary.tsv",
]

REQUIRED_TABLES = [
    "fasta_stats_combined.tsv",
    "orf_summary_combined.tsv",
    "codon_summary_combined.tsv",
    "cohort_similarity_summary.tsv",
    "cohort_pairwise_similarity.tsv",
    "intergenomic_similarity_summary.tsv",
    "intergenomic_similarity_pairs.tsv",
    "intergenomic_similarity_matrix.tsv",
    "intergenomic_distance_matrix.tsv",
    "marker_tree_summary.tsv",
    "marker_presence.tsv",
    "marker_topology_consistency.tsv",
    "pangenome_summary.tsv",
    "presence_absence.tsv",
    "genome_metadata.tsv",
    "host_context.tsv",
    "host_codon_adaptation.tsv",
    "host_codon_rscu.tsv",
    "crispr_spacer_matches.tsv",
    "crispr_spacer_summary.tsv",
    "optional_tool_summary.tsv",
]

OPTIONAL_GROUPS = {
    "lite": ["trnascan", "bacphlip", "abricate"],
    "publication": ["trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "clinker"],
    "structure": ["phold"],
    "host": ["host"],
    "all": ["trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "clinker", "host"],
}

OPTIONAL_TOOLS = {
    "trnascan": ["tRNAscan-SE"],
    "bacphlip": ["bacphlip"],
    "checkv": ["checkv"],
    "abricate": ["abricate"],
    "pharokka": ["pharokka.py"],
    "genomad": ["genomad"],
    "phold": ["phold"],
    "clinker": ["clinker"],
    "host": ["prodigal", "minced"],
}


def row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        return sum(1 for row in reader if any(cell.strip() for cell in row))


def line_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open() as handle:
        return sum(1 for line in handle if line.strip())


def read_key_value(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                values[row[0]] = row[1]
    return values


def read_samples(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [row.get("sample_id", "").strip() for row in reader if row.get("sample_id", "").strip()]


def read_software_versions(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            tool = row.get("tool", "")
            if tool:
                values[tool] = row.get("version_or_status", "")
    return values


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader]


def path_has_content(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        return any(path.iterdir())
    return False


def check_file(results: list[dict[str, str]], label: str, path: Path, required_nonempty: bool = True) -> bool:
    exists = path.exists()
    nonempty = exists and path_has_content(path)
    ok = exists and (nonempty or not required_nonempty)
    results.append(
        {
            "check": label,
            "path": str(path),
            "exists": "true" if exists else "false",
            "nonempty": "true" if nonempty else "false",
            "status": "PASS" if ok else "FAIL",
        }
    )
    return ok


def check_min_count(results: list[dict[str, str]], label: str, path: Path, minimum: int) -> bool:
    count = row_count(path)
    ok = count >= minimum
    results.append(
        {
            "check": label,
            "path": str(path),
            "exists": "true" if path.exists() else "false",
            "nonempty": "true" if count > 0 else "false",
            "status": "PASS" if ok else "FAIL",
            "observed_count": str(count),
            "minimum_count": str(minimum),
        }
    )
    return ok


def check_min_lines(results: list[dict[str, str]], label: str, path: Path, minimum: int) -> bool:
    count = line_count(path)
    ok = count >= minimum
    results.append(
        {
            "check": label,
            "path": str(path),
            "exists": "true" if path.exists() else "false",
            "nonempty": "true" if count > 0 else "false",
            "status": "PASS" if ok else "FAIL",
            "observed_count": str(count),
            "minimum_count": str(minimum),
        }
    )
    return ok


def check_glob_count(
    results: list[dict[str, str]],
    label: str,
    directory: Path,
    pattern: str,
    minimum: int,
    require_nonempty: bool = True,
) -> bool:
    matches = sorted(directory.glob(pattern)) if directory.exists() else []
    enough = len(matches) >= minimum
    contents_ok = all(path_has_content(path) for path in matches) if require_nonempty else True
    ok = enough and contents_ok
    results.append(
        {
            "check": label,
            "path": str(directory / pattern),
            "exists": "true" if directory.exists() else "false",
            "nonempty": "true" if matches and contents_ok else "false",
            "status": "PASS" if ok else "FAIL",
            "observed_count": str(len(matches)),
            "minimum_count": str(minimum),
        }
    )
    return ok


def check_software(results: list[dict[str, str]], versions: dict[str, str], tool: str) -> bool:
    value = versions.get(tool, "")
    ok = bool(value) and value != "not_found"
    results.append(
        {
            "check": f"optional_tool_available:{tool}",
            "path": "99_report/software_versions.tsv",
            "exists": "true" if value else "false",
            "nonempty": "true" if value else "false",
            "status": "PASS" if ok else "FAIL",
            "value": value or "missing_version_record",
        }
    )
    return ok


def expected_optional_modules(args: argparse.Namespace) -> list[str]:
    expected: list[str] = []
    raw_items = []
    for item in args.expect_optional or []:
        raw_items.extend(part.strip() for part in item.split(",") if part.strip())
    if args.expect_lite_optionals:
        raw_items.append("lite")
    if args.expect_publication_optionals:
        raw_items.append("publication")
    for name in ["trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "clinker"]:
        if getattr(args, f"expect_{name}"):
            raw_items.append(name)
    for item in raw_items:
        expanded = OPTIONAL_GROUPS.get(item, [item])
        for module in expanded:
            if module not in OPTIONAL_TOOLS:
                raise ValueError(f"Unknown optional module/group '{item}'. Use one of: {', '.join(sorted(set(OPTIONAL_TOOLS) | set(OPTIONAL_GROUPS)))}")
            if module not in expected:
                expected.append(module)
    return expected


def check_optional_module(
    results: list[dict[str, str]],
    outdir: Path,
    module: str,
    sample_count: int,
    versions: dict[str, str],
) -> bool:
    optional_dir = outdir / "05_optional"
    ok = True
    for tool in OPTIONAL_TOOLS[module]:
        ok &= check_software(results, versions, tool)

    if module == "trnascan":
        directory = optional_dir / "trnascan"
        ok &= check_glob_count(results, "optional_output:trnascan_tables", directory, "*.trnascan.tsv", sample_count)
        ok &= check_glob_count(results, "optional_output:trnascan_logs", directory, "*.trnascan.log", sample_count)
    elif module == "bacphlip":
        directory = optional_dir / "bacphlip"
        ok &= check_glob_count(results, "optional_output:bacphlip_logs", directory, "*.bacphlip.log", sample_count)
    elif module == "checkv":
        directory = optional_dir / "checkv"
        ok &= check_glob_count(results, "optional_output:checkv_dirs", directory, "*.checkv", sample_count)
        ok &= check_glob_count(results, "optional_output:checkv_quality_summaries", directory, "*.checkv/quality_summary.tsv", sample_count)
    elif module == "abricate":
        directory = optional_dir / "abricate"
        ok &= check_glob_count(results, "optional_output:abricate_tables", directory, "*.abricate.tsv", sample_count)
    elif module == "pharokka":
        directory = optional_dir / "pharokka"
        ok &= check_glob_count(results, "optional_output:pharokka_dirs", directory, "*.pharokka", sample_count)
        ok &= check_glob_count(results, "optional_output:pharokka_genbank", directory, "*.pharokka/**/*.gb*", sample_count)
        ok &= check_glob_count(results, "optional_output:pharokka_gff", directory, "*.pharokka/**/*.gff*", sample_count)
    elif module == "genomad":
        directory = optional_dir / "genomad"
        ok &= check_glob_count(results, "optional_output:genomad_dirs", directory, "*.genomad", sample_count)
        ok &= check_glob_count(results, "optional_output:genomad_logs", directory, "*.genomad.log", sample_count)
    elif module == "phold":
        directory = optional_dir / "phold"
        ok &= check_glob_count(results, "optional_output:phold_dirs", directory, "*.phold", sample_count)
        ok &= check_glob_count(results, "optional_output:phold_logs", directory, "*.phold.log", sample_count)
    elif module == "clinker":
        directory = optional_dir / "clinker_synteny"
        ok &= check_file(results, "optional_output:clinker_html", directory / "clinker_synteny.html")
        ok &= check_file(results, "optional_output:clinker_gbk_files", directory / "gbk_files.txt")
        ok &= check_file(results, "optional_output:clinker_note", directory / "clinker_synteny_note.md")
        min_gbk = min(sample_count, 2) if sample_count else 2
        if sample_count >= 2:
            ok &= check_min_lines(results, "optional_output:clinker_gbk_file_count", directory / "gbk_files.txt", min_gbk)
    return bool(ok)


def check_optional_summary_module(
    results: list[dict[str, str]],
    tables_dir: Path,
    module: str,
    sample_count: int,
) -> bool:
    path = tables_dir / "optional_tool_summary.tsv"
    rows = read_rows(path)
    expected = 1 if module == "clinker" else sample_count
    matching = [row for row in rows if row.get("tool") == module]
    available = [row for row in matching if row.get("status") == "available"]
    ok = len(matching) >= expected and len(available) >= expected
    results.append(
        {
            "check": f"optional_summary:{module}",
            "path": str(path),
            "exists": "true" if path.exists() else "false",
            "nonempty": "true" if rows else "false",
            "status": "PASS" if ok else "FAIL",
            "observed_count": str(len(available)),
            "minimum_count": str(expected),
        }
    )
    return ok



def check_host_adaptation(results: list[dict[str, str]], tables_dir: Path, figures_dir: Path) -> bool:
    ok = True
    ok &= check_min_count(results, "host_adaptation_rows", tables_dir / "host_codon_adaptation.tsv", 1)
    ok &= check_min_count(results, "host_rscu_rows", tables_dir / "host_codon_rscu.tsv", 1)
    ok &= check_glob_count(results, "host_adaptation_tiff_figures", figures_dir, "host_codon_adaptation*.tiff", 1)
    return bool(ok)


def check_crispr_hits(results: list[dict[str, str]], tables_dir: Path) -> bool:
    ok = True
    matches = row_count(tables_dir / "crispr_spacer_matches.tsv")
    hit_ok = matches > 0
    results.append(
        {
            "check": "crispr_spacer_hits_required",
            "path": str(tables_dir / "crispr_spacer_matches.tsv"),
            "exists": "true" if (tables_dir / "crispr_spacer_matches.tsv").exists() else "false",
            "nonempty": "true" if matches > 0 else "false",
            "status": "PASS" if hit_ok else "FAIL",
            "observed_count": str(matches),
            "minimum_count": "1",
        }
    )
    ok &= hit_ok
    ok &= check_min_count(results, "crispr_spacer_summary_rows", tables_dir / "crispr_spacer_summary.tsv", 1)
    return bool(ok)


def check_marker_tree(results: list[dict[str, str]], outdir: Path, tables_dir: Path, figures_dir: Path) -> bool:
    ok = True
    summary_path = tables_dir / "marker_tree_summary.tsv"
    summary = read_key_value(summary_path)
    status = summary.get("status", "")
    built = int(float(summary.get("markers_built", "0") or 0))
    status_ok = status == "completed" and built > 0
    results.append(
        {
            "check": "marker_tree_summary_completed",
            "path": str(summary_path),
            "exists": "true" if summary_path.exists() else "false",
            "nonempty": "true" if row_count(summary_path) > 0 else "false",
            "status": "PASS" if status_ok else "FAIL",
            "value": f"status={status};markers_built={built}",
        }
    )
    ok &= status_ok
    ok &= check_min_count(results, "marker_tree_presence_rows", tables_dir / "marker_presence.tsv", 1)
    ok &= check_min_count(results, "marker_tree_topology_rows", tables_dir / "marker_topology_consistency.tsv", 1)
    ok &= check_min_count(results, "marker_tree_provenance_rows", tables_dir / "marker_provenance.tsv", 1)
    ok &= check_glob_count(results, "marker_tree_newick_files", outdir / "04_comparative" / "marker_phylogeny" / "trees", "*.nwk", 1)
    ok &= check_glob_count(results, "marker_tree_tiff_figures", figures_dir, "marker_tree_*.tiff", 1)
    return bool(ok)


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a completed PhageFlow run directory.")
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--report", default=None, type=Path, help="Optional path for validation report TSV.")
    parser.add_argument("--min-figures", default=2, type=int)
    parser.add_argument("--require-pangenome-rows", action="store_true")
    parser.add_argument("--expect-marker-tree", action="store_true", help="Require completed marker-gene phylogeny outputs and TIFF tree figures.")
    parser.add_argument("--expect-host-adaptation", action="store_true", help="Require nonempty host codon-adaptation/RSCU outputs and host-adaptation TIFF figure.")
    parser.add_argument("--expect-crispr-hits", action="store_true", help="Require at least one CRISPR spacer/protospacer match row.")
    parser.add_argument("--expect-optional", action="append", default=[], help="Optional module or comma-separated modules/groups expected in 05_optional. Groups: lite, publication, structure, host, all.")
    parser.add_argument("--expect-lite-optionals", action="store_true", help="Require tRNAscan-SE, BACPHLIP, and ABRicate outputs.")
    parser.add_argument("--expect-publication-optionals", action="store_true", help="Require tRNAscan-SE, BACPHLIP, CheckV, ABRicate, Pharokka, geNomad, and clinker outputs.")
    for module in ["trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "clinker"]:
        parser.add_argument(f"--expect-{module}", action="store_true", help=f"Require {module} optional outputs and software-version records.")
    for module in ["checkv", "pharokka", "genomad", "phold", "clinker"]:
        parser.add_argument(f"--expect-{module}-summary", action="store_true", help=f"Require {module} rows in 99_report/tables/optional_tool_summary.tsv.")
    args = parser.parse_args()

    outdir = args.outdir
    report_dir = outdir / "99_report"
    tables_dir = report_dir / "tables"
    figures_dir = report_dir / "figures"
    results = []
    ok = True

    normalized_samplesheet = outdir / "00_inputs" / "samplesheet.normalized.tsv"
    ok &= check_file(results, "normalized_samplesheet", normalized_samplesheet)
    ok &= check_file(results, "validation_summary", outdir / "00_inputs" / "validation_summary.tsv")
    ok &= check_file(results, "cohort_similarity_summary", outdir / "04_comparative" / "cohort_similarity" / "cohort_similarity_summary.tsv")

    for name in REQUIRED_REPORT_FILES:
        ok &= check_file(results, f"report_file:{name}", report_dir / name)
    optional_empty_tables = {"host_context.tsv", "host_codon_adaptation.tsv", "host_codon_rscu.tsv", "crispr_spacer_matches.tsv", "presence_absence.tsv", "cohort_pairwise_similarity.tsv", "intergenomic_similarity_pairs.tsv", "marker_presence.tsv", "marker_topology_consistency.tsv"}
    for name in REQUIRED_TABLES:
        required_rows = 0 if name in optional_empty_tables else 1
        ok &= check_min_count(results, f"report_table:{name}", tables_dir / name, required_rows)

    figure_pngs = sorted(figures_dir.glob("*.png")) if figures_dir.exists() else []
    figure_tiffs = sorted(figures_dir.glob("*.tiff")) if figures_dir.exists() else []
    ok &= len(figure_pngs) >= args.min_figures
    results.append({"check": "figure_png_count", "path": str(figures_dir), "observed_count": str(len(figure_pngs)), "minimum_count": str(args.min_figures), "status": "PASS" if len(figure_pngs) >= args.min_figures else "FAIL"})
    ok &= len(figure_tiffs) >= args.min_figures
    results.append({"check": "figure_tiff_count", "path": str(figures_dir), "observed_count": str(len(figure_tiffs)), "minimum_count": str(args.min_figures), "status": "PASS" if len(figure_tiffs) >= args.min_figures else "FAIL"})

    manifest_path = report_dir / "validation_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            manifest_ok = bool(manifest.get("report_complete"))
            ok &= manifest_ok
            results.append({"check": "manifest_report_complete", "path": str(manifest_path), "status": "PASS" if manifest_ok else "FAIL", "value": str(manifest.get("report_complete"))})
        except Exception as exc:
            ok = False
            results.append({"check": "manifest_json_parse", "path": str(manifest_path), "status": "FAIL", "value": exc.__class__.__name__})

    if args.expect_marker_tree:
        ok &= check_marker_tree(results, outdir, tables_dir, figures_dir)

    if args.expect_host_adaptation:
        ok &= check_host_adaptation(results, tables_dir, figures_dir)

    if args.expect_crispr_hits:
        ok &= check_crispr_hits(results, tables_dir)

    if args.require_pangenome_rows:
        pangenome_rows = row_count(tables_dir / "presence_absence.tsv")
        row_ok = pangenome_rows > 0
        ok &= row_ok
        results.append({"check": "pangenome_presence_rows_required", "path": str(tables_dir / "presence_absence.tsv"), "observed_count": str(pangenome_rows), "minimum_count": "1", "status": "PASS" if row_ok else "FAIL"})

    try:
        expected_modules = expected_optional_modules(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if expected_modules:
        samples = read_samples(normalized_samplesheet)
        validation_values = read_key_value(outdir / "00_inputs" / "validation_summary.tsv")
        sample_count = len(samples) or int(float(validation_values.get("genomes", "1") or 1))
        versions = read_software_versions(report_dir / "software_versions.tsv")
        for module in expected_modules:
            if module == "host":
                for tool in OPTIONAL_TOOLS[module]:
                    ok &= check_software(results, versions, tool)
            else:
                ok &= check_optional_module(results, outdir, module, sample_count, versions)
                if module in {"checkv", "pharokka", "genomad", "phold", "clinker"}:
                    ok &= check_optional_summary_module(results, tables_dir, module, sample_count)

    expected_summary_modules = [module for module in ["checkv", "pharokka", "genomad", "phold", "clinker"] if getattr(args, f"expect_{module}_summary")]
    if expected_summary_modules:
        samples = read_samples(normalized_samplesheet)
        validation_values = read_key_value(outdir / "00_inputs" / "validation_summary.tsv")
        sample_count = len(samples) or int(float(validation_values.get("genomes", "1") or 1))
        for module in expected_summary_modules:
            ok &= check_optional_summary_module(results, tables_dir, module, sample_count)

    report_path = args.report or (report_dir / "phageflow_validation_report.tsv")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_results(report_path, results)
    if not ok:
        print(f"PhageFlow validation failed. See {report_path}", file=sys.stderr)
        return 1
    print(f"PhageFlow validation passed. Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
