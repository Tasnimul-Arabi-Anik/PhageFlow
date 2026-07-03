# Troubleshooting

This guide covers common local setup, optional-tool, database, container, and validation issues. It keeps fixes local and reproducible. For heavy optional databases, check the upstream license, citation, storage requirements, and local policy before downloading, updating, or using a database.

Commands assume you are in the PhageFlow repository root.

## Quick Triage

Run these checks first:

```bash
bash bin/phageflow doctor
tail -n 80 .nextflow.log
```

For failed Nextflow tasks, inspect the task log that Nextflow reports:

```bash
ls -lah work/
TASK_DIR=work/path_reported_by_nextflow
cat "$TASK_DIR/.command.err"
cat "$TASK_DIR/.command.log"
```

Use the exact task directory printed by Nextflow. Do not copy large work directories into Git.

## Nextflow Not Found

Symptom:

- `nextflow: command not found`
- PhageFlow stops before launching the workflow.

Likely cause:

- Nextflow is not installed or the PhageFlow conda environment is not active.

Safe fix:

```bash
bash install.sh
bash bin/phageflow install
```

Command to re-check:

```bash
bash bin/phageflow doctor
nextflow -version
```

## Java Missing

Symptom:

- Nextflow reports that Java is missing.
- Nextflow starts and exits before running any process.

Likely cause:

- A Java runtime compatible with Nextflow is not visible on `PATH`.

Safe fix:

Use the PhageFlow installer or activate an environment that includes Java/Nextflow:

```bash
bash bin/phageflow install
```

If using a system package manager, install a supported Java runtime according to your operating-system policy, then reopen the shell.

Command to re-check:

```bash
java -version
nextflow -version
```

## Conda, Mamba, Or Micromamba Missing

Symptom:

- `ERROR: conda/mamba/micromamba not found`
- `bash bin/phageflow install` cannot create the local environment.

Likely cause:

- No supported conda frontend is installed or visible on `PATH`.

Safe fix:

Install Miniconda, Miniforge, Mambaforge, mamba, or micromamba using your normal local policy, then start a new shell and rerun:

```bash
bash bin/phageflow install
```

Command to re-check:

```bash
command -v mamba || command -v micromamba || command -v conda
bash bin/phageflow doctor
```

## Docker Unavailable

Symptom:

- `docker: command not found`
- `Cannot connect to the Docker daemon`
- `bash bin/phageflow container-smoke` fails before running the workflow.

Likely cause:

- Docker is not installed, the daemon is stopped, or the current user cannot access Docker.

Safe fix:

Use the native conda/local workflow unless you specifically need containers:

```bash
bash bin/phageflow test
```

If containers are required, install/start Docker using your local system policy and confirm your user can run Docker.

Command to re-check:

```bash
docker info
bash bin/phageflow container-smoke
```

## MMseqs Not Found

Symptom:

- A pangenome run fails with `mmseqs: command not found`.
- `--pangenome_method mmseqs` cannot complete.

Likely cause:

- MMseqs2 is missing from `PATH` or the PhageFlow environment was not installed.

Safe fix:

```bash
bash bin/phageflow install
```

For a run that does not need pangenome clustering, use:

```bash
bash bin/phageflow run \
  --input assets/test_data/toy_phage_a.fasta \
  --pangenome_method none \
  --outdir results/single_no_pangenome
```

Command to re-check:

```bash
mmseqs version
bash bin/phageflow doctor
```

## BLAST Tools Missing

Symptom:

- A comparative or reciprocal-best-hit run fails with `blastn`, `blastp`, or `makeblastdb` not found.
- Intergenomic similarity or RBH pangenome outputs are missing after a failed run.

Likely cause:

- BLAST+ executables are missing from `PATH` or the PhageFlow environment was not installed.

Safe fix:

```bash
bash bin/phageflow install
```

Command to re-check:

```bash
blastn -version
blastp -version
makeblastdb -version
bash bin/phageflow doctor
```

## Optional Tool Executable Missing

Symptom:

- A run with an optional `--run_* true` flag fails because an executable is missing.
- `bash bin/phageflow doctor --with ...` reports missing optional tools.

Likely cause:

- The optional executable group was not installed into the active PhageFlow environment.

Safe fix:

Install only the optional group you intend to run:

```bash
bash bin/phageflow install --with publication
bash bin/phageflow install --with structure
bash bin/phageflow install --with phylogeny
bash bin/phageflow install --with host
bash bin/phageflow install --with host-prediction
bash bin/phageflow install --with integrated
```

Use `--with all` only when you intentionally want every optional executable installed.

Command to re-check:

```bash
bash bin/phageflow doctor --with publication
bash bin/phageflow doctor --with structure
bash bin/phageflow doctor --with phylogeny
bash bin/phageflow doctor --with host
bash bin/phageflow doctor --with host-prediction
bash bin/phageflow doctor --with integrated
```

## Heavy Database Path Missing

Symptom:

- A run requests CheckV, Pharokka, geNomad, Phold, iPHoP, or PhaBOX/PhaBOX2 and fails before or during the optional module.
- The relevant parameter is missing or points to a nonexistent directory.

Likely cause:

- The executable is installed, but the required local database path was not provided.

Safe fix:

Supply the matching local path parameter:

