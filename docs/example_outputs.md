# Example Outputs

This guide shows what a successful PhageFlow run should produce in common use cases. It is meant to help users review result folders without reading every intermediate file.

All examples use placeholder paths. Replace input paths, output paths, and database paths with local files from your own project. PhageFlow outputs are software artifacts; they do not by themselves prove taxonomy, host range, infectivity, wet-lab outcome, or manuscript-grade biological conclusions.

## 1. Minimal Single-Genome Run

Use this when you have one assembled phage genome FASTA and want a compact report.

```bash
bash bin/phageflow run \
  --input my_phage.fasta \
  --pangenome_method none \
  --outdir results/my_phage
```

Expected top-level output folders:

```text
results/my_phage/00_inputs/
results/my_phage/01_qc/
results/my_phage/02_annotation/
results/my_phage/03_codon_usage/
results/my_phage/04_comparative/
results/my_phage/06_host_context/
results/my_phage/99_report/
```

Key report files:

```text
results/my_phage/99_report/index.html
results/my_phage/99_report/important_files.tsv
results/my_phage/99_report/software_versions.tsv
results/my_phage/99_report/runtime_summary.tsv
results/my_phage/99_report/validation_manifest.json
results/my_phage/99_report/tables/fasta_stats_combined.tsv
results/my_phage/99_report/tables/orf_summary_combined.tsv
results/my_phage/99_report/tables/codon_summary_combined.tsv
results/my_phage/99_report/tables/claim_evidence_matrix.tsv
results/my_phage/99_report/tables/figure_manifest.tsv
```

Recommended validation command:

```bash
bash bin/phageflow validate --outdir results/my_phage
```

Conservative interpretation boundary:

Use this output for input validation, genome statistics, lightweight ORF/codon summaries, and report QA. Do not use it as a standalone biological annotation or classification result.

## 2. Small Cohort Run

Use this when you have two or more related phage genomes and want local comparative outputs.

```bash
bash bin/phageflow run \
  --input phage_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/phage_cohort
```

Expected top-level output folders:

```text
results/phage_cohort/00_inputs/
results/phage_cohort/01_qc/
results/phage_cohort/02_annotation/
results/phage_cohort/03_codon_usage/
results/phage_cohort/04_comparative/
results/phage_cohort/06_host_context/
results/phage_cohort/99_report/
```

Key report files:

```text
results/phage_cohort/99_report/index.html
results/phage_cohort/99_report/tables/cohort_similarity_summary.tsv
results/phage_cohort/99_report/tables/cohort_pairwise_similarity.tsv
results/phage_cohort/99_report/tables/intergenomic_similarity_summary.tsv
results/phage_cohort/99_report/tables/intergenomic_similarity_pairs.tsv
results/phage_cohort/99_report/tables/intergenomic_similarity_matrix.tsv
results/phage_cohort/99_report/tables/intergenomic_distance_matrix.tsv
results/phage_cohort/99_report/tables/pangenome_summary.tsv
results/phage_cohort/99_report/tables/presence_absence.tsv
results/phage_cohort/99_report/figures/intergenomic_similarity_heatmap.tiff
results/phage_cohort/99_report/figures/pangenome_presence_absence_heatmap.tiff
```

Recommended validation command:

```bash
bash bin/phageflow validate \
  --outdir results/phage_cohort \
  --require-pangenome-rows
```

If the samplesheet includes rows marked `role=reference`, also require local reference-context outputs:

```bash
bash bin/phageflow validate \
  --outdir results/phage_cohort \
  --require-pangenome-rows \
  --expect-reference-context
```

Conservative interpretation boundary:

Use this output for local similarity, duplicate screening, pangenome method review, and reference-panel context. These tables are not public taxonomy assignment and are not a replacement for domain review.

## 3. Host-Context Run

Use this when phage samples have linked host metadata and a host samplesheet.

```bash
bash bin/phageflow run \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/phage_host_context
```

Expected top-level output folders:

```text
results/phage_host_context/00_inputs/
results/phage_host_context/04_comparative/
results/phage_host_context/06_host_context/
results/phage_host_context/99_report/
```

Key report files:

```text
results/phage_host_context/99_report/index.html
results/phage_host_context/99_report/tables/host_context.tsv
results/phage_host_context/99_report/tables/host_codon_adaptation.tsv
results/phage_host_context/99_report/tables/host_codon_rscu.tsv
results/phage_host_context/99_report/tables/crispr_spacer_summary.tsv
results/phage_host_context/99_report/figures/host_context_composition.tiff
results/phage_host_context/99_report/figures/host_codon_adaptation.tiff
```

Recommended validation command:

