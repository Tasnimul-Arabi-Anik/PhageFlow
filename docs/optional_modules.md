# Optional Module Installation And Validation

PhageFlow keeps the default environment small. Optional publication modules can be installed into the same removable conda prefix when needed.

Commands in this guide assume you are inside the PhageFlow repository root after cloning:

```bash
git clone https://github.com/Tasnimul-Arabi-Anik/PhageFlow.git
cd PhageFlow
```

## Simple Install Commands

```bash
bash bin/phageflow install --with lite
bash bin/phageflow install --with publication
bash bin/phageflow install --with structure
bash bin/phageflow install --with phylogeny
bash bin/phageflow install --with host
bash bin/phageflow install --with host-prediction
bash bin/phageflow install --with integrated
bash bin/phageflow install --with all
```

Groups:

- `lite`: tRNAscan-SE, BACPHLIP, ABRicate.
- `publication`: `lite` plus CheckV, Pharokka, geNomad, and clinker.
- `structure`: Phold.
- `phylogeny`: MAFFT, IQ-TREE, trimAl, and Biopython for marker-gene trees.
- `host`: Prodigal and minced for optional host-context enrichment.
- `host-prediction`: iPHoP for optional database-backed host prediction.
- `integrated`: PhaBOX2 for optional broad classification, host, lifestyle, and related context.
- `all`: `publication` plus `structure`, `phylogeny`, `host`, `host-prediction`, and `integrated`.

The installer handles executables only. Database-heavy tools still require local database paths, for example `--checkv_db`, `--pharokka_db`, `--genomad_db`, `--phold_db`, `--iphop_db`, and `--phabox_db`.

## Managed Heavy Databases

Use `bin/phageflow db` to prepare optional databases outside the repository:

```bash
export PHAGEFLOW_DB_ROOT=/mnt/storage/db/phageflow
bash bin/phageflow db status
bash bin/phageflow db prepare \
  --tools publication,structure,host-prediction,integrated \
  --threads 16 \
  --dry-run
```

Remove `--dry-run` to download missing databases. Existing populated database directories are skipped by default; use `bash bin/phageflow db update ...` to fetch fresh copies. After preparation, generate matching Nextflow arguments:

```bash
bash bin/phageflow db run-args --tools all --shell
```

See [`database_management.md`](database_management.md) for the full local and `dulab` remote workflow.

## Doctor Checks

```bash
bash bin/phageflow doctor --with publication
bash bin/phageflow doctor --with phylogeny
bash bin/phageflow doctor --with host
bash bin/phageflow doctor --with host-prediction
bash bin/phageflow doctor --with integrated
bash bin/phageflow doctor --with all
```

The doctor command reports whether the expected optional executables are visible in the active PhageFlow environment.

## Rigorous Optional Output Validation

After an optional run, validate only the optional modules that were expected to run:

```bash
bash bin/phageflow validate \
  --outdir results/phage_publication \
  --require-pangenome-rows \
  --expect-publication-optionals
```

For Phold in addition to the publication group:

```bash
bash bin/phageflow validate \
  --outdir results/phage_publication_structure \
  --require-pangenome-rows \
  --expect-publication-optionals \
  --expect-phold
```


Validate marker-gene phylogeny outputs when `--run_marker_tree true` was used:

```bash
bash bin/phageflow validate \
  --outdir results/phage_marker_tree \
  --expect-marker-tree
```

Validate host codon-adaptation and CRISPR spacer matching outputs when a host samplesheet and spacer FASTA were supplied:

```bash
bash bin/phageflow validate \
  --outdir results/phage_host_context \
  --expect-host-adaptation \
  --expect-crispr-hits
```

Validate optional iPHoP host-prediction artifacts after a run with `--run_iphop true --iphop_db ...`:

```bash
bash bin/phageflow validate \
  --outdir results/phage_iphop \
  --expect-iphop
```

Validate optional PhaBOX2 artifacts after a run with `--run_phabox true --phabox_db ...`:

```bash
bash bin/phageflow validate \
  --outdir results/phage_phabox \
  --expect-phabox
```

You can also validate individual modules:

```bash
bash bin/phageflow validate \
  --outdir results/my_run \
  --expect-trnascan \
  --expect-bacphlip \
  --expect-pharokka
```

The optional validator checks software-version records, expected files under `05_optional/`, and report-level rows in `99_report/tables/optional_tool_summary.tsv` for expected optional modules. For example, `lite` validation checks tRNAscan-SE, BACPHLIP, and ABRicate artifacts plus summary rows; Pharokka validation requires per-sample output directories plus GenBank and GFF files; clinker validation checks the synteny HTML, GenBank input list, note file, and report summary row.

Phold validates its database and runs Foldseek as usual. If Phold reports the known no-hit condition for a valid input, PhageFlow keeps the Phold directory, log, and a `phold_no_hits_note.txt` file and treats that as an available no-result optional artifact instead of failing the whole workflow.

To validate only the report-level optional summary after manually inspecting or packaging a completed run:

```bash
bash bin/phageflow validate \
  --outdir results/my_run \
  --expect-checkv-summary \
  --expect-pharokka-summary
```

## Consolidated Optional-Screen Summary

Use this on any completed run to summarize optional safety-related artifact presence and row counts without printing feature names:

```bash
bash bin/phageflow safety-summary \
  --outdir results/my_run \
  --output results/my_run_safety_summary.tsv \
  --summary-json results/my_run_safety_summary.json
```

This is a software QA summary. It reports whether optional artifacts were present, empty, had rows, or were not run. It does not turn missing optional artifacts or zero-row tables into biological conclusions.

