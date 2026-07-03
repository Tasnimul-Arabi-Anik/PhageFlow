# Heavy Optional Validation Runbook

This runbook prepares database-backed PhageFlow validation for heavy optional modules. It is for software/workflow validation only. Heavy outputs remain external-tool evidence; PhageFlow validates artifact presence, report integration, software-version capture, and summary rows.

Before running heavy optional validation:

- Use a small public input subset or an internal validation subset with clear provenance.
- Keep heavy tools disabled by default.
- Keep databases outside Git under a user-chosen database root.
- Check upstream licenses, citations, database terms, and local storage policy.
- Record database versions and commands according to [`public_example_data_policy.md`](public_example_data_policy.md).
- Validate only modules that were explicitly enabled and completed.

## Shared Setup

Install optional executables:

```bash
bash bin/phageflow install --with publication,structure,host-prediction,integrated
bash bin/phageflow doctor --with publication
bash bin/phageflow doctor --with structure
bash bin/phageflow doctor --with host-prediction
bash bin/phageflow doctor --with integrated
```

Check or prepare local databases after reviewing licenses/citations:

```bash
export PHAGEFLOW_DB_ROOT=/path/to/database_root
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT"
bash bin/phageflow db prepare --db-root "$PHAGEFLOW_DB_ROOT" --tools all --threads 16 --dry-run
bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools all --shell
```

Remove `--dry-run` only when large downloads are approved for the target machine. Existing populated databases are skipped by `prepare`; use `db update` only when a fresh database copy is intentionally needed.

For each validation run, record:

```text
example_id
phageflow_commit
input_manifest_path
tool
executable_version
database_root
database_path_parameter
database_version_or_release
database_retrieval_date
database_manifest_path
run_command
validator_command
validation_outcome
interpretation_boundary
```

## CheckV

Required executable:

- `checkv`

Required database/path parameter:

- `--checkv_db /path/to/checkv_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_checkv true \
  --checkv_db /path/to/checkv_db \
  --outdir results/public_examples/<example_id>_checkv
```

Expected output directory:

```text
05_optional/checkv/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_checkv \
  --expect-checkv
```

Expected report summary table rows:

- `99_report/tables/optional_tool_summary.tsv` includes CheckV artifact rows.
- `99_report/tables/optional_tool_metrics.tsv` includes CheckV metric-count rows when stable high-level outputs are present.
- `99_report/software_versions.tsv` includes CheckV status.

Resource notes:

- Database-backed quality checks can require substantial disk and runtime compared with the default workflow.
- Keep the database under the shared database root, not under the repository.

Interpretation boundary:

- CheckV values remain external-tool quality evidence. PhageFlow validates artifact capture and report integration only.

Database provenance fields to record:

```text
checkv_db_path
checkv_database_release_or_manifest
retrieval_date
retrieval_or_update_command
license_or_terms_checked
citation_or_reference
```

## Pharokka

Required executable:

- `pharokka.py`

Required database/path parameter:

- `--pharokka_db /path/to/pharokka_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_pharokka true \
  --pharokka_db /path/to/pharokka_db \
  --outdir results/public_examples/<example_id>_pharokka
```

Expected output directory:

```text
05_optional/pharokka/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_pharokka \
  --expect-pharokka
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes Pharokka artifact rows.
- `optional_tool_metrics.tsv` includes Pharokka metric-count rows when compatible tables are present.
- `functional_category_summary.tsv` is produced when compatible category tables are available.
- `software_versions.tsv` includes Pharokka status.

Resource notes:

- Pharokka is the preferred heavy annotation route for formal reporting, but the default lightweight ORF path remains useful for quick validation.
- Use the same annotation strategy for all genomes in a cohort when comparing outputs.

Interpretation boundary:

- Gene/product/category values are external annotation evidence. PhageFlow summarizes broad artifact and count information without treating annotations as biological conclusions.

Database provenance fields to record:

```text
pharokka_db_path
pharokka_database_release_or_manifest
retrieval_date
retrieval_or_update_command
license_or_terms_checked
citation_or_reference
```

## geNomad

Required executable:

- `genomad`

Required database/path parameter:

- `--genomad_db /path/to/genomad_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_genomad true \
  --genomad_db /path/to/genomad_db \
  --outdir results/public_examples/<example_id>_genomad
