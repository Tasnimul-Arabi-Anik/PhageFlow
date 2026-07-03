#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BUILD_REPORT = REPO / "bin" / "build_report.py"


def load_build_report():
    spec = importlib.util.spec_from_file_location("build_report", BUILD_REPORT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_figure_manifest_regression(tmp_path: Path) -> None:
    build_report = load_build_report()
    report_dir = tmp_path / "99_report"
    figures_dir = report_dir / "figures"
    figures_dir.mkdir(parents=True)
    png = figures_dir / "cohort_similarity_heatmap.png"
    svg = figures_dir / "cohort_similarity_heatmap.svg"
    png.write_bytes(b"png-bytes\n")
    svg.write_bytes(b"svg-bytes\n")

    rows = build_report.figure_manifest_rows([str(svg), str(png)], report_dir)
    assert [row["extension"] for row in rows] == ["png", "svg"]
    assert rows[0]["figure_id"] == "FIG_001"
    assert rows[0]["relative_path"] == "figures/cohort_similarity_heatmap.png"
    assert rows[0]["bytes"] == str(png.stat().st_size)
    assert rows[0]["sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_figure_manifest_regression(Path(tmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
