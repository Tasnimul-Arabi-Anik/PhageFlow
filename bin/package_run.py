#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import tarfile
from pathlib import Path

from artifact_inventory import collect_artifact_summary, checksum_rows, default_package_files, rows_to_tsv
from optional_tool_summary import collect_optional_rows, rows_to_tsv as optional_rows_to_tsv
from safety_summary import collect_safety_rows, rows_to_tsv as safety_rows_to_tsv
from structural_summary import collect_structural_rows, rows_to_tsv as structural_rows_to_tsv


def add_text(tar: tarfile.TarFile, archive_name: str, text: str) -> None:
    data = text.encode()
    info = tarfile.TarInfo(archive_name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser(description="Package selected PhageFlow report/QA artifacts into a tar.gz archive.")
    parser.add_argument("--outdir", required=True, type=Path, help="Completed PhageFlow output directory.")
    parser.add_argument("--output", default=None, type=Path, help="Output .tar.gz path. Defaults to <outdir-name>_phageflow_package.tar.gz.")
    parser.add_argument("--include-logs", action="store_true", help="Include .log files from the completed output directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output archive.")
    args = parser.parse_args()

    root = args.outdir.resolve()
    if not root.exists() or not root.is_dir():
        parser.error(f"--outdir is not a directory: {args.outdir}")

    output = args.output or Path(f"{root.name}_phageflow_package.tar.gz")
    if output.exists() and not args.force:
        parser.error(f"output archive already exists: {output} (use --force to overwrite)")
    output.parent.mkdir(parents=True, exist_ok=True)

    files = default_package_files(root, include_logs=args.include_logs)
    summary = collect_artifact_summary(root)
    checksums = checksum_rows(root, files)
    safety_rows = collect_safety_rows(root)
    structural_rows = collect_structural_rows(root)
    optional_rows = collect_optional_rows(
        samplesheet=None,
        root=root,
        checkv_artifacts=[],
        pharokka_artifacts=[],
        genomad_artifacts=[],
        genomad_logs=[],
        phold_artifacts=[],
        phold_logs=[],
        clinker_artifacts=[],
    )
    summary["safety_screen_summary"] = {
        "rows": len(safety_rows),
        "statuses": sorted({row["status"] for row in safety_rows}),
    }
    summary["structural_annotation_summary"] = {
        "rows": len(structural_rows),
        "statuses": sorted({row["status"] for row in structural_rows}),
    }
    summary["optional_tool_summary"] = {
        "rows": len(optional_rows),
        "statuses": sorted({row["status"] for row in optional_rows}),
        "available_tools": sorted({row["tool"] for row in optional_rows if row["status"] == "available"}),
    }
    prefix = "phageflow_package"

    with tarfile.open(output, "w:gz") as tar:
        for path in files:
            rel = path.relative_to(root).as_posix()
            tar.add(path, arcname=f"{prefix}/{rel}", recursive=False)
        add_text(tar, f"{prefix}/phageflow_artifact_summary.json", json.dumps(summary, indent=2) + "\n")
        add_text(tar, f"{prefix}/phageflow_package_checksums.tsv", rows_to_tsv(checksums, ["relative_path", "bytes", "sha256"]))
        add_text(tar, f"{prefix}/phageflow_safety_summary.tsv", safety_rows_to_tsv(safety_rows))
        add_text(tar, f"{prefix}/phageflow_structural_summary.tsv", structural_rows_to_tsv(structural_rows))
        add_text(tar, f"{prefix}/phageflow_optional_tool_summary.tsv", optional_rows_to_tsv(optional_rows))

    print(f"PhageFlow package written: {output}")
    print(f"Packaged files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
