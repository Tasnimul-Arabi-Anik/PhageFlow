#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from artifact_inventory import sha256_file


FIELDS = [
    "tool",
    "scope",
    "sample_id",
    "status",
    "artifact_count",
    "primary_artifact_id",
    "primary_artifact_type",
    "records",
    "columns",
    "bytes",
    "sha256",
    "limitation",
]

SAMPLE_TOOLS = ("trnascan", "bacphlip", "checkv", "abricate", "pharokka", "genomad", "phold", "iphop")
TOOL_SUFFIXES = {
    "trnascan": ".trnascan.tsv",
    "bacphlip": ".bacphlip.log",
    "checkv": ".checkv",
    "abricate": ".abricate.tsv",
    "pharokka": ".pharokka",
    "genomad": ".genomad",
    "phold": ".phold",
    "iphop": ".iphop",
}
LIMITATIONS = {
    "trnascan": "tRNAscan-SE artifact summary only; tRNA calls are not interpreted.",
    "bacphlip": "BACPHLIP artifact summary only; lifecycle probabilities are not interpreted.",
    "checkv": "CheckV artifact summary only; quality/completeness fields are not interpreted.",
    "abricate": "ABRicate artifact summary only; feature names and hits are not printed or interpreted.",
    "pharokka": "Pharokka artifact summary only; gene or function annotations are not printed or interpreted.",
    "genomad": "geNomad artifact summary only; classification and taxonomy values are not interpreted.",
    "phold": "Phold artifact summary only; structural annotation values are not printed or interpreted.",
    "iphop": "iPHoP artifact summary only; host-prediction values are not interpreted as host-range evidence.",
    "clinker": "clinker synteny artifact summary only; gene-order visualization is not interpreted.",
}