```

Expected output directory:

```text
05_optional/genomad/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_genomad \
  --expect-genomad
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes geNomad artifact rows.
- `optional_tool_metrics.tsv` includes geNomad metric-count rows when stable high-level outputs are present.
- `software_versions.tsv` includes geNomad status.

Resource notes:

- geNomad runs are database-backed and can be split or tuned through existing workflow parameters.
- Record any non-default `--genomad_splits` or extra arguments.

Interpretation boundary:

- Classification, taxonomy, provirus, topology, or hallmark outputs remain external-tool evidence and are not PhageFlow claims.

Database provenance fields to record:

```text
genomad_db_path
genomad_database_release_or_manifest
retrieval_date
retrieval_or_update_command
license_or_terms_checked
citation_or_reference
```

## Phold

Required executable:

- `phold`
- `pharokka.py` is also required because Phold runs from Pharokka GenBank output in this workflow.

Required database/path parameter:

- `--phold_db /path/to/phold_db`
- `--pharokka_db /path/to/pharokka_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_phold true \
  --phold_db /path/to/phold_db \
  --pharokka_db /path/to/pharokka_db \
  --outdir results/public_examples/<example_id>_phold
```

Expected output directory:

```text
05_optional/pharokka/
05_optional/phold/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_phold \
  --expect-pharokka \
  --expect-phold
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes Pharokka and Phold artifact rows.
- `optional_tool_metrics.tsv` includes Phold metric-count rows when stable high-level outputs are present.
- `software_versions.tsv` includes Phold and Pharokka status.

Resource notes:

- Phold is structure-oriented and can be slower than lightweight annotation.
- A valid no-hit state is retained as an optional artifact when Phold reports the known no-hit condition.
- Pharokka output is part of the Phold input contract in PhageFlow.

Interpretation boundary:

- Structural annotation outputs remain external-tool evidence. No-hit or hit-count artifacts are workflow states, not biological conclusions.

Database provenance fields to record:

```text
phold_db_path
pharokka_db_path
phold_database_release_or_manifest
pharokka_database_release_or_manifest
retrieval_date
retrieval_or_update_command
license_or_terms_checked
citation_or_reference
```

## iPHoP

Required executable:

- `iphop`

Required database/path parameter:

- `--iphop_db /path/to/iphop_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_iphop true \
  --iphop_db /path/to/iphop_db \
  --outdir results/public_examples/<example_id>_iphop
```

Expected output directory:

```text
05_optional/iphop/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_iphop \
  --expect-iphop
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes iPHoP artifact rows.
- `optional_tool_metrics.tsv` includes iPHoP metric-count rows when stable high-level outputs are present.
- `software_versions.tsv` includes iPHoP status.

Resource notes:

- iPHoP database downloads are large and may be split or resumed by the database manager.
- Keep staging and promoted database directories outside Git under the database root.

Interpretation boundary:

- Host-prediction outputs are computational evidence only. They do not prove host range, infection, or experimental compatibility.

Database provenance fields to record:

```text
iphop_db_path
iphop_database_release_or_manifest
retrieval_date
retrieval_or_update_command
license_or_terms_checked
citation_or_reference
```

## PhaBOX2

Required executable:

- `phabox2`
- Runtime helper tools required by PhaBOX2, such as DIAMOND and Prodigal-GV, must be available through the selected environment.

Required database/path parameter:

- `--phabox_db /path/to/phabox_db`

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_phabox true \
  --phabox_db /path/to/phabox_db \
  --outdir results/public_examples/<example_id>_phabox
