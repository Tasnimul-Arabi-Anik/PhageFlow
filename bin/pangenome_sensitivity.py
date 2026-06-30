#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter


DEFAULT_METRICS = [
    "method",
    "genomes",
    "proteins",
    "orthogroups",
    "core_orthogroups",
    "accessory_orthogroups",
    "singleton_orthogroups",
]
FIELDS = ["metric", "left_value", "right_value", "delta_right_minus_left", "status", "limitation"]
SUMMARY_FIELDS = ["metric", "value", "limitation"]
LIMITATION = "Completed-run pangenome metric comparison only; not a biological interpretation."


def read_key_value(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                values[row[0]] = row[1]
    return values


def read_comparison_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [{field: str(row.get(field, "")) for field in FIELDS} for row in reader]


def pangenome_summary_path(root: Path) -> Path:
    candidates = [
        root / "99_report" / "tables" / "pangenome_summary.tsv",
        root / "04_comparative" / "mmseqs_pangenome" / "pangenome_summary.tsv",
        root / "04_comparative" / "rbh_blastp_pangenome" / "pangenome_summary.tsv",
        root / "04_comparative" / "no_pangenome" / "pangenome_summary.tsv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def numeric_delta(left: str, right: str) -> str:
    try:
        return str(float(right) - float(left))
    except (TypeError, ValueError):
        return ""


def compare(left_root: Path, right_root: Path) -> list[dict[str, str]]:
    left = read_key_value(pangenome_summary_path(left_root))
    right = read_key_value(pangenome_summary_path(right_root))
    metrics = list(dict.fromkeys(DEFAULT_METRICS + sorted(set(left) | set(right))))
    rows = []
    for metric in metrics:
        left_value = left.get(metric, "")
        right_value = right.get(metric, "")
        delta = numeric_delta(left_value, right_value)
        if not left_value or not right_value:
            status = "missing_metric"
        elif delta and float(delta) != 0:
            status = "different"
        elif not delta and left_value != right_value:
            status = "different"
        else:
            status = "same"
        rows.append(
            {
                "metric": metric,
                "left_value": left_value,
                "right_value": right_value,
                "delta_right_minus_left": delta,
                "status": status,
                "limitation": LIMITATION,
            }
        )
    return rows


def summarize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    statuses = Counter(row.get("status", "") or "unknown" for row in rows)
    numeric_delta_rows = [
        row
        for row in rows
        if row.get("delta_right_minus_left", "").strip()
        and row.get("delta_right_minus_left", "").strip() not in {"0", "0.0"}
    ]
    return [
        {"metric": "comparison_rows", "value": str(len(rows)), "limitation": LIMITATION},
        {"metric": "same_metrics", "value": str(statuses.get("same", 0)), "limitation": LIMITATION},
        {"metric": "different_metrics", "value": str(statuses.get("different", 0)), "limitation": LIMITATION},
        {"metric": "missing_metrics", "value": str(statuses.get("missing_metric", 0)), "limitation": LIMITATION},
        {"metric": "numeric_delta_metrics", "value": str(len(numeric_delta_rows)), "limitation": LIMITATION},
    ]


def summarize_for_json(rows: list[dict[str, str]]) -> dict[str, object]:
    statuses = Counter(row.get("status", "") or "unknown" for row in rows)
    return {
        "detected": bool(rows),
        "rows": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "numeric_delta_metrics": sum(
            1
            for row in rows
            if row.get("delta_right_minus_left", "").strip()
            and row.get("delta_right_minus_left", "").strip() not in {"0", "0.0"}
        ),
        "software_validation_conclusion": LIMITATION,
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def summary_rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(SUMMARY_FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in SUMMARY_FIELDS))
    return "\n".join(lines) + "\n"


def markdown_report(rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Pangenome Sensitivity Summary",
        "",
        "Completed-run pangenome method-sensitivity QA. This report compares software summary metrics only and does not choose a biologically correct method.",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row.get('metric', '')} | {row.get('value', '')} |")
    lines.extend(
        [
            "",
            "## Metric Comparison",
            "",
            "| metric | left_value | right_value | delta_right_minus_left | status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(str(row.get(field, "")) for field in ["metric", "left_value", "right_value", "delta_right_minus_left", "status"])
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def update_important_files(report_dir: Path) -> None:
    path = report_dir / "important_files.tsv"
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows.extend(dict(row) for row in reader)
    existing_paths = {row.get("path", "") for row in rows}
    additions = [
        {
            "category": "table",
            "path": "tables/pangenome_sensitivity.tsv",
            "description": "Completed-run pangenome method-sensitivity metric comparison",
        },
        {
            "category": "qa",
            "path": "tables/pangenome_sensitivity_summary.tsv",
            "description": "Summary counts for imported pangenome method-sensitivity comparison",
        },
        {
            "category": "report",
            "path": "pangenome_sensitivity_report.md",
            "description": "Markdown pangenome method-sensitivity summary",
        },
    ]
    rows.extend(row for row in additions if row["path"] not in existing_paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "path", "description"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def import_to_report(root: Path, rows: list[dict[str, str]]) -> dict[str, str]:
    report_dir = root / "99_report"
    tables_dir = report_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = summarize_rows(rows)
    comparison_path = tables_dir / "pangenome_sensitivity.tsv"
    summary_path = tables_dir / "pangenome_sensitivity_summary.tsv"
    markdown_path = report_dir / "pangenome_sensitivity_report.md"
    comparison_path.write_text(rows_to_tsv(rows))
    summary_path.write_text(summary_rows_to_tsv(summary_rows))
    markdown_path.write_text(markdown_report(rows, summary_rows))
    update_important_files(report_dir)
    return {
        "comparison": comparison_path.as_posix(),
        "summary": summary_path.as_posix(),
        "markdown": markdown_path.as_posix(),
    }


def report_import_summary(root: Path) -> dict[str, object]:
    path = root / "99_report" / "tables" / "pangenome_sensitivity.tsv"
    rows = read_comparison_rows(path)
    summary = summarize_for_json(rows)
    summary["detected"] = path.exists()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare pangenome summary metrics from two completed PhageFlow runs.")
    parser.add_argument("--left", default=None, type=Path, help="First completed PhageFlow output directory.")
    parser.add_argument("--right", default=None, type=Path, help="Second completed PhageFlow output directory.")
    parser.add_argument("--input", default=None, type=Path, help="Existing pangenome-sensitivity TSV to summarize or import.")
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-output", default=None, type=Path, help="Optional summary TSV output path.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional summary JSON output path.")
    parser.add_argument("--import-to-report", default=None, type=Path, help="Completed PhageFlow output directory whose 99_report/tables directory should receive the comparison and summary tables.")
    args = parser.parse_args()

    if args.input and (args.left or args.right):
        parser.error("use either --input or --left/--right, not both")
    if args.input:
        if not args.input.exists() or not args.input.is_file():
            parser.error(f"--input does not exist or is not a file: {args.input}")
        rows = read_comparison_rows(args.input)
    else:
        if not args.left or not args.right:
            parser.error("either --input or both --left and --right are required")
        for root in [args.left, args.right]:
            if not root.exists() or not root.is_dir():
                parser.error(f"run directory does not exist: {root}")
        rows = compare(args.left, args.right)

    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    elif not args.import_to_report:
        print(text, end="")
    summary_rows = summarize_rows(rows)
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(summary_rows_to_tsv(summary_rows))
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_for_json(rows), indent=2, sort_keys=True) + "\n")
    if args.import_to_report:
        if not args.import_to_report.exists() or not args.import_to_report.is_dir():
            parser.error(f"--import-to-report is not a directory: {args.import_to_report}")
        imported = import_to_report(args.import_to_report, rows)
        print(json.dumps({"imported": imported, "summary": summarize_for_json(rows)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