def read_samples(samplesheet: Path | None, root: Path | None) -> list[str]:
    candidates = []
    if samplesheet:
        candidates.append(samplesheet)
    if root:
        candidates.append(root / "00_inputs" / "samplesheet.normalized.tsv")
    for path in candidates:
        if path and path.exists():
            with path.open(newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                samples = [row.get("sample_id", "").strip() for row in reader if row.get("sample_id", "").strip()]
                if samples:
                    return samples
    return []


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


def line_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        with path.open(errors="ignore") as handle:
            return sum(1 for line in handle if line.strip())
    except Exception:
        return 0


def sample_from_artifact(path: Path, tool: str) -> str:
    name = path.name
    suffix = TOOL_SUFFIXES[tool]
    if name.endswith(suffix):
        return name[: -len(suffix)]
    if name.endswith(suffix + ".log"):
        return name[: -len(suffix + ".log")]
    return path.stem


def artifact_id(tool: str, index: int) -> str:
    return f"{tool.upper()}_{index:03d}"


def table_type(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if "quality_summary" in name:
        return "quality_summary"
    if "trnascan" in name and suffix in {".tsv", ".csv"}:
        return "trna_table"
    if "abricate" in name and suffix in {".tsv", ".csv"}:
        return "screen_table"
    if "cds_functions" in name:
        return "cds_functions_table"
    if "summary" in name and suffix in {".tsv", ".csv"}:
        return "summary_table"
    if "confidence" in name and suffix in {".tsv", ".csv"}:
        return "confidence_table"
    if "host" in name and suffix in {".tsv", ".csv"}:
        return "host_prediction_table"
    if suffix in {".gb", ".gbk"}:
        return "genbank"
    if suffix.startswith(".gff"):
        return "gff"
    if suffix == ".log":
        return "log"
    if suffix in {".tsv", ".csv"}:
        return "table"
    if suffix in {".html", ".htm"}:
        return "html"
    return "artifact"


def file_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return sum(1 for item in path.rglob("*") if item.is_file())


def preferred_checkv_artifact(path: Path) -> Path | None:
    candidate = path / "quality_summary.tsv"
    if candidate.exists():
        return candidate
    return first_file(path, ["*.tsv", "*.txt", "*.log"])


def preferred_trnascan_artifact(path: Path) -> Path | None:
    return first_file(path, ["*.trnascan.tsv", "*.tsv", "*.log"])


def preferred_bacphlip_artifact(path: Path) -> Path | None:
    return first_file(path, ["*.bacphlip.log", "*.log", "*.txt"])


def preferred_abricate_artifact(path: Path) -> Path | None:
    return first_file(path, ["*.abricate.tsv", "*.tsv", "*.csv", "*.log"])


def preferred_pharokka_artifact(path: Path) -> Path | None:
    patterns = ["**/*cds_functions*.tsv", "**/*.gbk", "**/*.gb", "**/*.gff", "**/*.gff3", "**/*.tsv", "**/*.log"]
    return first_file(path, patterns)


def preferred_genomad_artifact(path: Path, log_path: Path | None = None) -> Path | None:
    patterns = ["**/*summary*.tsv", "**/*virus*.tsv", "**/*plasmid*.tsv", "**/*.tsv", "**/*.log"]
    return first_file(path, patterns) or log_path


def preferred_phold_artifact(path: Path, log_path: Path | None = None) -> Path | None:
    patterns = ["**/*confidence*.tsv", "**/*per_cds*.tsv", "**/*all_cds*.tsv", "**/*.tsv", "**/*.gbk", "**/*.gff", "**/*.log"]
    return first_file(path, patterns) or log_path


def preferred_iphop_artifact(path: Path, log_path: Path | None = None) -> Path | None:
    patterns = [
        "**/*Host_prediction*.csv",
        "**/*host*prediction*.csv",
        "**/*host*.csv",
        "**/*host*.tsv",
        "**/*.csv",
        "**/*.tsv",
        "**/*.log",
    ]
    return first_file(path, patterns) or log_path


def first_file(path: Path, patterns: list[str]) -> Path | None:
    if path.is_file():
        return path
    for pattern in patterns:
        matches = sorted(item for item in path.glob(pattern) if item.is_file())
        if matches:
            return matches[0]
    return None


def summarize_sample_tool(tool: str, sample_id: str, artifact: Path | None, index: int, log_path: Path | None = None) -> dict[str, str]:
    if artifact is None or not artifact.exists():
        return {
            "tool": tool,
            "scope": "sample",
            "sample_id": sample_id,
            "status": "not_run",
            "artifact_count": "0",
            "primary_artifact_id": "",
            "primary_artifact_type": "",
            "records": "0",
            "columns": "0",
            "bytes": "0",
            "sha256": "",
            "limitation": LIMITATIONS[tool],
        }

    if tool == "trnascan":
        primary = preferred_trnascan_artifact(artifact)
    elif tool == "bacphlip":
        primary = preferred_bacphlip_artifact(artifact)
    elif tool == "checkv":
        primary = preferred_checkv_artifact(artifact)
    elif tool == "abricate":
        primary = preferred_abricate_artifact(artifact)
    elif tool == "pharokka":
        primary = preferred_pharokka_artifact(artifact)
    elif tool == "genomad":
        primary = preferred_genomad_artifact(artifact, log_path)
    elif tool == "phold":
        primary = preferred_phold_artifact(artifact, log_path)
    elif tool == "iphop":
        primary = preferred_iphop_artifact(artifact, log_path)
    else:
        primary = first_file(artifact, ["*"])

    count = file_count(artifact)
    if primary is None or not primary.exists():
        status = "empty_artifact" if count == 0 else "available_no_primary_table"
        return {
            "tool": tool,
            "scope": "sample",
            "sample_id": sample_id,
            "status": status,
            "artifact_count": str(count),
            "primary_artifact_id": "",
            "primary_artifact_type": "",
            "records": "0",
            "columns": "0",
            "bytes": "0",
            "sha256": "",
            "limitation": LIMITATIONS[tool],
        }

    records, columns = delimited_shape(primary) if primary.suffix.lower() in {".tsv", ".csv"} else (0, 0)
    return {
        "tool": tool,
        "scope": "sample",
        "sample_id": sample_id,
        "status": "available" if primary.stat().st_size > 0 else "empty_artifact",
        "artifact_count": str(count),
        "primary_artifact_id": artifact_id(tool, index),
        "primary_artifact_type": table_type(primary),
        "records": str(records),
        "columns": str(columns),
        "bytes": str(primary.stat().st_size),
        "sha256": sha256_file(primary),
        "limitation": LIMITATIONS[tool],
    }


def index_sample_artifacts(paths: list[Path], tool: str) -> dict[str, Path]:
    indexed: dict[str, Path] = {}
    for path in paths:
        indexed[sample_from_artifact(path, tool)] = path
    return indexed


def root_artifacts(root: Path, tool: str) -> list[Path]:
    optional_root = root / "05_optional" / ("clinker_synteny" if tool == "clinker" else tool)
    if not optional_root.exists():
        return []
    if tool == "clinker":
        return sorted(path for path in optional_root.iterdir() if path.is_file())
    if tool in {"trnascan", "bacphlip", "abricate"}:
        return sorted(path for path in optional_root.glob(f"*{TOOL_SUFFIXES[tool]}"))
    return sorted(path for path in optional_root.glob(f"*{TOOL_SUFFIXES[tool]}"))


def summarize_clinker(paths: list[Path], root: Path | None, index: int) -> dict[str, str]:
    if not paths and root:
        paths = root_artifacts(root, "clinker")
    by_name = {path.name: path for path in paths if path.exists()}
    html = by_name.get("clinker_synteny.html")
    gbk_files = by_name.get("gbk_files.txt")
    primary = html or first_file_from_list(paths, [".html", ".txt", ".md", ".log"])
    count = len([path for path in paths if path.exists() and path.is_file()])
    if primary is None:
        return {
            "tool": "clinker",
            "scope": "cohort",
            "sample_id": "COHORT",
            "status": "not_run",
            "artifact_count": "0",
            "primary_artifact_id": "",
            "primary_artifact_type": "",
            "records": "0",
            "columns": "0",
            "bytes": "0",
            "sha256": "",
            "limitation": LIMITATIONS["clinker"],
        }
    return {
        "tool": "clinker",
        "scope": "cohort",
        "sample_id": "COHORT",
        "status": "available" if primary.stat().st_size > 0 else "empty_artifact",
        "artifact_count": str(count),
        "primary_artifact_id": artifact_id("clinker", index),
        "primary_artifact_type": table_type(primary),
        "records": str(line_count(gbk_files)) if gbk_files else "0",
        "columns": "0",
        "bytes": str(primary.stat().st_size),
        "sha256": sha256_file(primary),
        "limitation": LIMITATIONS["clinker"],
    }


def first_file_from_list(paths: list[Path], suffixes: list[str]) -> Path | None:
    for suffix in suffixes:
        for path in sorted(paths):
            if path.exists() and path.is_file() and path.suffix.lower() == suffix:
                return path
    return None


def collect_optional_rows(
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

    rows: list[dict[str, str]] = []
    artifact_index = 1
    for sample_id in samples:
        for tool in SAMPLE_TOOLS:
            row = summarize_sample_tool(
                tool,
                sample_id,
                sample_artifacts[tool].get(sample_id),
                artifact_index,
                log_artifacts.get(tool, {}).get(sample_id),
            )
            rows.append(row)
            if row["primary_artifact_id"]:
                artifact_index += 1
    rows.append(summarize_clinker(clinker_artifacts, root, artifact_index))
    return rows


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "rows": len(rows),
        "tool_counts": dict(sorted(Counter(row["tool"] for row in rows).items())),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "available_tools": sorted({row["tool"] for row in rows if row["status"] == "available"}),
        "software_validation_conclusion": (
            "Optional-tool artifact summary completed. The summary reports artifact presence, "
            "shape, sizes, and checksums only; it does not interpret optional-tool biology."
        ),
    }


def rows_to_tsv(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in FIELDS))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize optional-tool PhageFlow artifacts without printing annotation values.")
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
    parser.add_argument("--clinker-artifact", action="append", default=[], type=Path)
    parser.add_argument("--output", default=None, type=Path, help="Optional TSV output path. Defaults to stdout.")
    parser.add_argument("--summary-json", default=None, type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args()

    if args.root and (not args.root.exists() or not args.root.is_dir()):
        parser.error(f"--root is not a directory: {args.root}")

    rows = collect_optional_rows(
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
        args.summary_json.write_text(json.dumps(summarize_rows(rows), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
