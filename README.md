# PhageFlow

[![CI](https://github.com/Tasnimul-Arabi-Anik/PhageFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/Tasnimul-Arabi-Anik/PhageFlow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Compact Nextflow workflow for reproducible in-silico analysis of already sequenced bacteriophage genomes.

PhageFlow now treats Nextflow as the single normal execution layer. The previous `../pangenome/` Snakemake workflow is retained only as a deprecated parity backend for one release; new runs should use native `mmseqs` or `rbh_blastp` pangenome methods.

## Current Status

PhageFlow is functionally complete and validated for the current lightweight single-genome and small-cohort genome-analysis scope. The first strict-validation milestone is `v0.1.0-validated`; the current repository state is `v0.2.0-dev`, which adds completed-run QA, packaging, provenance, and release-polish utilities on top of the validated core.

This is a software/workflow validation statement only. Biological interpretation, manuscript-grade conclusions, and project-specific claims remain outside the pipeline validation scope. See [`docs/validation_status.md`](docs/validation_status.md) for the validation evidence and boundaries, and [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for the release-state summary.

The proposed v0.2 extension plan is reviewed in [`docs/v0.2_extension_review.md`](docs/v0.2_extension_review.md). It prioritizes software-facing QA, packaging, and conservative artifact summaries before heavier optional analyses.
Current v0.2 progress is tracked in [`docs/v0.2_roadmap_status.md`](docs/v0.2_roadmap_status.md).
The v0.2 completion audit is in [`docs/v0.2_completion_audit.md`](docs/v0.2_completion_audit.md).
The next optional-analysis roadmap is in [`docs/v0.3_analysis_roadmap.md`](docs/v0.3_analysis_roadmap.md).

## What It Does

- Single phage genome characterization: input validation, genome QC, lightweight ORF prediction, codon usage, optional tRNA/lifecycle/quality/taxonomy/annotation/marker-tree modules, and report.
- Cohort comparative genomics: exact/near-duplicate screening, k-mer similarity, BLASTN intergenomic similarity, optional marker-gene phylogeny, MMseqs pangenome, and conservative RBH-BLASTP pangenome.
- Optional host context: linked host metadata plus phage-host GC/tetranucleotide composition comparison.
- PanResistome-style important reporting: `index.html`, high-resolution figures, downloadable key TSVs, software versions, parameters, runtime summary, important-files manifest, and validation manifest.

This workflow only processes existing sequence files and metadata. It does not perform wet-lab design, phage engineering, host-range expansion, synthesis, or virulence enhancement.


## Easiest Install and Run

For a beginner-friendly copy-paste walkthrough, see [`docs/quickstart.md`](docs/quickstart.md).
For optional publication modules and strict optional-output validation, see [`docs/optional_modules.md`](docs/optional_modules.md).

From this repository root, users can let PhageFlow install missing tools into a removable conda prefix and run the bundled validation data:

```bash
bash phageflow/install.sh
bash phageflow/bin/phageflow test
```

Install optional tool groups with one command when you want publication-level modules:

```bash
bash phageflow/bin/phageflow install --with publication
bash phageflow/bin/phageflow doctor --with publication
```

Optional install groups are `lite`, `publication`, `structure`, `phylogeny`, `host`, and `all`. These install executables only; large databases such as CheckV, Pharokka, geNomad, and Phold databases still need to be provided separately with the relevant workflow parameters.

Run a real phage genome with automatic tool detection/installation:

```bash
bash phageflow/bin/phageflow run --input my_phage.fasta --outdir results/my_phage
```

Use a custom removable environment location:

```bash
PHAGEFLOW_ENV_PREFIX=/path/to/removable/phageflow-env bash phageflow/bin/phageflow install
```

Check the active environment/tools:

```bash
bash phageflow/bin/phageflow doctor
```

Summarize or package a completed run without rerunning the workflow:

```bash
bash phageflow/bin/phageflow summarize --outdir results/my_phage --output results/my_phage_summary.json
bash phageflow/bin/phageflow package --outdir results/my_phage --output my_phage_phageflow_package.tar.gz
```

Summarize structural-annotation artifacts from a completed run or artifact directory:

```bash
bash phageflow/bin/phageflow structural-summary \
  --outdir results/my_phage \
  --output results/my_phage_structural_summary.tsv
```

Run the optional container smoke test when Docker is available:

```bash
bash phageflow/bin/phageflow container-smoke
```

Compare pangenome summaries from two completed runs:

```bash
bash phageflow/bin/phageflow pangenome-sensitivity \
  --left results/phage_cohort_mmseqs \
  --right results/phage_cohort_rbh \
  --output pangenome_sensitivity.tsv
```

## Inputs

The main input can be a FASTA file, a directory of FASTA files, or a tab-delimited samplesheet.

```text
sample_id	fasta	role	host_id	accession
phage_a	/path/to/phage_a.fasta	query	host_1	
phage_b	/path/to/phage_b.fasta	reference	host_2	NC_000000
```

Required columns: `sample_id`, `fasta`.

Optional columns: `role`, `host_id`, `accession`.

Optional host samplesheet:

```text
host_id	fasta	taxon	accession
host_1	/path/to/host.fasta	Salmonella enterica	GCF_000000000.1
```

When host context is supplied, PhageFlow reports GC/tetranucleotide composition plus host codon-adaptation and RSCU metrics. Optional CRISPR spacer matching can be enabled with an existing spacer FASTA:

```bash
bash phageflow/bin/phageflow install --with host
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --run_crispr_spacer_match true \
  --crispr_spacers host_spacers.fa \
  --outdir results/phage_host_context
```

## Main Commands

Bundled validation test with native MMseqs pangenome:

```bash
nextflow run phageflow/main.nf -profile test
python3 phageflow/bin/validate_phageflow_run.py --outdir phageflow_test_results --require-pangenome-rows
```

Single phage:

```bash
nextflow run phageflow/main.nf --input my_phage.fasta --outdir results/my_phage
```

User cohort with default MMseqs pangenome:

```bash
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/phage_cohort
```

Conservative RBH-BLASTP comparison backend:

```bash
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --pangenome_method rbh_blastp \
  --outdir results/phage_cohort_rbh
```

Optional host context:

```bash
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --outdir results/phage_host_context
```

Sanitized summary for a completed run:

```bash
bash phageflow/bin/phageflow summarize \
  --outdir results/phage_cohort \
  --output results/phage_cohort_artifact_summary.json
```

Shareable report/QA package for a completed run:

```bash
bash phageflow/bin/phageflow package \
  --outdir results/phage_cohort \
  --output phage_cohort_phageflow_package.tar.gz
```

Production-style optional modules:

```bash
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --run_trnascan true \
  --run_bacphlip true \
  --run_checkv true \
  --checkv_db /path/to/checkv-db-v1.5 \
  --run_pharokka true \
  --pharokka_db /path/to/pharokka_db \
  --outdir results/phage_publication
```

Publication-enrichment modules for stronger comparative papers:

```bash
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --run_genomad true \
  --genomad_db /path/to/genomad_db \
  --run_phold true \
  --run_clinker true \
  --pharokka_db /path/to/pharokka_db \
  --outdir results/phage_publication_enriched
```

`--run_phold true` and `--run_clinker true` automatically run Pharokka first because both modules need GenBank annotation output. Phold improves functional annotation using protein structural homology, while clinker creates comparative gene-order/synteny visualisations from annotated GenBank files.

Marker-gene phylogeny from user-supplied marker proteins:

```bash
bash phageflow/bin/phageflow install --with phylogeny
nextflow run phageflow/main.nf \
  --input phage_samplesheet.tsv \
  --run_marker_tree true \
  --marker_faa marker_proteins.faa \
  --marker_source marker_faa \
  --marker_tree_engine iqtree2 \
  --outdir results/phage_marker_tree
```

Marker FASTA headers should use `sample_id|marker_kind|gene_id`, for example `my_phage|terminase_large|terL_1`. Supported marker kinds are `terminase_large`, `portal`, and `major_capsid`.

## Output Modes

`--output_mode important` is the default and writes the practical publication/reporting bundle.

Supported values:

- `basic`: compact report contract.
- `important`: dashboard, figures, tables, manifests, and validation-ready outputs.
- `all`: reserved for future expanded outputs; currently follows the important contract.

## Important Outputs

Outputs are written under `--outdir`:

- `00_inputs/`: normalized samplesheet and input validation summary.
- `01_qc/fasta_stats/`: genome length, contig count, GC, N50, ambiguous-base summary, and conservative exact-terminal-repeat heuristics.
- `02_annotation/lightweight_orfs/`: dependency-light ORF predictions for smoke tests and scaffolding.
- `03_codon_usage/`: codon counts and genome-level coding summaries.
- `04_comparative/cohort_similarity/`: exact duplicate checks and k-mer Jaccard similarity.
- `04_comparative/intergenomic_similarity/`: BLASTN identity, reciprocal aligned-fraction, conservative similarity-score, similarity matrix, distance matrix, and method note.
- `04_comparative/marker_phylogeny/`: marker protein selection, alignments, Newick trees, topology consistency table, provenance table, and method note when enabled.
- `04_comparative/mmseqs_pangenome/`: default pangenome outputs.
- `04_comparative/rbh_blastp_pangenome/`: conservative RBH pangenome outputs.
- `05_optional/`: tRNAscan-SE, BACPHLIP, CheckV, ABRicate, Pharokka, geNomad, Phold, and clinker outputs when enabled.
- `06_host_context/`: host-linked nucleotide composition comparison.
- `99_report/index.html`: HTML dashboard.
- `99_report/figures/`: PNG, TIFF, PDF, and SVG figures.
- `99_report/tables/`: key downloadable TSV files.
- `99_report/tables/claim_evidence_matrix.tsv`: software claim-to-artifact evidence matrix with limitations.
- `99_report/tables/marker_provenance.tsv`: marker alignment/tree provenance table when marker-tree outputs are enabled.
- `99_report/important_files.tsv`: important output manifest.
- `99_report/validation_manifest.json`: report-level QA manifest.
- `99_report/software_versions.tsv`: software/runtime version capture.

## Pangenome Methods

`--pangenome_method mmseqs` is the recommended default. It scales better for larger cohorts and produces orthogroups, presence/absence matrix, genome metadata, and summary tables.

`--pangenome_method rbh_blastp` is the conservative reciprocal-best-hit backend ported from the previous Snakemake logic. Use it as a second pangenome method for sensitivity analysis, not as the default for large cohorts.

`--pangenome_method none` skips pangenome clustering and still builds QC, codon, cohort similarity, BLASTN intergenomic similarity, host-context, and report outputs.

`--pangenome_method legacy_snakemake_rbh` is deprecated and retained only for one-release parity checks with the older `../pangenome/` workflow. It is not required for normal PhageFlow runs.

## Validation

Run the complete local validation suite:

```bash
bash phageflow/bin/run_local_validation.sh
```

Or validate an existing run:

```bash
python3 phageflow/bin/validate_phageflow_run.py \
  --outdir phageflow_validation_mmseqs \
  --require-pangenome-rows
```

Validate expected optional outputs rigorously after an optional run:

```bash
python3 phageflow/bin/validate_phageflow_run.py \
  --outdir results/phage_publication_enriched \
  --require-pangenome-rows \
  --expect-publication-optionals \
  --expect-phold
```

The validator checks the dashboard, manifests, report tables, figure counts, TIFF outputs, BLASTN intergenomic similarity tables, marker-tree tables when present, pangenome presence/absence rows, and any optional modules explicitly requested with `--expect-optional`, `--expect-lite-optionals`, `--expect-publication-optionals`, or per-module flags such as `--expect-pharokka`; marker-tree runs can be checked with `--expect-marker-tree`.

Completed-run utilities:

```bash
bash phageflow/bin/phageflow summarize --outdir phageflow_validation_mmseqs --output /tmp/phageflow_summary.json
bash phageflow/bin/phageflow safety-summary --outdir phageflow_validation_mmseqs --output /tmp/phageflow_safety_summary.tsv
bash phageflow/bin/phageflow structural-summary --outdir phageflow_validation_mmseqs --output /tmp/phageflow_structural_summary.tsv
bash phageflow/bin/phageflow package --outdir phageflow_validation_mmseqs --output /tmp/phageflow_package.tar.gz
```

`summarize` reports sanitized artifact counts, anonymous TSV/figure IDs, file sizes, checksums, validation-manifest status, optional-screen artifact status, structural-artifact status, and generic PASS/FAIL/WARN/ERROR marker counts. `safety-summary` reports optional safety-related artifact presence and row counts without printing feature names. `structural-summary` reports structural-annotation artifact classes, table shapes, sizes, and checksums without printing annotation values. `package` creates a report/QA archive with relative paths, package checksums, optional-screen and structural summaries, and the sanitized artifact summary.

Compare completed pangenome runs:

```bash
bash phageflow/bin/phageflow pangenome-sensitivity \
  --left phageflow_validation_mmseqs \
  --right phageflow_validation_rbh \
  --output /tmp/phageflow_pangenome_sensitivity.tsv
```

This compares summary metrics only and does not interpret biological meaning.

## Containers and Conda

Use conda if you want a removable local environment:

```bash
nextflow run phageflow/main.nf -profile conda --input phage_samplesheet.tsv
```

Build Docker image:

```bash
docker build -t phageflow:latest -f phageflow/containers/Dockerfile phageflow
nextflow run phageflow/main.nf -profile docker --input phage_samplesheet.tsv
```

## Publication Note

The bundled lightweight ORF predictor exists to keep tests and scaffolding reproducible without heavy databases. For final manuscript-grade biology, run a consistent phage annotation backend such as Pharokka/PHANOTATE across every genome before interpreting pangenome content and marker selection.

## Citation, License, And Contributions

Use [`CITATION.cff`](CITATION.cff) for citation metadata. PhageFlow is distributed under the [`MIT License`](LICENSE).

Contribution guidance is in [`CONTRIBUTING.md`](CONTRIBUTING.md), release readiness checks are in [`docs/release_checklist.md`](docs/release_checklist.md), and security/data-boundary notes are in [`SECURITY.md`](SECURITY.md).
