#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from optional_tool_summary import (
    first_file_from_list,
    index_sample_artifacts,
    preferred_abricate_artifact,
    preferred_bacphlip_artifact,
    preferred_checkv_artifact,
    preferred_genomad_artifact,
    preferred_iphop_artifact,
    preferred_phabox_artifact,
    preferred_pharokka_artifact,
    preferred_phold_artifact,
    preferred_trnascan_artifact,
    read_samples,
    root_artifacts,
)


FIELDS = [
    "tool",
    "scope",
    "sample_id",
    "metric",
    "status",
    "value",
    "source_records",
    "source_columns",
    "limitation",
]

SAMPLE_TOOLS = ("trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "iphop", "phabox")
LIMITATIONS = {
    "trnascan": "tRNAscan-SE metric counts only; tRNA calls are not interpreted.",
    "bacphlip": "BACPHLIP metric counts only; lifecycle probabilities are not interpreted.",
    "checkv": "CheckV metric counts only; quality/completeness values are not interpreted.",
    "abricate": "ABRicate metric counts only; feature names and hits are not printed or interpreted.",
    "pharokka": "Pharokka metric counts only; gene or function annotations are not printed or interpreted.",
    "genomad": "geNomad metric counts only; classification and taxonomy values are not printed or interpreted.",
    "phold": "Phold metric counts only; structural annotation values are not printed or interpreted.",
    "iphop": "iPHoP metric counts only; host predictions are not interpreted as host-range evidence.",
    "phabox": "PhaBOX/PhaBOX2 metric counts only; taxonomy, lifestyle, host, and annotation values are not printed or interpreted.",
    "clinker": "clinker metric counts only; gene-order visualization is not interpreted.",
}


def delimited_rows(path: Path | None) -> tuple[list[dict[str, str]], list[str]]:
    if path is None or not path.exists() or path.is_dir() or path.stat().st_size == 0:
        return [], []
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    try:
        with path.open(newline="", errors="ignore") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = [dict(row) for row in reader]
            return rows, list(reader.fieldnames or [])
    except Exception:
        return [], []


def matching_columns(columns: list[str], patterns: list[str]) -> list[str]:
    found = []
    lowered = {column: column.lower().replace(" ", "_") for column in columns}
    for column, normalized in lowered.items():
        if any(pattern in normalized for pattern in patterns):
            found.append(column)
    return found


def nonempty_count(rows: list[dict[str, str]], columns: list[str]) -> int:
    if not rows or not columns:
        return 0
    return sum(1 for row in rows if any(str(row.get(column, "")).strip() for column in columns))


def add_metric(
    output: list[dict[str, str]],
    tool: str,
    sample_id: str,
    metric: str,
    value: int,
    source_records: int,
    source_columns: int,
    status: str = "available",
    scope: str = "sample",
) -> None:
    output.append(
        {
            "tool": tool,
            "scope": scope,
            "sample_id": sample_id,
            "metric": metric,
            "status": status,
            "value": str(value),
            "source_records": str(source_records),
            "source_columns": str(source_columns),
            "limitation": LIMITATIONS[tool],
        }
    )


def add_not_run(output: list[dict[str, str]], tool: str, sample_id: str) -> None:
    add_metric(output, tool, sample_id, "metrics_available", 0, 0, 0, status="not_run")


def table_metrics(
    output: list[dict[str, str]],
    tool: str,
    sample_id: str,
    artifact: Path | None,
    metric_name: str,
    field_patterns: dict[str, list[str]],
) -> None:
    if artifact is None or not artifact.exists():
        add_not_run(output, tool, sample_id)
        return
    rows, columns = delimited_rows(artifact)
    status = "available" if rows or columns else "available_no_table_rows"
    add_metric(output, tool, sample_id, metric_name, len(rows), len(rows), len(columns), status=status)
    for metric, patterns in field_patterns.items():
        add_metric(output, tool, sample_id, metric, nonempty_count(rows, matching_columns(columns, patterns)), len(rows), len(columns), status=status)


def log_metrics(output: list[dict[str, str]], tool: str, sample_id: str, artifact: Path | None) -> None:
    if artifact is None or not artifact.exists():
        add_not_run(output, tool, sample_id)
        return
    try:
        text = artifact.read_text(errors="ignore")
    except Exception:
        text = ""
    lines = [line for line in text.splitlines() if line.strip()]
    probabilities = re.findall(r"\b(?:0(?:\.\d+)?|1(?:\.0+)?)\b", text)
    add_metric(output, tool, sample_id, "nonempty_log_lines", len(lines), len(lines), 0)
    add_metric(output, tool, sample_id, "probability_values_detected", len(probabilities), len(lines), 0)


def metrics_for_tool(tool: str, sample_id: str, artifact: Path | None, log_path: Path | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if artifact is None and log_path is None:
        add_not_run(rows, tool, sample_id)
        return rows
    if tool == "trnascan":
        table_metrics(rows, tool, sample_id, preferred_trnascan_artifact(artifact) if artifact else None, "trna_records", {})
    elif tool == "bacphlip":
        log_metrics(rows, tool, sample_id, preferred_bacphlip_artifact(artifact) if artifact else None)
    elif tool == "checkv":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_checkv_artifact(artifact) if artifact else None,
            "quality_summary_records",
            {
                "completeness_values_detected": ["completeness"],
                "contamination_values_detected": ["contamination"],
                "quality_values_detected": ["quality"],
                "provirus_values_detected": ["provirus"],
            },
        )
    elif tool == "abricate":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_abricate_artifact(artifact) if artifact else None,
            "screen_records",
            {
                "identity_values_detected": ["identity", "%identity", "pct_identity"],
                "coverage_values_detected": ["coverage", "cov"],
            },
        )
    elif tool == "pharokka":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_pharokka_artifact(artifact) if artifact else None,
            "annotation_records",
            {
                "function_values_detected": ["function", "product", "annotation"],
                "phrog_values_detected": ["phrog"],
                "card_values_detected": ["card"],
                "vfdb_values_detected": ["vfdb", "virulence"],
            },
        )
    elif tool == "genomad":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_genomad_artifact(artifact, log_path) if artifact else log_path,
            "classification_records",
            {
                "taxonomy_values_detected": ["taxonomy", "taxid", "lineage"],
                "score_values_detected": ["score", "confidence"],
                "topology_values_detected": ["topology"],
                "hallmark_values_detected": ["hallmark"],
            },
        )
    elif tool == "phold":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_phold_artifact(artifact, log_path) if artifact else log_path,
            "structural_annotation_records",
            {
                "confidence_values_detected": ["confidence", "probability", "score"],
                "annotation_values_detected": ["annotation", "product", "function"],
            },
        )
    elif tool == "iphop":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_iphop_artifact(artifact, log_path) if artifact else log_path,
            "host_prediction_records",
            {
                "score_values_detected": ["score"],
                "confidence_values_detected": ["confidence"],
                "prediction_fields_detected": ["host", "prediction"],
            },
        )
    elif tool == "phabox":
        table_metrics(
            rows,
            tool,
            sample_id,
            preferred_phabox_artifact(artifact) if artifact else None,
            "phabox_records",
            {
                "taxonomy_fields_detected": ["taxonomy", "lineage", "taxon", "family", "genus"],
                "host_prediction_fields_detected": ["host"],
                "lifestyle_fields_detected": ["lifestyle", "temperate", "virulent"],
                "score_fields_detected": ["score", "confidence", "probability"],
                "contamination_fields_detected": ["contamination", "provirus"],
                "annotation_fields_detected": ["annotation", "function", "protein"],
            },
        )
    return rows


