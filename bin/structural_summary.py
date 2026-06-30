#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from artifact_inventory import sha256_file


STRUCTURAL_NAME_TOKENS = ("phold", "foldseek", "prostt5", "3di", "structural")
STRUCTURAL_EXTS = {".tsv", ".csv", ".gb", ".gbk", ".gff", ".log", ".txt", ".json", ".faa", ".fasta", ".tif", ".tiff", ".png", ".pdf", ".svg"}
FIELDS = ["artifact_id", "artifact_type", "extension", "records", "columns", "bytes", "sha256", "status", "limitation"]


def delimited_shape(path: Path) -> tuple[int, int]:
    if not path.exists() or path.stat().st_size == 0:
        return 0, 0
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    try:
        with path.open(newline="", errors="ignore") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, [])
            rows = sum(1 for row in reader if any(cell.strip() for cell in row))
        return rows, len(header)
    except Exception:
        return 0, 0


def artifact_type(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff", ".png", ".pdf", ".svg"}:
        return "figure"
    if "sub_db_tophits" in path.as_posix().lower():
        return "sub_database_top_hits"
    if "per_cds" in name or "all_cds" in name:
        return "per_cds_table"
    if "confidence" in name or "function_counts" in name:
        return "summary_table"
    if suffix in {".gb", ".gbk", ".gff"}:
        return "annotation_file"
    if suffix in {".faa", ".fasta"}:
        return "sequence_artifact"
    if suffix == ".log":
        return "log"
    return "structural_artifact"


def is_structural_artifact(path: Path) -> bool:
    lower = path.as_posix().lower()
    return path.suffix.lower() in STRUCTURAL_EXTS and any(token in lower for token in STRUCTURAL_NAME_TOKENS)


def collect_structural_rows(root: Path) -> list[dict[str, str]]:
    files = sorted(path for path in root.resolve().rglob("*") if path.is_file() and is_structural_artifact(path))
    rows = []
    for index, path in enumerate(files, start=1):
        records, columns = delimited_shape(path) if path.suffix.lower() in {".tsv", ".csv"} else (0, 0)
        rows.append(
            {
                "artifact_id": f"STRUCT_{index:03d}",
                "artifact_type": artifact_type(path),
                "extension": path.suffix.lower(),
                "records": str(records),
                "columns": str(columns),
                "bytes": str(path.stat().st_size),
                "sha256": sha256_file(path),
                "status": "available" if path.stat().st_size > 0 else "empty_artifact",
                "limitation": "Structural annotation artifact inventory only; no annotation values or biological interpretation are reported.",
            }
        )
    return rows


def summarize_structural_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        by_type[row["artifact_type"]] = by_type.get(row["artifact_type"], 0) + 1
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "structural_artifact_count": len(rows),
        "artifact_type_counts": dict(sorted(by_type.items())),
        "status_counts": dict(sorted(by_status.items())),
        "software_validation_conclusion": (
            "Structural annotation artifact inventory completed. This is a software QA "
            "summary and does not report or interpret structural annotations."
        ),
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize structural-annotation artifacts without printing annotation values.")
    parser.add_argument("--outdir", required=True, type=Path, help="Completed output directory or project artifact directory.")
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args()

    if not args.outdir.exists() or not args.outdir.is_dir():
        parser.error(f"--outdir is not a directory: {args.outdir}")

    rows = collect_structural_rows(args.outdir)
    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_structural_rows(rows), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
