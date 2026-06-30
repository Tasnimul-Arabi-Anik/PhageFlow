#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


FIGURE_EXTS = {".png", ".svg", ".pdf", ".jpg", ".jpeg", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".tsv", ".csv", ".log", ".md", ".json", ".yaml", ".yml"}
REPORT_LIKE_TOKENS = ("report", "log", "version", "manifest", "checksum", "md5", "sha")
MARKERS = ("PASS", "FAIL", "WARN", "ERROR")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tsv_shape(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        first = handle.readline().rstrip(b"\r\n")
        if not first:
            return 0, 0
        rows_total = 1 + sum(1 for _ in handle)
    return max(rows_total - 1, 0), len(first.split(b"\t"))


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


def validator_status(root: Path) -> dict[str, int | str | bool]:
    report = root / "99_report" / "phageflow_validation_report.tsv"
    status = {"detected": report.exists(), "PASS": 0, "FAIL": 0, "WARN": 0, "ERROR": 0}
    if not report.exists():
        return status
    with report.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            value = (row.get("status") or "").upper()
            if value in status:
                status[value] = int(status[value]) + 1
    return status


def manifest_status(root: Path) -> dict[str, str | bool]:
    manifest = root / "99_report" / "validation_manifest.json"
    if not manifest.exists():
        return {"detected": False}
    try:
        data = json.loads(manifest.read_text())
    except Exception as exc:
        return {"detected": True, "parse_error": exc.__class__.__name__}
    return {
        "detected": True,
        "report_complete": bool(data.get("report_complete")),
        "output_mode": str(data.get("output_mode", "")),
        "pangenome_method": str(data.get("pangenome_method", "")),
        "intergenomic_status": str(data.get("intergenomic_status", "")),
        "marker_status": str(data.get("marker_status", "")),
        "crispr_status": str(data.get("crispr_status", "")),
    }


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def collect_artifact_summary(root: Path) -> dict[str, object]:
    root = root.resolve()
    files = iter_files(root) if root.exists() and root.is_dir() else []
    tsv_artifacts = []
    figure_artifacts = []
    marker_counts = {marker: 0 for marker in MARKERS}
    text_like_count = 0
    report_like_count = 0

    for path in files:
        suffix = path.suffix.lower()
        name = path.name.lower()
        stat = path.stat()

        if suffix == ".tsv":
            rows, columns = tsv_shape(path)
            tsv_artifacts.append(
                {
                    "id": f"TSV_{len(tsv_artifacts) + 1:03d}",
                    "rows": rows,
                    "columns": columns,
                    "bytes": stat.st_size,
                    "sha256": sha256_file(path),
                }
            )

        if suffix in FIGURE_EXTS:
            figure_artifacts.append(
                {
                    "id": f"FIG_{len(figure_artifacts) + 1:03d}",
                    "extension": suffix,
                    "bytes": stat.st_size,
                    "sha256": sha256_file(path),
                }
            )

        if any(token in name for token in REPORT_LIKE_TOKENS):
            report_like_count += 1

        if suffix in TEXT_EXTS:
            text_like_count += 1
            try:
                upper = path.read_text(errors="ignore").upper()
            except Exception:
                continue
            for marker in MARKERS:
                marker_counts[marker] += len(re.findall(rf"\b{marker}\b", upper))

    return {
        "result_directory_detected": bool(files),
        "result_directory_id": "RESULT_001" if files else "",
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "tsv_count": len(tsv_artifacts),
        "figure_count": len(figure_artifacts),
        "text_like_file_count": text_like_count,
        "report_log_version_manifest_checksum_like_file_count": report_like_count,
        "generic_marker_counts": marker_counts,
        "validation_manifest": manifest_status(root),
        "validator_report": validator_status(root),
        "tsv_artifacts": tsv_artifacts,
        "figure_artifacts": figure_artifacts,
        "software_validation_conclusion": (
            "Sanitized artifact QA completed. This summary describes software artifacts "
            "only and does not provide biological interpretation."
        ),
    }


def default_package_files(root: Path, include_logs: bool = False) -> list[Path]:
    root = root.resolve()
    selected: set[Path] = set()
    report_dir = root / "99_report"
    if report_dir.exists():
        selected.update(path for path in report_dir.rglob("*") if path.is_file())
    validation_summary = root / "00_inputs" / "validation_summary.tsv"
    if validation_summary.exists():
        selected.add(validation_summary)
    if include_logs:
        selected.update(path for path in root.rglob("*.log") if path.is_file())
    return sorted(selected)


def checksum_rows(root: Path, files: Iterable[Path]) -> list[dict[str, str]]:
    rows = []
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        rows.append({"relative_path": rel, "bytes": str(path.stat().st_size), "sha256": sha256_file(path)})
    return rows


def rows_to_tsv(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    lines = ["\t".join(fieldnames)]
    for row in rows:
        lines.append("\t".join(str(row.get(field, "")) for field in fieldnames))
    return "\n".join(lines) + "\n"
