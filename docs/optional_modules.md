# Optional Module Installation And Validation

PhageFlow keeps the default environment small. Optional publication modules can be installed into the same removable conda prefix when needed.

## Simple Install Commands

```bash
bash phageflow/bin/phageflow install --with lite
bash phageflow/bin/phageflow install --with publication
bash phageflow/bin/phageflow install --with structure
bash phageflow/bin/phageflow install --with phylogeny
bash phageflow/bin/phageflow install --with host
bash phageflow/bin/phageflow install --with all
```

Groups:

- `lite`: tRNAscan-SE, BACPHLIP, ABRicate.
- `publication`: `lite` plus CheckV, Pharokka, geNomad, and clinker.
- `structure`: Phold.
- `phylogeny`: MAFFT, IQ-TREE, trimAl, and Biopython for marker-gene trees.
- `host`: Prodigal and minced for optional host-context enrichment.
- `all`: `publication` plus `structure`, `phylogeny`, and `host`.

The installer handles executables only. Database-heavy tools still require user-provided database paths, for example `--checkv_db`, `--pharokka_db`, and `--genomad_db`.

## Doctor Checks

```bash
bash phageflow/bin/phageflow doctor --with publication
bash phageflow/bin/phageflow doctor --with phylogeny
bash phageflow/bin/phageflow doctor --with host
bash phageflow/bin/phageflow doctor --with all
```

The doctor command reports whether the expected optional executables are visible in the active PhageFlow environment.

## Rigorous Optional Output Validation

After an optional run, validate only the optional modules that were expected to run:

```bash
bash phageflow/bin/phageflow validate \
  --outdir results/phage_publication \
  --require-pangenome-rows \
  --expect-publication-optionals
```

For Phold in addition to the publication group:

```bash
bash phageflow/bin/phageflow validate \
  --outdir results/phage_publication_structure \
  --require-pangenome-rows \
  --expect-publication-optionals \
  --expect-phold
```


Validate marker-gene phylogeny outputs when `--run_marker_tree true` was used:

```bash
bash phageflow/bin/phageflow validate \
  --outdir results/phage_marker_tree \
  --expect-marker-tree
```

Validate host codon-adaptation and CRISPR spacer matching outputs when a host samplesheet and spacer FASTA were supplied:

```bash
bash phageflow/bin/phageflow validate \
  --outdir results/phage_host_context \
  --expect-host-adaptation \
  --expect-crispr-hits
```

You can also validate individual modules:

```bash
bash phageflow/bin/phageflow validate \
  --outdir results/my_run \
  --expect-trnascan \
  --expect-bacphlip \
  --expect-pharokka
```

The optional validator checks both software-version records and expected files under `05_optional/`. For example, Pharokka validation requires per-sample output directories plus GenBank and GFF files, while clinker validation checks the synteny HTML, GenBank input list, and note file.

## Consolidated Optional-Screen Summary

Use this on any completed run to summarize optional safety-related artifact presence and row counts without printing feature names:

```bash
bash phageflow/bin/phageflow safety-summary \
  --outdir results/my_run \
  --output results/my_run_safety_summary.tsv \
  --summary-json results/my_run_safety_summary.json
```

This is a software QA summary. It reports whether optional artifacts were present, empty, had rows, or were not run. It does not turn missing optional artifacts or zero-row tables into biological conclusions.

## Completed-Run Pangenome Sensitivity Summary

Run the MMseqs and RBH modes into separate output directories, then compare their software summary metrics:

```bash
bash phageflow/bin/phageflow pangenome-sensitivity \
  --left results/phage_cohort_mmseqs \
  --right results/phage_cohort_rbh \
  --output results/pangenome_sensitivity.tsv
```

This reports metric deltas only. It is intended for method-sensitivity QA and does not decide which method is biologically correct.

## Completed-Run Structural Artifact Summary

Use this on a completed Phold-containing run or on a copied structural-artifact directory:

```bash
bash phageflow/bin/phageflow structural-summary \
  --outdir results/my_run \
  --output results/my_run_structural_summary.tsv \
  --summary-json results/my_run_structural_summary.json
```

The summary reports artifact classes, table row/column counts, sizes, checksums, and empty/nonempty status. It intentionally does not print annotation values or interpret structural results.
