# Dulab Remote Runbook

This runbook is for future PhageFlow work on the `dulab` workstation. It records the canonical project location, shared database root, database reuse policy, and validation commands for remote runs.

Keep this workflow software-focused. Heavy optional outputs are external-tool evidence and should not be treated as biological conclusions.

## Canonical Locations

Use these paths on `dulab`:

```text
Project workspace: $HOME/Work/Bioinformatics/phagegenomics
Canonical checkout: $HOME/Work/Bioinformatics/phagegenomics/PhageFlow
Core environment:  $HOME/Work/Bioinformatics/phagegenomics/phageflow-env
Tool envs:         $HOME/Work/Bioinformatics/phagegenomics/tool-envs
Shared DB root:    /mnt/storage/db
Backups:           $HOME/Work/Bioinformatics/phagegenomics/_backups
```

The canonical checkout should be the only active PhageFlow working tree for future runs. Older scratch or non-git PhageFlow folders should be moved to a timestamped backup directory before replacement, not deleted immediately.

## Current Remote Setup State

As of 2026-07-06, `dulab` was configured with:

- a real Git checkout at `$HOME/Work/Bioinformatics/phagegenomics/PhageFlow`;
- the latest local `main` state at setup time;
- the GitHub remote URL set to `https://github.com/Tasnimul-Arabi-Anik/PhageFlow.git`;
- previous non-git/scratch PhageFlow folders moved under `$HOME/Work/Bioinformatics/phagegenomics/_backups/`;
- core workflow validation passing with `bash bin/phageflow test`;
- all six heavy PhageFlow database roots available under `/mnt/storage/db`.

The remote host could not reach GitHub over HTTPS during setup, so the checkout was seeded from a local Git bundle. If GitHub access later works from `dulab`, normal updates should use:

```bash
cd "$HOME/Work/Bioinformatics/phagegenomics/PhageFlow"
git fetch origin
git checkout main
git pull --ff-only
```

If GitHub is still unavailable, seed updates from a trusted local clone with a Git bundle rather than copying generated workflow outputs.

## Environment Setup

Use the existing core environment for lightweight runs:

```bash
export PHAGEFLOW_ROOT="$HOME/Work/Bioinformatics/phagegenomics"
export PHAGEFLOW_ENV_PREFIX="$PHAGEFLOW_ROOT/phageflow-env"
cd "$PHAGEFLOW_ROOT/PhageFlow"

bash bin/phageflow doctor
```

Optional tools are installed or linked in separate tool environments. For heavy optional runs, prepend their `bin` directories:

```bash
export PHAGEFLOW_ROOT="$HOME/Work/Bioinformatics/phagegenomics"
export PHAGEFLOW_ENV_PREFIX="$PHAGEFLOW_ROOT/phageflow-env"
export PATH="$PHAGEFLOW_ROOT/tool-envs/wrappers/bin:$PHAGEFLOW_ENV_PREFIX/bin:$PHAGEFLOW_ROOT/tool-envs/bacphlip/bin:$PHAGEFLOW_ROOT/tool-envs/checkv/bin:$PHAGEFLOW_ROOT/tool-envs/pharokka/bin:$PHAGEFLOW_ROOT/tool-envs/genomad/bin:$PHAGEFLOW_ROOT/tool-envs/phold/bin:$PHAGEFLOW_ROOT/tool-envs/clinker/bin:$PHAGEFLOW_ROOT/tool-envs/iphop/bin:$PHAGEFLOW_ROOT/tool-envs/phabox2/bin:$PHAGEFLOW_ROOT/tool-envs/phabox/bin:$PHAGEFLOW_ROOT/tool-envs/phylogeny/bin:$PATH"
```

Verified optional tool locations include:

```text
tool-envs/wrappers/bin/abricate
tool-envs/bacphlip/bin/bacphlip
tool-envs/checkv/bin/checkv
tool-envs/pharokka/bin/pharokka.py
tool-envs/pharokka/bin/tRNAscan-SE
tool-envs/genomad/bin/genomad
tool-envs/phold/bin/phold
tool-envs/clinker/bin/clinker
tool-envs/iphop/bin/iphop
tool-envs/phabox2/bin/phabox2
tool-envs/phylogeny/bin/iqtree2
tool-envs/phylogeny/bin/trimal
```

`tool-envs/abricate` is a symlink to an existing ABRicate conda environment. The wrapper in `tool-envs/wrappers/bin/abricate` ensures ABRicate uses that environment's Perl modules even when the PhageFlow core environment appears earlier in `PATH`. `tool-envs/phylogeny/bin/iqtree2` is a compatibility symlink to the IQ-TREE executable installed by the conda package.

