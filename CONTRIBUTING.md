# Contributing To PhageFlow

PhageFlow is maintained as a reproducible software workflow for already sequenced phage genomes. Contributions should strengthen the pipeline, output contracts, documentation, validation, or optional analysis wrappers without turning software validation into biological interpretation.

## Development Checks

Run the lightweight checks before opening a change:

```bash
python3 -m py_compile bin/*.py
bash -n bin/phageflow bin/run_local_validation.sh bin/container_smoke_test.sh
```

Run the full local validation suite when changing workflow behavior, report generation, validation logic, or module wiring:

```bash
bash bin/run_local_validation.sh
```

Run the container smoke test when changing `containers/Dockerfile`, `.dockerignore`, environment setup, launcher behavior, or Nextflow profiles:

```bash
bash bin/phageflow container-smoke
```

## Scope Rules

- Keep default runs local and reproducible.
- Do not add network-dependent data fetching to the core workflow.
- Require explicit local database or reference inputs for heavy optional tools.
- Record tool versions, parameters, provenance, and limitations for new outputs.
- Add validator coverage for new required outputs and optional-output flags for optional modules.
- Keep manuscript-grade biological conclusions outside the pipeline report.

## Adding Optional Tools

New optional tools should be wrapped behind clear parameters, for example `--run_tool_name true` plus any required database path. The first implementation should produce a stable artifact inventory or conservative summary before trying to generate interpretive text.

Useful acceptance criteria for a new optional module:

- The workflow still passes bundled test data without the optional tool installed.
- Enabling the module has a clear failure message when required executables or databases are missing.
- Outputs are written under a predictable `05_optional/` subdirectory.
- `validate_phageflow_run.py` can check expected artifacts.
- `build_report.py`, `summarize`, or `package` exposes non-sensitive summary/provenance fields.