```text
--checkv_db /path/to/checkv_db
--pharokka_db /path/to/pharokka_db
--genomad_db /path/to/genomad_db
--phold_db /path/to/phold_db
--iphop_db /path/to/iphop_db
--phabox_db /path/to/phabox_db
```

To manage databases with PhageFlow, first check upstream licenses/citations and local storage policy, then preview the database operation:

```bash
export PHAGEFLOW_DB_ROOT=/path/to/database_root
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT"
bash bin/phageflow db prepare --db-root "$PHAGEFLOW_DB_ROOT" --tools all --dry-run
bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools all --shell
```

Remove `--dry-run` only after the database source, license/citation, and storage requirements are acceptable for your environment. Existing populated database directories are skipped by `prepare`; use `db update` only when you intentionally want a fresh database copy.

Command to re-check:

```bash
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT"
bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools all --shell
```

## PhaBOX2 Requested Without A Database

Symptom:

- A run includes `--run_phabox true` and fails because `--phabox_db` was not supplied.

Likely cause:

- PhaBOX/PhaBOX2 is database-backed and cannot run from the executable alone.

Safe fix:

Provide a validated local PhaBOX/PhaBOX2 database path:

```bash
nextflow run main.nf \
  --input phage_samplesheet.tsv \
  --run_phabox true \
  --phabox_db /path/to/phabox_db \
  --outdir results/phabox_run
```

If using managed database arguments, check upstream license/citation and local storage policy first, then generate the local flags:

```bash
bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools integrated --shell
```

Command to re-check:

```bash
test -d /path/to/phabox_db && echo "PhaBOX database directory exists"
bash bin/phageflow validate --outdir results/phabox_run --expect-phabox
```

## Output Directory Already Exists

Symptom:

- A run fails because an output directory already exists.
- New results are mixed with files from an older attempt.

Likely cause:

- The same `--outdir` was reused for a different run, or a previous failed run left partial output files.

Safe fix:

Use a new descriptive output directory for each independent run:

```bash
bash bin/phageflow run \
  --input assets/test_data/toy_phage_a.fasta \
  --outdir results/my_run_001
```

If you are resuming the same interrupted Nextflow run, use the same command and Nextflow resume behavior deliberately. Archive or remove old output directories only after you confirm they are no longer needed.

Command to re-check:

```bash
test ! -e results/my_run_001 && echo "output path is available"
```

## Optional Expectation Flag Used Incorrectly

Symptom:

- The workflow completed, but validation fails after adding `--expect-*`.
- The validator reports missing optional rows or missing optional directories.

Likely cause:

- The validator was told to expect an optional module that was not actually run, or the matching database-backed module failed earlier.

Safe fix:

Validate only the modules that were requested and completed. For a default run:

```bash
bash bin/phageflow validate --outdir results/my_run
```

For an optional run, match validator flags to the run command:

```bash
bash bin/phageflow validate \
  --outdir results/my_run \
  --expect-publication-optionals
```

Add per-module expectation flags only for modules that were enabled and completed, for example `--expect-phold`, `--expect-iphop`, or `--expect-phabox`.

Command to re-check:

```bash
test -s results/my_run/99_report/phageflow_validation_report.tsv && echo "validation report exists"
test -s results/my_run/99_report/tables/optional_tool_summary.tsv && echo "optional summary exists"
```

## Large Optional Tools Are Slow Or Memory-Heavy

Symptom:

- Heavy optional modules run for a long time, use substantial memory, or fill temporary storage.
- Database-backed modules are much slower than the default workflow.

Likely cause:

- Optional external tools and large databases have higher runtime, memory, and disk requirements than the lightweight default path.

Safe fix:

Keep the default run lightweight while testing:

```bash
bash bin/phageflow run \
  --input phage_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/lightweight_check
```

Then run heavy optional modules on a small public example or a subset, with an output directory dedicated to that run. On shared or remote workstations, use a project work directory outside Git and keep databases under a shared database root such as `/mnt/storage/db`.

Command to re-check:

```bash
du -sh results/lightweight_check
tail -n 80 .nextflow.log
bash bin/phageflow validate --outdir results/lightweight_check --require-pangenome-rows
```

## Container Output Permission Issues

Symptom:

- Docker runs finish but output files are owned by a different user.
- A container task fails with `Permission denied` while writing `results/` or `work/`.

Likely cause:

- The container user, mounted directory ownership, or host filesystem permissions do not match the local user.

Safe fix:

Create output and work directories as the current user before running the container workflow:

```bash
mkdir -p results work
ls -ld results work
```

If running Docker directly, pass the current user and group where appropriate:

```bash
docker run --rm -u "$(id -u):$(id -g)" phageflow:latest
```

If files were created with unexpected ownership, fix only the run directory you created after confirming it belongs to this workflow.

Command to re-check:

```bash
id
ls -ld results work
bash bin/phageflow container-smoke
```

## Still Failing

Collect software-level evidence without printing sequence content or table values:

```bash
bash bin/phageflow doctor
tail -n 80 .nextflow.log
find results/my_run -maxdepth 3 -type f | wc -l
```

For completed runs, package or summarize artifacts instead of rerunning:

```bash
bash bin/phageflow summarize --outdir results/my_run --output results/my_run_summary.json
bash bin/phageflow package --outdir results/my_run --output results/my_run_phageflow_package.tar.gz
```

Keep biological interpretation separate from software troubleshooting. Validation failures show missing or inconsistent workflow artifacts; they are not biological conclusions.
