#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_inventory import collect_artifact_summary
from functional_category_summary import collect_functional_category_rows, summarize_rows as summarize_functional_rows
from optional_tool_metrics import collect_optional_metric_rows, summarize_metric_rows
from optional_tool_summary import collect_optional_rows, summarize_rows as summarize_optional_rows
from pangenome_sensitivity import report_import_summary
from safety_summary import collect_safety_rows, summarize_safety_rows
from structural_summary import collect_structural_rows, summarize_structural_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a sanitized QA summary for a completed PhageFlow run.")
    parser.add_argument("--outdir", required=True, type=Path, help="Completed PhageFlow output directory.")
    parser.add_argument("--output", default=None, type=Path, help="Optional JSON output path. Defaults to stdout.")
    parser.add_argument("--compact", action="store_true", help="Write compact JSON instead of indented JSON.")
    args = parser.parse_args()

    if not args.outdir.exists() or not args.outdir.is_dir():
        parser.error(f"--outdir is not a directory: {args.outdir}")

    summary = collect_artifact_summary(args.outdir)
    summary["safety_screen_summary"] = summarize_safety_rows(collect_safety_rows(args.outdir))
    summary["structural_annotation_summary"] = summarize_structural_rows(collect_structural_rows(args.outdir))
    summary["optional_tool_summary"] = summarize_optional_rows(
        collect_optional_rows(
            samplesheet=None,
            root=args.outdir,
            trnascan_artifacts=[],
            bacphlip_artifacts=[],
            checkv_artifacts=[],
            abricate_artifacts=[],
            pharokka_artifacts=[],
            genomad_artifacts=[],
            genomad_logs=[],
            phold_artifacts=[],
            phold_logs=[],
            iphop_artifacts=[],
            iphop_logs=[],
            phabox_artifacts=[],
            clinker_artifacts=[],
        )
    )
    summary["optional_tool_metrics_summary"] = summarize_metric_rows(
        collect_optional_metric_rows(
            samplesheet=None,
            root=args.outdir,
            trnascan_artifacts=[],
            bacphlip_artifacts=[],
            checkv_artifacts=[],
            abricate_artifacts=[],
            pharokka_artifacts=[],
            genomad_artifacts=[],
            genomad_logs=[],
            phold_artifacts=[],
            phold_logs=[],
            iphop_artifacts=[],
            iphop_logs=[],
            phabox_artifacts=[],
            clinker_artifacts=[],
        )
    )
    summary["functional_category_summary"] = summarize_functional_rows(
        collect_functional_category_rows(samplesheet=None, root=args.outdir, pharokka_artifacts=[])
    )
    summary["pangenome_sensitivity_summary"] = report_import_summary(args.outdir)
    text = json.dumps(summary, sort_keys=True, separators=(",", ":")) if args.compact else json.dumps(summary, indent=2)
    text += "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
