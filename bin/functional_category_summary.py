#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from optional_tool_summary import index_sample_artifacts, read_samples, root_artifacts


FIELDS = [
    "tool",
    "sample_id",
    "category_source",
    "category",
    "count",
    "records",
    "status",
    "limitation",
]
LIMITATION = (
    "Functional-category count summary only. Counts require a consistent heavy annotation "
    "output such as Pharokka; individual gene/product annotations are not printed or interpreted."
)


def clean_cell(value: object) -> str:
    return " ".join(str(value or "").replace("\t", " ").split())


def delimited_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    try:
        with path.open(newline="", errors="ignore") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = [dict(row) for row in reader]
            return rows, list(reader.fieldnames or [])
    except Exception:
        return [], []


def candidate_tables(path: Path | None) -> list[Path]:
    if path is None or not path.exists():
        return []
    if path.is_file() and path.suffix.lower() in {".tsv", ".csv"}:
        return [path]
    patterns = [
        "**/*cds_functions*.tsv",
        "**/*function*.tsv",
        "**/*annotation*.tsv",
        "**/*summary*.tsv",
        "**/*.tsv",
        "**/*.csv",
    ]
    tables: list[Path] = []
    for pattern in patterns:
        for match in sorted(path.glob(pattern)):
            if match.is_file() and match not in tables:
                tables.append(match)
    return tables


def category_columns(columns: list[str]) -> list[str]:
    output = []
    for column in columns:
        normalized = column.lower().replace(" ", "_").replace("-", "_")
        if "category" in normalized:
            output.append(column)
    return output


def summarize_pharokka_sample(sample_id: str, artifact: Path | None) -> list[dict[str, str]]:
    if artifact is None or not artifact.exists():
        return [
            {
                "tool": "pharokka",
                "sample_id": sample_id,
                "category_source": "",
                "category": "",
                "count": "0",
                "records": "0",
                "status": "not_run",
                "limitation": LIMITATION,
            }
        ]

    for table in candidate_tables(artifact):
        rows, columns = delimited_rows(table)
        categories = category_columns(columns)
        if not categories:
            continue
        column = categories[0]
        counts = Counter(clean_cell(row.get(column)) or "uncategorized" for row in rows)
        if not counts:
            return [
                {
                    "tool": "pharokka",
                    "sample_id": sample_id,
                    "category_source": column,
                    "category": "",
                    "count": "0",
                    "records": str(len(rows)),
                    "status": "available_no_category_rows",
                    "limitation": LIMITATION,
                }
            ]
        return [
            {
                "tool": "pharokka",
                "sample_id": sample_id,
                "category_source": column,
                "category": category,
                "count": str(count),
                "records": str(len(rows)),
                "status": "available",
                "limitation": LIMITATION,
            }
            for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    records = 0
    for table in candidate_tables(artifact):
        rows, _columns = delimited_rows(table)
        records = max(records, len(rows))
    return [
        {
            "tool": "pharokka",
            "sample_id": sample_id,
            "category_source": "",
            "category": "",
            "count": "0",
            "records": str(records),
            "status": "category_column_missing",
            "limitation": LIMITATION,
        }
    ]


def collect_functional_category_rows(
    samplesheet: Path | None,
    root: Path | None,
    pharokka_artifacts: list[Path],
) -> list[dict[str, str]]:
    root = root.resolve() if root else None
    samples = read_samples(samplesheet, root)
    artifacts = index_sample_artifacts(pharokka_artifacts or (root_artifacts(root, "pharokka") if root else []), "pharokka")
    if not samples:
        samples = sorted(artifacts)

    rows: list[dict[str, str]] = []
    for sample_id in samples:
        rows.extend(summarize_pharokka_sample(sample_id, artifacts.get(sample_id)))
    return rows


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "rows": len(rows),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "available_category_rows": sum(1 for row in rows if row["status"] == "available"),
        "samples": sorted({row["sample_id"] for row in rows if row["sample_id"]}),
        "software_validation_conclusion": LIMITATION,
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(clean_cell(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize broad functional-category counts from consistent heavy annotation outputs.")
    parser.add_argument("--root", default=None, type=Path, help="Completed PhageFlow output directory.")
    parser.add_argument("--samplesheet", default=None, type=Path, help="Normalized samplesheet for expected sample IDs.")
    parser.add_argument("--pharokka-artifact", action="append", default=[], type=Path)
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args()

    if args.root and (not args.root.exists() or not args.root.is_dir()):
        parser.error(f"--root is not a directory: {args.root}")

    rows = collect_functional_category_rows(args.samplesheet, args.root, args.pharokka_artifact)
    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_rows(rows), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