```

Expected output directory:

```text
05_optional/phabox/
```

Recommended validator flag:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_phabox \
  --expect-phabox
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes PhaBOX/PhaBOX2 artifact rows.
- `optional_tool_metrics.tsv` includes PhaBOX/PhaBOX2 metric-count rows when stable high-level outputs are present.
- `software_versions.tsv` includes PhaBOX/PhaBOX2 status.

Resource notes:

- `bin/phageflow db prepare --tools phabox` rebuilds downloaded PhaBOX2 DIAMOND indexes with the local DIAMOND version.
- Record the selected `--phabox_task` when it differs from the default.

Interpretation boundary:

- Taxonomy, lifestyle, host, and annotation values remain external-tool evidence. PhageFlow validates artifact capture only.

Database provenance fields to record:

```text
phabox_db_path
phabox_database_release_or_manifest
retrieval_date
retrieval_or_update_command
diamond_index_rebuild_command
license_or_terms_checked
citation_or_reference
```

## Combined Publication-Style Run

Required executables:

- `trnascan-se`
- `bacphlip`
- `checkv`
- `abricate`
- `pharokka.py`
- `genomad`
- `phold`
- `clinker`
- `iphop`
- `phabox2`

Required database/path parameters:

```text
--checkv_db /path/to/checkv_db
--pharokka_db /path/to/pharokka_db
--genomad_db /path/to/genomad_db
--phold_db /path/to/phold_db
--iphop_db /path/to/iphop_db
--phabox_db /path/to/phabox_db
```

Example command:

```bash
nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --run_trnascan true \
  --run_bacphlip true \
  --run_checkv true \
  --checkv_db /path/to/checkv_db \
  --run_abricate true \
  --run_pharokka true \
  --pharokka_db /path/to/pharokka_db \
  --run_genomad true \
  --genomad_db /path/to/genomad_db \
  --run_phold true \
  --phold_db /path/to/phold_db \
  --run_clinker true \
  --run_iphop true \
  --iphop_db /path/to/iphop_db \
  --run_phabox true \
  --phabox_db /path/to/phabox_db \
  --outdir results/public_examples/<example_id>_heavy_optional
```

Expected output directories:

```text
05_optional/trnascan/
05_optional/bacphlip/
05_optional/checkv/
05_optional/abricate/
05_optional/pharokka/
05_optional/genomad/
05_optional/phold/
05_optional/clinker_synteny/
05_optional/iphop/
05_optional/phabox/
99_report/
```

Recommended validator command:

```bash
bash bin/phageflow validate \
  --outdir results/public_examples/<example_id>_heavy_optional \
  --require-pangenome-rows \
  --expect-publication-optionals \
  --expect-phold \
  --expect-iphop \
  --expect-phabox
```

Expected report summary table rows:

- `optional_tool_summary.tsv` includes rows for every enabled optional module.
- `optional_tool_metrics.tsv` includes compact metric-count rows for supported optional outputs.
- `functional_category_summary.tsv` includes broad category counts when compatible annotation category tables are present.
- `software_versions.tsv` includes status for enabled optional tools.
- `important_files.tsv` and `validation_manifest.json` include report-level packaging and QA evidence.

Resource notes:

- Use a small validation subset first.
- Run on a workstation or cluster node with enough disk, memory, and wall time.
- Keep output directories specific to each validation attempt.
- Use `bin/phageflow db run-args` to avoid hand-copying database paths.

Interpretation boundary:

- A combined heavy run validates wrapper integration and report completeness. It does not convert external-tool outputs into PhageFlow biological conclusions.

Database provenance fields to record:

```text
database_root
database_manifest_path
tool_to_database_path_map
tool_to_database_release_map
database_retrieval_or_update_dates
database_prepare_or_update_commands
license_or_terms_checked_per_database
citation_or_reference_per_database
```

## Completion Criteria

A heavy optional validation is complete only when:

- The input manifest and database provenance are recorded.
- The workflow command is recorded exactly.
- The validator command uses only matching expectation flags.
- The validator passes.
- `optional_tool_summary.tsv`, `optional_tool_metrics.tsv`, and `software_versions.tsv` are present.
- The release note states software/workflow validation only.
- No raw sequence strings, annotation values, taxonomy labels, host-prediction values, or table cell dumps are copied into the validation summary.
