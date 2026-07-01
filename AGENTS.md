# PhageFlow Agent Handoff

This repository is a validated software pipeline for lightweight single-genome and small-cohort phage genome analysis, with heavier analyses kept optional. Future AI agents should preserve the validated default path and treat biological outputs as software artifacts unless a separate domain-validation effort is explicitly added.

## Read First

- `README.md`: user-facing install, run, output, and validation commands.
- `docs/analysis_capability_matrix.md`: what is default, heavy optional, import-only, or deferred.
- `docs/optional_modules.md`: optional tool install/run/validate contracts.
- `docs/release_checklist.md`: release and analysis-scope gate.
- `docs/v0.4_progress.md`: recent expansion status and remaining deferred work.
- `docs/validation_status.md`: validation claims and explicit boundaries.

## Current Architecture

- `main.nf` wires the Nextflow workflow and must keep lightweight behavior enabled by default.
- `modules/core.nf` and `bin/build_report.py` generate the report bundle, including `99_report/tables/` and `99_report/figures/`.
- `modules/optional_tools.nf` contains disabled-by-default heavy wrappers.
- `bin/optional_tool_summary.py` and `bin/optional_tool_metrics.py` summarize optional artifacts without printing annotation, taxonomy, host-prediction, or feature values.
- `bin/validate_phageflow_run.py` is the strict completed-run validator.
- `bin/phageflow` is the user launcher for install, doctor, run, validate, summarize, package, and related commands.

## Non-Negotiable Boundaries

- Do not make heavy tools or large databases part of the default run.
- Do not add public-network database discovery to the default workflow.
- Do not print raw annotation values, taxonomy labels, host-prediction values, feature names, table cell contents, or sensitive sequence strings in summary utilities.
- Do not claim host range, infectivity, wet-lab outcome, manuscript-grade biological conclusions, or domain interpretation.
- Keep every external database as an explicit local path parameter.
- Capture software-version status for any runnable optional tool.
- Add validator expectations for any new optional wrapper.

## Adding A New Analysis

Use the scope gate in `docs/release_checklist.md` before coding:

- Default: small, local, no large database, bundled validation data available.
- Heavy optional wrapper: disabled by default, explicit executable/database params, output under `05_optional/<tool>/`, software versions captured, validator can require expected outputs, docs describe limitations.
- Import-only summary: accepts completed outputs, reports only counts/shapes/checksums/broad categories, integrates with `summarize` and `package`.
- Deferred: raw reads, metagenomic discovery, public taxonomy assignment, unstable CLI/database contracts, or features needing a separate validation dataset.

## External Pipeline Reuse

Borrow design patterns from mature pipelines, such as module layout, clear output contracts, provenance, and validation style. Do not copy external code wholesale unless license compatibility and attribution are reviewed. Prefer native PhageFlow wrappers or import-only summaries around established tools.

## Validation Commands

Run focused checks for most changes:

```bash
python3 -m py_compile bin/*.py tests/*.py
bash -n bin/phageflow bin/run_local_validation.sh bin/container_smoke_test.sh
git diff --check
```

Run relevant regression tests:

```bash
python3 tests/test_optional_tool_summary.py
python3 tests/test_validator_optionals.py
python3 tests/test_lightweight_metrics.py
python3 tests/test_pangenome_sensitivity.py
python3 tests/test_network_context_summary.py
```

Run the full local workflow validation after changes to Nextflow wiring, report tables, validator contracts, or user-facing output layout:

```bash
bash bin/run_local_validation.sh
```

For larger validations, use the configured remote host `dulab` with a temporary directory, copy only needed files, and remove the directory after validation.

## Current Deferred Work

- vConTACT2-style execution remains deferred; import-only `network-summary` exists.
- Public-database taxonomy assignment needs a database/version/provenance policy first.
- Metagenomic discovery needs a separate input contract and validation dataset.
- Read-based termini or packaging inference needs raw-read inputs and validation data.