```bash
bash bin/phageflow validate \
  --outdir results/phage_host_context \
  --require-pangenome-rows
```

If host codon-adaptation outputs are expected to be populated:

```bash
bash bin/phageflow validate \
  --outdir results/phage_host_context \
  --require-pangenome-rows \
  --expect-host-adaptation
```

If CRISPR spacer matching was explicitly enabled and matches are expected:

```bash
bash bin/phageflow validate \
  --outdir results/phage_host_context \
  --expect-crispr-hits
```

Conservative interpretation boundary:

Use host-context outputs as composition and sequence-match context only. They do not prove host range, infectivity, or wet-lab compatibility.

## 4. Optional Publication-Style Run

Use this when optional tools and their local databases are already installed and you want heavier software artifacts in addition to the lightweight report.

First inspect or prepare databases outside the repository:

```bash
export PHAGEFLOW_DB_ROOT=/path/to/phageflow-db
bash bin/phageflow db status --tools publication,structure,host-prediction,integrated
bash bin/phageflow db run-args --tools publication,structure,host-prediction,integrated --shell
```

Then run Nextflow with the generated `--run_*` and `--*_db` arguments. A typical shape is:

```bash
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --outdir results/phage_publication \
  --run_checkv true \
  --checkv_db /path/to/checkv_db \
  --run_pharokka true \
  --pharokka_db /path/to/pharokka_db \
  --run_genomad true \
  --genomad_db /path/to/genomad_db
```

Expected top-level output folders:

```text
results/phage_publication/05_optional/
results/phage_publication/05_optional/checkv/
results/phage_publication/05_optional/pharokka/
results/phage_publication/05_optional/genomad/
results/phage_publication/05_optional/summary/
results/phage_publication/99_report/
```

Additional optional folders can appear when enabled:

```text
results/phage_publication/05_optional/phold/
results/phage_publication/05_optional/clinker_synteny/
results/phage_publication/05_optional/iphop/
results/phage_publication/05_optional/phabox/
```

Key report files:

```text
results/phage_publication/99_report/tables/optional_tool_summary.tsv
results/phage_publication/99_report/tables/optional_tool_metrics.tsv
results/phage_publication/99_report/tables/functional_category_summary.tsv
results/phage_publication/99_report/software_versions.tsv
results/phage_publication/99_report/important_files.tsv
```

Recommended validation command:

```bash
bash bin/phageflow validate \
  --outdir results/phage_publication \
  --require-pangenome-rows \
  --expect-publication-optionals
```

Add per-tool flags only for tools that were actually enabled:

```bash
bash bin/phageflow validate \
  --outdir results/phage_publication \
  --expect-phold \
  --expect-iphop \
  --expect-phabox
```

Conservative interpretation boundary:

Optional outputs are external-tool artifacts summarized by PhageFlow. PhageFlow records availability, shapes, checksums, broad counts, and provenance; it does not reinterpret annotation values, taxonomy labels, host predictions, lifecycle predictions, or safety-related hits.

## 5. Completed-Run Package

Use this after a workflow has already completed successfully and you want a shareable software QA bundle.

```bash
bash bin/phageflow summarize \
  --outdir results/phage_cohort \
  --output results/phage_cohort_summary.json

bash bin/phageflow package \
  --outdir results/phage_cohort \
  --output results/phage_cohort_phageflow_package.tar.gz
```

Expected package inputs:

```text
results/phage_cohort/99_report/index.html
results/phage_cohort/99_report/important_files.tsv
results/phage_cohort/99_report/software_versions.tsv
results/phage_cohort/99_report/runtime_summary.tsv
results/phage_cohort/99_report/tables/
results/phage_cohort/99_report/figures/
```

Recommended validation command before packaging:

```bash
bash bin/phageflow validate \
  --outdir results/phage_cohort \
  --require-pangenome-rows
```

Conservative interpretation boundary:

The package is a completed-run software artifact bundle. It is suitable for review of run structure, provenance, selected tables, figures, and validation reports. It does not turn workflow outputs into biological conclusions.

## 6. What Not To Conclude From The Outputs

Do not conclude any of the following from PhageFlow output alone:

- Host range, infectivity, or wet-lab outcome.
- Public taxonomy assignment or species demarcation.
- Therapeutic suitability, biosafety status, or regulatory status.
- Manuscript-grade biological conclusions without separate domain review.
- Correctness of external-tool predictions beyond the evidence and limitations of those tools.
- Superiority of one pangenome or similarity method without a documented validation design.

Use the report tables as reproducible software evidence. For biological interpretation, record input provenance, database versions, tool versions, parameters, and any independent validation evidence separately.