## Optional Tool Artifact Summary

Every new PhageFlow report includes:

```text
99_report/tables/optional_tool_summary.tsv
```

Use the completed-run command when you want the same summary from an existing output directory:

```bash
bash bin/phageflow optional-summary \
  --root results/my_run \
  --output results/my_run_optional_tool_summary.tsv \
  --summary-json results/my_run_optional_tool_summary.json
```

This table summarizes tRNAscan-SE, BACPHLIP, ABRicate, CheckV, Pharokka, geNomad, Phold, clinker, iPHoP, and PhaBOX/PhaBOX2 artifact availability, primary artifact class, table row/column counts, file counts, sizes, and checksums. It intentionally does not print annotation values, host-prediction values, or make biological conclusions.

## PhaBOX/PhaBOX2 Wrapper And Imports

PhaBOX2 is available as a disabled-by-default heavy optional wrapper. It requires a local PhaBOX2 database path:

```bash
bash bin/phageflow install --with integrated
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --run_phabox true \
  --phabox_db /path/to/phabox_db \
  --phabox_task end_to_end \
  --outdir results/phage_phabox
```

Supported `--phabox_task` values are `end_to_end`, `phamer`, `phagcn`, `phatyp`, `cherry`, `phavip`, `contamination`, `votu`, and `tree`. PhaBOX2 also requires runtime helper tools such as `prodigal-gv` and `diamond` on `PATH`; `bin/phageflow db prepare --tools phabox` rebuilds the downloaded PhaBOX2 DIAMOND indexes with the local DIAMOND version. The wrapper writes per-sample directories and logs under `05_optional/phabox/`, then summarizes those artifacts in `optional_tool_summary.tsv` and `optional_tool_metrics.tsv`.

To include already completed PhaBOX/PhaBOX2 outputs in the conservative optional summary layer, pass the output directory explicitly:

```bash
bash bin/phageflow optional-summary \
  --root results/my_run \
  --phabox-artifact results/my_run/05_optional/phabox/sample_a.phabox \
  --output results/my_run_phabox_optional_summary.tsv

bash bin/phageflow optional-metrics \
  --root results/my_run \
  --phabox-artifact results/my_run/05_optional/phabox/sample_a.phabox \
  --output results/my_run_phabox_optional_metrics.tsv
```

If a completed run contains directories named like `05_optional/phabox/<sample_id>.phabox`, the completed-run summary/package helpers also detect them. PhaBOX/PhaBOX2 rows are artifact/metric counts only; taxonomy, lifestyle, host-prediction, and annotation values are not printed or interpreted.

## Optional Tool Metric Summary

Every new PhageFlow report also includes:

```text
99_report/tables/optional_tool_metrics.tsv
```

Use the completed-run command when you want the same metric-count summary from an existing output directory:

```bash
bash bin/phageflow optional-metrics \
  --root results/my_run \
  --output results/my_run_optional_tool_metrics.tsv \
  --summary-json results/my_run_optional_tool_metrics.json
```

This table reports compact counts from stable high-level optional-tool outputs, such as quality-summary rows, confidence fields detected, or host-prediction score fields detected. It intentionally does not print annotation values, taxonomy labels, predicted hosts, feature names, or biological conclusions.

## Functional Category Counts

Every new PhageFlow report includes:

```text
99_report/tables/functional_category_summary.tsv
```

Use the completed-run command when you want the same summary from existing heavy annotation outputs:

```bash
bash bin/phageflow functional-summary \
  --root results/my_run \
  --output results/my_run_functional_category_summary.tsv \
  --summary-json results/my_run_functional_category_summary.json
```

The first implementation counts broad category values from Pharokka-style category columns, such as PHROG category fields, when present. It does not print individual gene/product annotations and reports `not_run` or `category_column_missing` when a consistent category column is absent.

## Imported Network Context

PhageFlow does not run vConTACT2 or assign network taxonomy. To include counts from a completed vConTACT2-style output directory:

```bash
bash bin/phageflow network-summary \
  --vcontact-dir results/vcontact2 \
  --output results/my_run_network_context_summary.tsv \
  --summary-json results/my_run_network_context_summary.json \
  --import-to-report results/my_run
```

The import summarizes row/column counts from overview tables and node/edge counts from network files. It does not print cluster assignments, taxonomy labels, or biological conclusions. Imported tables are written to `99_report/tables/network_context_summary.tsv` and included by `summarize`/`package`.

## Completed-Run Pangenome Sensitivity Summary

Run the MMseqs and RBH modes into separate output directories, then compare their software summary metrics:

```bash
bash bin/phageflow pangenome-sensitivity \
  --left results/phage_cohort_mmseqs \
  --right results/phage_cohort_rbh \
  --output results/pangenome_sensitivity.tsv \
  --summary-output results/pangenome_sensitivity_summary.tsv \
  --import-to-report results/phage_cohort_mmseqs
```

This reports metric deltas only. It is intended for method-sensitivity QA and does not decide which method is biologically correct. The `--import-to-report` option copies the comparison plus a compact summary into `99_report/tables/` and adds a Markdown sensitivity note to the selected completed report.

## Completed-Run Structural Artifact Summary

Use this on a completed Phold-containing run or on a copied structural-artifact directory:

```bash
bash bin/phageflow structural-summary \
  --outdir results/my_run \
  --output results/my_run_structural_summary.tsv \
  --summary-json results/my_run_structural_summary.json
```

The summary reports artifact classes, table row/column counts, sizes, checksums, and empty/nonempty status. It intentionally does not print annotation values or interpret structural results.
