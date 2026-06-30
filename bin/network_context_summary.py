#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = ["source", "artifact", "metric", "value", "status", "limitation"]
LIMITATION = (
    "Completed-network context summary only. Counts describe imported network artifacts "
    "and do not assign taxonomy or interpret viral clusters."
)


def clean_cell(value: object) -> str:
    return " ".join(str(value or "").replace("\t", " ").split())


def find_first(root: Path, names: list[str], patterns: list[str]) -> Path | None:
    by_name = {path.name.lower(): path for path in root.rglob("*") if path.is_file()}
    for name in names:
        match = by_name.get(name.lower())
        if match:
            return match
    for pattern in patterns:
        matches = sorted(path for path in root.rglob(pattern) if path.is_file())
        if matches:
            return matches[0]
    return None


def read_delimited(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    try:
        with path.open(newline="", errors="ignore") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = [dict(row) for row in reader]
            return rows, list(reader.fieldnames or [])
    except Exception:
        return [], []


def add_row(rows: list[dict[str, str]], source: str, artifact: str, metric: str, value: int, status: str) -> None:
    rows.append(
        {
            "source": source,
            "artifact": artifact,
            "metric": metric,
            "value": str(value),
            "status": status,
            "limitation": LIMITATION,
        }
    )


def summarize_table(rows: list[dict[str, str]], source: str, artifact_name: str, path: Path | None, prefix: str) -> None:
    if path is None or not path.exists():
        add_row(rows, source, artifact_name, f"{prefix}_detected", 0, "missing")
        return
    records, columns = read_delimited(path)
    status = "available" if records or columns else "empty"
    add_row(rows, source, artifact_name, f"{prefix}_records", len(records), status)
    add_row(rows, source, artifact_name, f"{prefix}_columns", len(columns), status)
    cluster_columns = [
        column
        for column in columns
        if ("cluster" in column.lower() or column.lower().startswith("vc")) and "status" not in column.lower()
    ]
    add_row(rows, source, artifact_name, f"{prefix}_cluster_columns_detected", len(cluster_columns), status)
    cluster_values = {
        clean_cell(row.get(column))
        for row in records
        for column in cluster_columns
        if clean_cell(row.get(column))
    }
    add_row(rows, source, artifact_name, f"{prefix}_unique_cluster_values_detected", len(cluster_values), status)


def summarize_network(rows: list[dict[str, str]], source: str, path: Path | None) -> None:
    artifact = "network_edges"
    if path is None or not path.exists():
        add_row(rows, source, artifact, "network_detected", 0, "missing")
        return
    edges = 0
    nodes: set[str] = set()
    try:
        for line in path.read_text(errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.replace(",", "\t").split()
            if len(parts) >= 2:
                edges += 1
                nodes.add(parts[0])
                nodes.add(parts[1])
    except Exception:
        pass
    status = "available" if edges else "empty"
    add_row(rows, source, artifact, "network_edges", edges, status)
    add_row(rows, source, artifact, "network_nodes_detected", len(nodes), status)


def collect_network_rows(vcontact_dir: Path | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if vcontact_dir is None or not vcontact_dir.exists() or not vcontact_dir.is_dir():
        add_row(rows, "vcontact2", "input_dir", "network_context_detected", 0, "missing")
        return rows

    genome_overview = find_first(vcontact_dir, ["genome_by_genome_overview.csv"], ["*genome*overview*.csv", "*genome*overview*.tsv"])
    cluster_overview = find_first(vcontact_dir, ["viral_cluster_overview.csv"], ["*cluster*overview*.csv", "*cluster*overview*.tsv"])
    network_file = find_first(vcontact_dir, ["c1.ntw"], ["*.ntw", "*network*.tsv", "*network*.csv", "*edges*.tsv", "*edges*.csv"])
    summarize_table(rows, "vcontact2", "genome_by_genome_overview", genome_overview, "genome_overview")
    summarize_table(rows, "vcontact2", "viral_cluster_overview", cluster_overview, "cluster_overview")
    summarize_network(rows, "vcontact2", network_file)
    return rows


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "rows": len(rows),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "available_rows": sum(1 for row in rows if row["status"] == "available"),
        "software_validation_conclusion": LIMITATION,
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(clean_cell(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def summary_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Network Context Summary",
        "",
        "Imported network context counts only. PhageFlow does not assign taxonomy or interpret viral clusters from these imported artifacts.",
        "",
        "| source | artifact | metric | value | status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean_cell(row.get(field, "")) for field in ["source", "artifact", "metric", "value", "status"]) + " |")
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
        {"category": "table", "path": "tables/network_context_summary.tsv", "description": "Imported network-context artifact counts"},
        {"category": "report", "path": "network_context_report.md", "description": "Markdown imported network-context summary"},
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
    table = tables_dir / "network_context_summary.tsv"
    markdown = report_dir / "network_context_report.md"
    table.write_text(rows_to_tsv(rows))
    markdown.write_text(summary_markdown(rows))
    update_important_files(report_dir)
    return {"table": table.as_posix(), "markdown": markdown.as_posix()}


def report_import_summary(root: Path) -> dict[str, object]:
    path = root / "99_report" / "tables" / "network_context_summary.tsv"
    if not path.exists():
        summary = summarize_rows([])
        summary["detected"] = False
        return summary
    rows, _columns = read_delimited(path)
    summary = summarize_rows(rows)
    summary["detected"] = True
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize completed network-context outputs without assigning taxonomy.")
    parser.add_argument("--vcontact-dir", default=None, type=Path, help="Completed vConTACT2-style output directory.")
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    parser.add_argument("--import-to-report", default=None, type=Path, help="Completed PhageFlow output directory whose 99_report/tables directory should receive the network summary.")
    args = parser.parse_args()

    rows = collect_network_rows(args.vcontact_dir)
    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    elif not args.import_to_report:
        print(text, end="")
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_rows(rows), indent=2, sort_keys=True) + "\n")
    if args.import_to_report:
        if not args.import_to_report.exists() or not args.import_to_report.is_dir():
            parser.error(f"--import-to-report is not a directory: {args.import_to_report}")
        imported = import_to_report(args.import_to_report, rows)
        print(json.dumps({"imported": imported, "summary": summarize_rows(rows)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
