#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


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
                "limitation": "Completed-run pangenome metric comparison only; not a biological interpretation.",
            }
        )
    return rows


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare pangenome summary metrics from two completed PhageFlow runs.")
    parser.add_argument("--left", required=True, type=Path, help="First completed PhageFlow output directory.")
    parser.add_argument("--right", required=True, type=Path, help="Second completed PhageFlow output directory.")
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    args = parser.parse_args()

    for root in [args.left, args.right]:
        if not root.exists() or not root.is_dir():
            parser.error(f"run directory does not exist: {root}")

    text = rows_to_tsv(compare(args.left, args.right))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
