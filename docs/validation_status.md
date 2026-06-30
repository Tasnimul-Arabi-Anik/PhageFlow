# PhageFlow Validation Status

Status: `v0.3.0-validated`

Validation date: 2026-07-01

## Scope

PhageFlow is complete for the current lightweight single-genome and small-cohort genome-analysis scope. This status covers software workflow execution, report generation, validation checks, completed-run QA utilities, optional artifact summaries, local reference-context reporting, container smoke validation, and package export. It does not claim domain interpretation or manuscript-grade biological conclusions.

## Completed

- Core Nextflow workflow.
- Single-genome and small-cohort modes.
- QC, ORF, codon, comparative, and optional pangenome-style summaries.
- Optional marker-tree branch.
- Optional host-context artifact branch.
- CLI install, doctor, run, test, and validate commands.
- Report generation with tables, figures, manifests, versions, parameters, and runtime summaries.
- Completed-run summarize, safety-summary, optional-summary, structural-summary, pangenome-sensitivity, and package utilities.
- Optional-tool artifact summaries for CheckV, Pharokka, geNomad, Phold, and clinker.
- Local reference-context branch for samplesheets with `role=reference`.
- Strict validator coverage for pangenome rows, marker-tree outputs, host-context outputs, CRISPR spacer hits, optional-module outputs, and local reference-context outputs when requested.

## Validation Evidence

Release validation commands for `v0.3.0-validated`:

- `python3 -m py_compile bin/*.py`
- `bash -n bin/phageflow bin/run_local_validation.sh bin/container_smoke_test.sh`
- `git diff --check`
- `bash bin/run_local_validation.sh`
- `bash bin/phageflow container-smoke`

Release validation outcomes:

- Full local validation suite: passed.
- Container smoke test: passed.
- Package export from completed run: passed.
- Local reference-context validator check: passed in bundled cohort validation runs.
- Marker-tree validator check: passed in bundled marker-tree validation run.

Historical `v0.1.0-validated` focused audit:

- Full focused local Nextflow run: completed.
- Strict validator: passed.
- Sanitized artifact QA: completed.
- Result directory detection: passed.
- Total files in audited result directory: 297.
- Total audited bytes: 520038453.
- TSV artifacts: 171.
- Figure artifacts: 18.
- Text-like files scanned for generic markers: 179.
- Report/log/version/manifest/checksum-like files: 8.
- Generic marker counts: PASS 38, FAIL 0, WARN 0, ERROR 0.

The historical artifact audit did not rerun the workflow, print table contents, expose result paths, or perform domain-specific interpretation. The artifact inventory used anonymous IDs for TSV and figure files.

## Boundaries

- Software/workflow validation: claimed.
- Domain interpretation: not claimed.
- Manuscript-grade biological conclusion: not claimed.
- Wet-lab design, engineering, host-range expansion, synthesis, or virulence-enhancement support: not provided by this pipeline.

## Remaining Polish

Remaining work after `v0.3.0-validated` is future feature work, not release-blocking core validation:

- Optional reference package manifest beyond existing run/report manifests.
- Optional host-prediction wrapper with a local database contract.
- Pangenome method concordance import into reports.
- Marker-tree QC dashboard refinements.