def collect_optional_metric_rows(
    samplesheet: Path | None,
    root: Path | None,
    trnascan_artifacts: list[Path],
    bacphlip_artifacts: list[Path],
    checkv_artifacts: list[Path],
    abricate_artifacts: list[Path],
    pharokka_artifacts: list[Path],
    genomad_artifacts: list[Path],
    genomad_logs: list[Path],
    phold_artifacts: list[Path],
    phold_logs: list[Path],
    iphop_artifacts: list[Path],
    iphop_logs: list[Path],
    phabox_artifacts: list[Path],
    clinker_artifacts: list[Path],
) -> list[dict[str, str]]:
    root = root.resolve() if root else None
    samples = read_samples(samplesheet, root)
    sample_artifacts = {
        "trnascan": index_sample_artifacts(trnascan_artifacts or (root_artifacts(root, "trnascan") if root else []), "trnascan"),
        "bacphlip": index_sample_artifacts(bacphlip_artifacts or (root_artifacts(root, "bacphlip") if root else []), "bacphlip"),
        "checkv": index_sample_artifacts(checkv_artifacts or (root_artifacts(root, "checkv") if root else []), "checkv"),
        "abricate": index_sample_artifacts(abricate_artifacts or (root_artifacts(root, "abricate") if root else []), "abricate"),
        "pharokka": index_sample_artifacts(pharokka_artifacts or (root_artifacts(root, "pharokka") if root else []), "pharokka"),
        "genomad": index_sample_artifacts(genomad_artifacts or (root_artifacts(root, "genomad") if root else []), "genomad"),
        "phold": index_sample_artifacts(phold_artifacts or (root_artifacts(root, "phold") if root else []), "phold"),
        "iphop": index_sample_artifacts(iphop_artifacts or (root_artifacts(root, "iphop") if root else []), "iphop"),
        "phabox": index_sample_artifacts(phabox_artifacts or (root_artifacts(root, "phabox") if root else []), "phabox"),
    }
    log_artifacts = {
        "genomad": index_sample_artifacts(genomad_logs, "genomad"),
        "phold": index_sample_artifacts(phold_logs, "phold"),
        "iphop": index_sample_artifacts(iphop_logs, "iphop"),
    }
    if not samples:
        detected = set()
        for items in sample_artifacts.values():
            detected.update(items)
        samples = sorted(detected)

    output: list[dict[str, str]] = []
    for sample_id in samples:
        for tool in SAMPLE_TOOLS:
            output.extend(metrics_for_tool(tool, sample_id, sample_artifacts[tool].get(sample_id), log_artifacts.get(tool, {}).get(sample_id)))

    output.extend(clinker_metrics(clinker_artifacts, root))
    return output


