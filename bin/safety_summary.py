#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = ["sample_id", "screen", "status", "artifact_id", "records", "bytes", "limitation"]
SAMPLE_SCREENS = [
    ("trnascan", "05_optional/trnascan/{sample_id}.trnascan.tsv", "Descriptive optional artifact; not a safety conclusion."),
    ("bacphlip", "05_optional/bacphlip/{sample_id}.bacphlip.log", "Lifecycle-classifier log presence only; interpret conservatively."),
    ("checkv", "05_optional/checkv/{sample_id}.checkv/quality_summary.tsv", "Quality summary only; not an AMR or virulence screen."),
    ("abricate", "05_optional/abricate/{sample_id}.abricate.tsv", "Row counts only; feature names are intentionally not printed."),
    ("pharokka", "05_optional/pharokka/{sample_id}.pharokka", "Annotation directory presence only; parse tool-specific tables separately for biology."),
    ("genomad", "05_optional/genomad/{sample_id}.genomad.log", "Classifier log presence only; not a standalone safety conclusion."),
    ("phold", "05_optional/phold/{sample_id}.phold.log", "Structural-annotation log presence only; not a standalone safety conclusion."),
]
COHORT_SCREENS = [
    ("clinker_synteny", "05_optional/clinker_synteny/clinker_synteny.html", "Comparative synteny artifact only; not a safety screen."),
]


def row_count(path: Path) -> int:
    if not path.exists() or path.is_dir() or path.stat().st_size == 0:
        return 0
    try:
        with path.open(newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            next(reader, None)
            return sum(1 for row in reader if any(cell.strip() for cell in row))
    except UnicodeDecodeError:
        return 0


def read_samples(root: Path) -> list[str]:
    samplesheet = root / "00_inputs" / "samplesheet.normalized.tsv"
    if samplesheet.exists():
        with samplesheet.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            samples = [row.get("sample_id", "").strip() for row in reader if row.get("sample_id", "").strip()]
            if samples:
                return samples
    fasta_table = root / "99_report" / "tables" / "fasta_stats_combined.tsv"
    if fasta_table.exists():
        with fasta_table.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return [row.get("sample_id", "").strip() for row in reader if row.get("sample_id", "").strip()]
    return []


def artifact_id(index: dict[Path, str], path: Path) -> str:
    if path not in index:
        index[path] = f"SAFETY_ART_{len(index) + 1:03d}"
    return index[path]


def status_for(screen: str, path: Path) -> str:
    if not path.exists():
        return "not_run"
    if path.is_dir():
        return "available" if any(path.iterdir()) else "empty_artifact"
    rows = row_count(path)
    if screen == "abricate":
        return "rows_detected" if rows else "no_rows_detected"
    return "available" if path.stat().st_size > 0 else "empty_artifact"


def collect_safety_rows(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    samples = read_samples(root)
    artifact_ids: dict[Path, str] = {}
    rows: list[dict[str, str]] = []

    for sample_id in samples:
        for screen, template, limitation in SAMPLE_SCREENS:
            path = root / template.format(sample_id=sample_id)
            exists = path.exists()
            rows.append(
                {
                    "sample_id": sample_id,
                    "screen": screen,
                    "status": status_for(screen, path),
                    "artifact_id": artifact_id(artifact_ids, path) if exists else "",
                    "records": str(row_count(path)) if exists and path.is_file() else "0",
                    "bytes": str(path.stat().st_size) if exists and path.is_file() else "0",
                    "limitation": limitation,
                }
            )

    for screen, rel, limitation in COHORT_SCREENS:
        path = root / rel
        exists = path.exists()
        rows.append(
            {
                "sample_id": "COHORT",
                "screen": screen,
                "status": status_for(screen, path),
                "artifact_id": artifact_id(artifact_ids, path) if exists else "",
                "records": str(row_count(path)) if exists and path.is_file() else "0",
                "bytes": str(path.stat().st_size) if exists and path.is_file() else "0",
                "limitation": limitation,
            }
        )
    return rows


def summarize_safety_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    status_counts = Counter(row["status"] for row in rows)
    screen_counts = Counter(row["screen"] for row in rows)
    rows_detected = [row["screen"] for row in rows if row["status"] == "rows_detected"]
    return {
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "screen_counts": dict(sorted(screen_counts.items())),
        "screens_with_rows_detected": sorted(set(rows_detected)),
        "software_validation_conclusion": (
            "Consolidated optional-screen artifact summary completed. Row counts and artifact "
            "presence are software QA signals only and do not provide biological interpretation."
        ),
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize optional safety-related PhageFlow artifacts without printing feature names.")
    parser.add_argument("--outdir", required=True, type=Path, help="Completed PhageFlow output directory.")
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args()

    if not args.outdir.exists() or not args.outdir.is_dir():
        parser.error(f"--outdir is not a directory: {args.outdir}")

    rows = collect_safety_rows(args.outdir)
    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_safety_rows(rows), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
