# PhageFlow

[![CI](https://github.com/Tasnimul-Arabi-Anik/PhageFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/Tasnimul-Arabi-Anik/PhageFlow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Compact Nextflow workflow for reproducible in-silico analysis of already sequenced bacteriophage genomes.

PhageFlow now treats Nextflow as the single normal execution layer. The previous `../pangenome/` Snakemake workflow is retained only as a deprecated parity backend for one release; new runs should use native `mmseqs` or `rbh_blastp` pangenome methods.

## Current Status

PhageFlow is functionally complete and validated for the current lightweight single-genome and small-cohort genome-analysis scope. The current release state is `v0.3.0-validated`, which includes completed-run QA, packaging, provenance, optional-tool artifact summaries, local reference-context reporting, and release validation on top of the original validated core.

This is a software/workflow validation statement only. Biological interpretation, manuscript-grade conclusions, and project-specific claims remain outside the pipeline validation scope. See [`docs/validation_status.md`](docs/validation_status.md) for the validation evidence and boundaries, and [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for the release-state summary.

The v0.2 extension review, roadmap status, and completion audit are preserved in [`docs/v0.2_extension_review.md`](docs/v0.2_extension_review.md), [`docs/v0.2_roadmap_status.md`](docs/v0.2_roadmap_status.md), and [`docs/v0.2_completion_audit.md`](docs/v0.2_completion_audit.md). The v0.3 analysis roadmap is in [`docs/v0.3_analysis_roadmap.md`](docs/v0.3_analysis_roadmap.md); the active v0.4 lightweight/heavy expansion audit, capability matrix, and progress notes are in [`docs/v0.4_analysis_expansion_audit.md`](docs/v0.4_analysis_expansion_audit.md), [`docs/analysis_capability_matrix.md`](docs/analysis_capability_matrix.md), and [`docs/v0.4_progress.md`](docs/v0.4_progress.md).

## What It Does

- Single phage genome characterization: input validation, genome QC, lightweight ORF prediction, codon usage, optional tRNA/lifecycle/quality/taxonomy/annotation/marker-tree modules, and report.
- Cohort comparative genomics: exact/near-duplicate screening, k-mer similarity, BLASTN intergenomic similarity, optional marker-gene phylogeny, MMseqs pangenome, and conservative RBH-BLASTP pangenome.
- Optional host context: linked host metadata plus phage-host GC/tetranucleotide composition comparison, optional spacer matching, and optional iPHoP host-prediction artifacts.
- PanResistome-style important reporting: `index.html`, high-resolution figures, downloadable key TSVs, software versions, parameters, runtime summary, important-files manifest, and validation manifest.

This workflow only processes existing sequence files and metadata. It does not perform wet-lab design, phage engineering, host-range expansion, synthesis, or virulence enhancement.


## Easiest Install and Run

For a beginner-friendly copy-paste walkthrough, see [`docs/quickstart.md`](docs/quickstart.md).
For optional publication modules and strict optional-output validation, see [`docs/optional_modules.md`](docs/optional_modules.md).

Clone the repository and work from the clone root:

```bash
git clone https://github.com/Tasnimul-Arabi-Anik/PhageFlow.git
cd PhageFlow
```

From this repository root, users can let PhageFlow install missing tools into a removable conda prefix and run the bundled validation data:

```bash
bash install.sh
bash bin/phageflow test
```

Install optional tool groups with one command when you want publication-level modules:

```bash
bash bin/phageflow install --with publication
bash bin/phageflow doctor --with publication
```

Optional install groups are `lite`, `publication`, `structure`, `phylogeny`, `host`, `host-prediction`, and `all`. These install executables only; large databases such as CheckV, Pharokka, geNomad, Phold, and iPHoP databases still need to be provided separately with the relevant workflow parameters.

Run a real phage genome with automatic tool detection/installation:

```bash
bash bin/phageflow run --input my_phage.fasta --outdir results/my_phage
```

Use a custom removable environment location:

```bash
PHAGEFLOW_ENV_PREFIX=/path/to/removable/phageflow-env bash bin/phageflow install
```

Check the active environment/tools:

```bash
bash bin/phageflow doctor
```

Summarize or package a completed run without rerunning the workflow:

```bash
bash bin/phageflow summarize --outdir results/my_phage --output results/my_phage_summary.json
bash bin/phageflow package --outdir results/my_phage --output my_phage_phageflow_package.tar.gz
```

Summarize structural-annotation artifacts from a completed run or artifact directory:

```bash
bash bin/phageflow structural-summary \
  --outdir results/my_phage \
  --output results/my_phage_structural_summary.tsv
```

Summarize optional-tool artifacts without rerunning the workflow:

```bash
bash bin/phageflow optional-summary \
  --root results/my_phage \
  --output results/my_phage_optional_tool_summary.tsv

bash bin/phageflow optional-metrics \
  --root results/my_phage \
  --output results/my_phage_optional_tool_metrics.tsv
```

Run the optional container smoke test when Docker is available:

```bash
bash bin/phageflow container-smoke
```

Compare pangenome summaries from two completed runs:

```bash
bash bin/phageflow pangenome-sensitivity \
  --left results/phage_cohort_mmseqs \
  --right results/phage_cohort_rbh \
  --output pangenome_sensitivity.tsv \
  --summary-output pangenome_sensitivity_summary.tsv \
  --import-to-report results/phage_cohort_mmseqs
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

Rows with `role=reference` are treated as a local reference panel. PhageFlow compares non-reference rows against those local references and reports nearest-reference metrics, duplicate flags, and method limitations in `99_report/tables/reference_context_*.tsv`. This is local context only; it is not live public database discovery or taxonomy assignment.

Optional host samplesheet:

```text
host_id	fasta	taxon	accession
host_1	/path/to/host.fasta	Salmonella enterica	GCF_000000000.1
```

When host context is supplied, PhageFlow reports GC/tetranucleotide composition plus host codon-adaptation and RSCU metrics. Optional CRISPR spacer matching can be enabled with an existing spacer FASTA:

```bash
bash bin/phageflow install --with host
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --run_crispr_spacer_match true \
  --crispr_spacers host_spacers.fa \
  --outdir results/phage_host_context
```

## Main Commands

Bundled validation test with native MMseqs pangenome:

```bash
nextflow run main.nf -profile test
python3 bin/validate_phageflow_run.py --outdir phageflow_test_results --require-pangenome-rows --expect-reference-context
```

Single phage:

```bash
nextflow run main.nf --input my_phage.fasta --outdir results/my_phage
```

User cohort with default MMseqs pangenome:

```bash
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/phage_cohort
```

Conservative RBH-BLASTP comparison backend:

```bash
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --pangenome_method rbh_blastp \
  --outdir results/phage_cohort_rbh
```

Optional host context:

```bash
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --outdir results/phage_host_context
```

Sanitized summary for a completed run:

```bash
bash bin/phageflow summarize \
  --outdir results/phage_cohort \
  --output results/phage_cohort_artifact_summary.json
```

Shareable report/QA package for a completed run:

```bash
bash bin/phageflow package \
  --outdir results/phage_cohort \
  --output phage_cohort_phageflow_package.tar.gz
```

Production-style optional modules:

```bash
nextflow run main.nf \
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
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --run_genomad true \
  --genomad_db /path/to/genomad_db \
  --run_phold true \
  --run_clinker true \
  --pharokka_db /path/to/pharokka_db \
  --outdir results/phage_publication_enriched
```

`--run_phold true` and `--run_clinker true` automatically run Pharokka first because both modules need GenBank annotation output. Phold improves functional annotation using protein structural homology, while clinker creates comparative gene-order/synteny visualisations from annotated GenBank files.

Optional database-backed host prediction:

```bash
bash bin/phageflow install --with host-prediction
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --run_iphop true \
  --iphop_db /path/to/iphop_db \
  --outdir results/phage_iphop
```

iPHoP outputs are summarized as optional artifacts only. Treat predicted-host evidence as computational context, not host-range proof.

Marker-gene phylogeny from user-supplied marker proteins:

```bash
bash bin/phageflow install --with phylogeny
nextflow run main.nf \
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
- `01_qc/fasta_stats/`: genome length, contig count, GC, GC/AT skew, N50, ambiguous-base summary, homopolymer/N-run metrics, and conservative exact-terminal-repeat heuristics.
- `02_annotation/lightweight_orfs/`: dependency-light ORF predictions plus coding-density, strand-balance, ORF-density, and ORF-length summaries for smoke tests and scaffolding.
- `03_codon_usage/`: codon counts and genome-level coding summaries.
- `04_comparative/cohort_similarity/`: exact duplicate checks and k-mer Jaccard similarity.
- `04_comparative/intergenomic_similarity/`: BLASTN identity, reciprocal aligned-fraction, conservative similarity-score, similarity matrix, distance matrix, and method note.
- `04_comparative/marker_phylogeny/`: marker protein selection, alignments, Newick trees, topology consistency table, provenance table, and method note when enabled.
- `04_comparative/mmseqs_pangenome/`: default pangenome outputs.
- `04_comparative/rbh_blastp_pangenome/`: conservative RBH pangenome outputs.
- `05_optional/`: tRNAscan-SE, BACPHLIP, CheckV, ABRicate, Pharokka, geNomad, Phold, clinker, and iPHoP outputs when enabled; PhaBOX/PhaBOX2 outputs can be summarized when imported or copied into `05_optional/phabox/`.
- `06_host_context/`: host-linked nucleotide composition comparison.
- `99_report/index.html`: HTML dashboard.
- `99_report/figures/`: PNG, TIFF, PDF, and SVG figures.
- `99_report/tables/`: key downloadable TSV files.
- `99_report/tables/claim_evidence_matrix.tsv`: software claim-to-artifact evidence matrix with limitations.
- `99_report/tables/marker_provenance.tsv`: marker alignment/tree provenance table when marker-tree outputs are enabled.
- `99_report/tables/optional_tool_summary.tsv`: optional tRNAscan-SE/BACPHLIP/ABRicate/CheckV/Pharokka/geNomad/Phold/clinker/iPHoP/PhaBOX artifact status, table shapes, sizes, and checksums.
- `99_report/tables/optional_tool_metrics.tsv`: compact optional-tool metric counts from stable high-level outputs without printing annotation, taxonomy, host-prediction, or feature values.
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
bash bin/run_local_validation.sh
```

Or validate an existing run:

```bash
python3 bin/validate_phageflow_run.py \
  --outdir phageflow_validation_mmseqs \
  --require-pangenome-rows \
  --expect-reference-context
```

Validate expected optional outputs rigorously after an optional run:

```bash
python3 bin/validate_phageflow_run.py \
  --outdir results/phage_publication_enriched \
  --require-pangenome-rows \
  --expect-publication-optionals \
  --expect-phold
```

The validator checks the dashboard, manifests, report tables, figure counts, TIFF outputs, BLASTN intergenomic similarity tables, local reference-context tables when requested with `--expect-reference-context`, marker-tree tables when present, pangenome presence/absence rows, and any optional modules explicitly requested with `--expect-optional`, `--expect-lite-optionals`, `--expect-publication-optionals`, or per-module flags such as `--expect-pharokka`; marker-tree runs can be checked with `--expect-marker-tree`. Expected optional modules also require matching rows in `99_report/tables/optional_tool_summary.tsv` and `99_report/tables/optional_tool_metrics.tsv`.

Completed-run utilities:

```bash
bash bin/phageflow summarize --outdir phageflow_validation_mmseqs --output /tmp/phageflow_summary.json
bash bin/phageflow safety-summary --outdir phageflow_validation_mmseqs --output /tmp/phageflow_safety_summary.tsv
bash bin/phageflow optional-summary --root phageflow_validation_mmseqs --output /tmp/phageflow_optional_tool_summary.tsv
bash bin/phageflow optional-metrics --root phageflow_validation_mmseqs --output /tmp/phageflow_optional_tool_metrics.tsv
bash bin/phageflow structural-summary --outdir phageflow_validation_mmseqs --output /tmp/phageflow_structural_summary.tsv
bash bin/phageflow package --outdir phageflow_validation_mmseqs --output /tmp/phageflow_package.tar.gz
```

`summarize` reports sanitized artifact counts, anonymous TSV/figure IDs, file sizes, checksums, validation-manifest status, optional-screen artifact status, optional-tool artifact status, optional-tool metric status, imported pangenome-sensitivity status, structural-artifact status, and generic PASS/FAIL/WARN/ERROR marker counts. `safety-summary` reports optional safety-related artifact presence and row counts without printing feature names. `optional-summary` reports optional-tool artifact presence, table shapes, sizes, and checksums without printing annotation values. `optional-metrics` reports compact high-level metric counts without printing annotation, taxonomy, host-prediction, or feature values. `structural-summary` reports structural-annotation artifact classes, table shapes, sizes, and checksums without printing annotation values. `package` creates a report/QA archive with relative paths, package checksums, optional-screen, optional-tool, optional-metric, pangenome-sensitivity, and structural summaries, and the sanitized artifact summary.

Compare completed pangenome runs:

```bash
bash bin/phageflow pangenome-sensitivity \
  --left phageflow_validation_mmseqs \
  --right phageflow_validation_rbh \
  --output /tmp/phageflow_pangenome_sensitivity.tsv \
  --summary-output /tmp/phageflow_pangenome_sensitivity_summary.tsv \
  --import-to-report phageflow_validation_mmseqs
```

This compares summary metrics only and does not interpret biological meaning. When `--import-to-report` is supplied, PhageFlow writes `99_report/tables/pangenome_sensitivity.tsv`, `99_report/tables/pangenome_sensitivity_summary.tsv`, and `99_report/pangenome_sensitivity_report.md` into the selected completed run; `summarize` and `package` then include the imported sensitivity status.

## Containers and Conda

Use conda if you want a removable local environment:

```bash
nextflow run main.nf -profile conda --input phage_samplesheet.tsv
```

Build Docker image:

```bash
docker build -t phageflow:latest -f containers/Dockerfile .
nextflow run main.nf -profile docker --input phage_samplesheet.tsv
```

## Publication Note

The bundled lightweight ORF predictor exists to keep tests and scaffolding reproducible without heavy databases. For final manuscript-grade biology, run a consistent phage annotation backend such as Pharokka/PHANOTATE across every genome before interpreting pangenome content and marker selection.

## Citation, License, And Contributions

Use [`CITATION.cff`](CITATION.cff) for citation metadata. PhageFlow is distributed under the [`MIT License`](LICENSE).

Contribution guidance is in [`CONTRIBUTING.md`](CONTRIBUTING.md), release readiness checks are in [`docs/release_checklist.md`](docs/release_checklist.md), and security/data-boundary notes are in [`SECURITY.md`](SECURITY.md).