def clinker_metrics(paths: list[Path], root: Path | None) -> list[dict[str, str]]:
    if not paths and root:
        paths = root_artifacts(root, "clinker")
    by_name = {path.name: path for path in paths if path.exists()}
    html = by_name.get("clinker_synteny.html") or first_file_from_list(paths, [".html"])
    gbk_files = by_name.get("gbk_files.txt")
    output: list[dict[str, str]] = []
    if html is None and gbk_files is None:
        add_metric(output, "clinker", "COHORT", "metrics_available", 0, 0, 0, status="not_run", scope="cohort")
        return output
    input_count = 0
    if gbk_files and gbk_files.exists():
        input_count = sum(1 for line in gbk_files.read_text(errors="ignore").splitlines() if line.strip())
    html_bytes = html.stat().st_size if html and html.exists() else 0
    add_metric(output, "clinker", "COHORT", "genbank_inputs_listed", input_count, input_count, 0, scope="cohort")
    add_metric(output, "clinker", "COHORT", "html_bytes", html_bytes, 1 if html_bytes else 0, 0, scope="cohort")
    return output


def summarize_metric_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    available = [row for row in rows if row["status"] == "available"]
    return {
        "rows": len(rows),
        "tool_counts": dict(sorted(Counter(row["tool"] for row in rows).items())),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "available_metric_rows": len(available),
        "metrics": sorted({row["metric"] for row in rows}),
        "software_validation_conclusion": (
            "Optional-tool metric summary completed. The summary reports counts of stable "
            "high-level fields only and does not print or interpret optional-tool values."
        ),
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize optional-tool high-level metrics without printing annotation values.")
    parser.add_argument("--root", default=None, type=Path, help="Completed PhageFlow output directory.")
    parser.add_argument("--samplesheet", default=None, type=Path, help="Normalized samplesheet for expected sample IDs.")
    parser.add_argument("--trnascan-artifact", action="append", default=[], type=Path)
    parser.add_argument("--bacphlip-artifact", action="append", default=[], type=Path)
    parser.add_argument("--checkv-artifact", action="append", default=[], type=Path)
    parser.add_argument("--abricate-artifact", action="append", default=[], type=Path)
    parser.add_argument("--pharokka-artifact", action="append", default=[], type=Path)
    parser.add_argument("--genomad-artifact", action="append", default=[], type=Path)
    parser.add_argument("--genomad-log", action="append", default=[], type=Path)
    parser.add_argument("--phold-artifact", action="append", default=[], type=Path)
    parser.add_argument("--phold-log", action="append", default=[], type=Path)
    parser.add_argument("--iphop-artifact", action="append", default=[], type=Path)
    parser.add_argument("--iphop-log", action="append", default=[], type=Path)
    parser.add_argument("--phabox-artifact", action="append", default=[], type=Path)
    parser.add_argument("--clinker-artifact", action="append", default=[], type=Path)
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args()

    if args.root and (not args.root.exists() or not args.root.is_dir()):
        parser.error(f"--root is not a directory: {args.root}")

    rows = collect_optional_metric_rows(
        samplesheet=args.samplesheet,
        root=args.root,
        trnascan_artifacts=args.trnascan_artifact,
        bacphlip_artifacts=args.bacphlip_artifact,
        checkv_artifacts=args.checkv_artifact,
        abricate_artifacts=args.abricate_artifact,
        pharokka_artifacts=args.pharokka_artifact,
        genomad_artifacts=args.genomad_artifact,
        genomad_logs=args.genomad_log,
        phold_artifacts=args.phold_artifact,
        phold_logs=args.phold_log,
        iphop_artifacts=args.iphop_artifact,
        iphop_logs=args.iphop_log,
        phabox_artifacts=args.phabox_artifact,
        clinker_artifacts=args.clinker_artifact,
    )
    text = rows_to_tsv(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summarize_metric_rows(rows), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
