# Heavy Database Management

PhageFlow keeps normal workflow runs offline and reproducible. Large optional databases are prepared explicitly with `bin/phageflow db` under a user-chosen database root, then passed to Nextflow as local paths.

The database manager supports the heavy optional tools that already have PhageFlow wrappers:

- CheckV: `checkv download_database`
- Pharokka: `install_databases.py -o`
- geNomad: `genomad download-database`
- Phold: `phold install -d`
- iPHoP: `iphop download --db_dir -dbv iPHoP.latest_rw --split`
- PhaBOX2: the current PhaBOX2 database release zip URL, followed by local DIAMOND index rebuilds from the bundled FASTA files

Source behavior was checked against the upstream documentation for CheckV, Pharokka, geNomad, Phold, iPHoP, and PhaBOX2 in July 2026. Keep these commands under review because database names and downloader options can change.

## Local Database Root

Pick a location outside the repository. For example:

```bash
export PHAGEFLOW_DB_ROOT=/mnt/storage/db/phageflow
```

On shared database hosts where each tool already has its own top-level directory, using the shared root directly is also valid:

```bash
export PHAGEFLOW_DB_ROOT=/mnt/storage/db
```

Check status:

```bash
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT"
```

Preview downloads without changing anything:

```bash
bash bin/phageflow db prepare \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools publication,structure,host-prediction,integrated \
  --threads 16 \
  --dry-run
```

Download only missing databases:

```bash
bash bin/phageflow db prepare \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools publication,structure,host-prediction,integrated \
  --threads 16
```

Download fresh copies and repoint each tool's `current` link:

```bash
bash bin/phageflow db update \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools publication,structure,host-prediction,integrated \
  --threads 16
```

`prepare` skips existing populated databases. `update` downloads into a staging directory, promotes the new database, and keeps older database directories unless you remove them manually after validation.

For iPHoP split downloads, `prepare` and `update` reuse the latest existing iPHoP staging directory by default. This lets interrupted large downloads continue from completed upstream chunks. Use `--no-resume-staging` only when you intentionally want to discard partial staging state and start a fresh download.

## Heavy Run Arguments

After databases are present, print the Nextflow flags:

```bash
bash bin/phageflow db run-args \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools all \
  --shell
```

Or print a complete command template:

```bash
bash bin/phageflow db heavy-command \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools all \
  --input phage_samplesheet.tsv \
  --outdir results/phageflow_heavy
```

The generated command enables the relevant `--run_*` flags and passes the managed local database paths. Phold also causes Pharokka arguments to be included because Phold consumes Pharokka GenBank output.

## Remote `dulab` Pattern

For the `dulab` workstation, use the dedicated storage mount for databases and a separate project workspace:

```bash
ssh dulab 'mkdir -p /mnt/storage/db "$HOME/Work/Bioinformatics/phagegenomics"'

ssh dulab 'cd "$HOME/Work/Bioinformatics/phagegenomics" && \
  git clone https://github.com/Tasnimul-Arabi-Anik/PhageFlow.git || true'

ssh dulab 'cd "$HOME/Work/Bioinformatics/phagegenomics/PhageFlow" && \
  git fetch origin && git checkout main && git pull --ff-only'

ssh dulab 'cd "$HOME/Work/Bioinformatics/phagegenomics/PhageFlow" && \
  bash bin/phageflow install --with all'

ssh dulab 'cd "$HOME/Work/Bioinformatics/phagegenomics/PhageFlow" && \
    bash bin/phageflow db prepare \
    --db-root /mnt/storage/db \
    --tools publication,structure,host-prediction,integrated \
    --threads 32 \
    --dry-run'
```

Remove `--dry-run` only when you are ready for large downloads. Keep large databases under `/mnt/storage/db` or another shared database root; do not commit them or copy them into the repository. The iPHoP downloader uses upstream split chunks by default and reuses the latest staging directory unless `--no-resume-staging` is given, so interrupted large downloads can reuse completed chunks. The PhaBOX2 preparation step rebuilds bundled DIAMOND indexes with the local DIAMOND executable so the downloaded archive is compatible with the runtime environment.

## Validation Boundary

Database preparation is a software artifact step. It verifies that local database directories exist and records downloader provenance in `phageflow_db_manifest.json`; it does not validate biological interpretation. After a heavy optional run, use `bin/phageflow validate` with the matching `--expect-*` flags and keep conclusions conservative.
