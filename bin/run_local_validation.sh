#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT}/.." && pwd)"
cd "${PROJECT_ROOT}"

python3 -m py_compile phageflow/bin/*.py
nextflow run phageflow/main.nf -profile test --pangenome_method mmseqs --outdir phageflow_validation_mmseqs
python3 phageflow/bin/validate_phageflow_run.py --outdir phageflow_validation_mmseqs --require-pangenome-rows --expect-reference-context
nextflow run phageflow/main.nf -profile test --pangenome_method rbh_blastp --outdir phageflow_validation_rbh
python3 phageflow/bin/validate_phageflow_run.py --outdir phageflow_validation_rbh --require-pangenome-rows --expect-reference-context
nextflow run phageflow/main.nf --input phageflow/assets/test_data/toy_phage_a.fasta --pangenome_method none --outdir phageflow_validation_single
python3 phageflow/bin/validate_phageflow_run.py --outdir phageflow_validation_single
nextflow run phageflow/main.nf --input phageflow/assets/test_data/marker_tree_samplesheet.tsv --pangenome_method none --run_marker_tree true --marker_faa phageflow/assets/test_data/toy_marker_proteins.faa --marker_source marker_faa --marker_tree_engine simple --marker_bootstrap 0 --outdir phageflow_validation_marker_tree
python3 phageflow/bin/validate_phageflow_run.py --outdir phageflow_validation_marker_tree --expect-marker-tree
python3 phageflow/bin/summarize_run.py --outdir phageflow_validation_mmseqs --output /tmp/phageflow_validation_mmseqs_summary.json
python3 phageflow/bin/safety_summary.py --outdir phageflow_validation_mmseqs --output /tmp/phageflow_validation_mmseqs_safety.tsv --summary-json /tmp/phageflow_validation_mmseqs_safety.json
python3 phageflow/bin/optional_tool_summary.py --root phageflow_validation_mmseqs --output /tmp/phageflow_validation_mmseqs_optional.tsv --summary-json /tmp/phageflow_validation_mmseqs_optional.json
python3 phageflow/bin/structural_summary.py --outdir phageflow_validation_mmseqs --output /tmp/phageflow_validation_mmseqs_structural.tsv --summary-json /tmp/phageflow_validation_mmseqs_structural.json
python3 phageflow/bin/pangenome_sensitivity.py --left phageflow_validation_mmseqs --right phageflow_validation_rbh --output /tmp/phageflow_pangenome_sensitivity.tsv
python3 phageflow/bin/package_run.py --outdir phageflow_validation_mmseqs --output /tmp/phageflow_validation_mmseqs_package.tar.gz --force