Do not force a single `bash bin/phageflow install --with all` solve if it stalls. Prefer reusing existing neighboring environments or installing missing tools into dedicated `tool-envs/<tool>/` environments.

## Shared Database Policy

Use `/mnt/storage/db` directly as the database root:

```bash
export PHAGEFLOW_DB_ROOT=/mnt/storage/db
```

Check status before any run:

```bash
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT" --tools all
```

Preview database preparation without downloading:

```bash
bash bin/phageflow db prepare \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools all \
  --threads 32 \
  --dry-run
```

Expected behavior for existing databases is `skipped_existing`. Do not run `db update` unless the user explicitly asks for a fresh copy.

Generate heavy-run arguments from the current links:

```bash
bash bin/phageflow db run-args \
  --db-root "$PHAGEFLOW_DB_ROOT" \
  --tools all \
  --shell
```

As of setup, `/mnt/storage/db/phageflow_db_manifest.json` recorded available current databases for:

```text
checkv
pharokka
genomad
phold
iphop
phabox
```

## Symlink And Copy Policy

Use this policy if a future database already exists outside `/mnt/storage/db`:

- Prefer a symlink from `/mnt/storage/db/<tool>/<label>` to the existing stable database location.
- Point `/mnt/storage/db/<tool>/current` at the selected version or symlink.
- Copy only when the existing location is temporary, unreliable, or expected to be removed.
- Never duplicate a large database if `db status` already reports a usable current database.
- Update `/mnt/storage/db/phageflow_db_manifest.json` only through `bin/phageflow db prepare` or `bin/phageflow db update`, or record any manual symlink adoption in a separate note.

## Lightweight Validation

Run the bundled smoke test before using the remote checkout for new work:

```bash
export PHAGEFLOW_ROOT="$HOME/Work/Bioinformatics/phagegenomics"
export PHAGEFLOW_ENV_PREFIX="$PHAGEFLOW_ROOT/phageflow-env"
cd "$PHAGEFLOW_ROOT/PhageFlow"

bash bin/phageflow test
```

The expected success message is:

```text
PhageFlow validation passed.
```

## Heavy Optional Run Template

Use a dedicated output directory for each heavy run:

```bash
export PHAGEFLOW_ROOT="$HOME/Work/Bioinformatics/phagegenomics"
export PHAGEFLOW_ENV_PREFIX="$PHAGEFLOW_ROOT/phageflow-env"
export PHAGEFLOW_DB_ROOT=/mnt/storage/db
export PATH="$PHAGEFLOW_ROOT/tool-envs/wrappers/bin:$PHAGEFLOW_ENV_PREFIX/bin:$PHAGEFLOW_ROOT/tool-envs/bacphlip/bin:$PHAGEFLOW_ROOT/tool-envs/checkv/bin:$PHAGEFLOW_ROOT/tool-envs/pharokka/bin:$PHAGEFLOW_ROOT/tool-envs/genomad/bin:$PHAGEFLOW_ROOT/tool-envs/phold/bin:$PHAGEFLOW_ROOT/tool-envs/clinker/bin:$PHAGEFLOW_ROOT/tool-envs/iphop/bin:$PHAGEFLOW_ROOT/tool-envs/phabox2/bin:$PHAGEFLOW_ROOT/tool-envs/phabox/bin:$PHAGEFLOW_ROOT/tool-envs/phylogeny/bin:$PATH"
cd "$PHAGEFLOW_ROOT/PhageFlow"

DB_ARGS="$(bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools all --shell)"

nextflow run main.nf \
  --input data/public_examples/<example_id>/samplesheet.tsv \
  --outdir results/<example_id>_heavy_optional \
  $DB_ARGS
```

Validate only the optional modules actually enabled and completed. For all supported database-backed wrappers:

```bash
bash bin/phageflow validate \
  --outdir results/<example_id>_heavy_optional \
  --require-pangenome-rows \
  --expect-checkv \
  --expect-pharokka \
  --expect-genomad \
  --expect-phold \
  --expect-iphop \
  --expect-phabox
```

If the run does not include every optional module, remove the unmatched `--expect-*` flags.

## Agent Rules

Future AI agents should follow these rules on `dulab`:

- Do not download databases before checking `/mnt/storage/db` with `db status`.
- Use `db prepare --dry-run` first; expect existing DBs to be skipped.
- Use `db update` only on explicit user request.
- Do not store large databases or generated heavy results inside Git.
- Back up old PhageFlow folders before replacing them.
- Keep one canonical active checkout at `$HOME/Work/Bioinformatics/phagegenomics/PhageFlow`.
- Use the PATH pattern above for existing tool envs instead of forcing a large all-in-one conda solve.
- Keep biological interpretation separate from software validation.
