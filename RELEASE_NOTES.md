# PhageFlow Release Notes

## v0.1.0-validated - 2026-06-29

PhageFlow is functionally complete and validated for the current lightweight single-genome and small-cohort genome-analysis scope.

Validation state:

- Focused local Nextflow workflow run completed.
- Strict validator passed.
- Sanitized artifact QA inventory completed with anonymous artifact IDs, row and column counts, file sizes, and checksums.
- Final artifact audit did not rerun the workflow, print table contents, expose result paths, or perform domain-specific interpretation.

Scope boundaries:

- Software/workflow validation is claimed.
- Domain interpretation is not claimed.
- Manuscript-grade biological conclusion is not claimed.

Remaining work is release polish: README and example-command refinement, packaging/container checks, and clear labeling of demo or stress-test outputs versus outputs suitable for formal reporting.

## v0.2.0-dev - 2026-06-30

Initial v0.2 planning and utility work:

- Added a reviewed extension plan in `docs/v0.2_extension_review.md`.
- Added `phageflow summarize` for sanitized completed-run artifact QA summaries.
- Added `phageflow safety-summary` for conservative optional-screen artifact status and row-count summaries.
- Added `phageflow structural-summary` for structural-annotation artifact inventory without annotation-value printing.
- Added `phageflow pangenome-sensitivity` to compare summary metrics from two completed pangenome runs.
- Added `phageflow package` for report/QA tarball generation from completed runs.
- Added conservative exact-terminal-repeat heuristic fields to FASTA QC outputs.
- Added `claim_evidence_matrix.tsv` to new reports for software claim-to-artifact traceability.
- Added `marker_provenance.tsv` for marker alignment/tree provenance and validator coverage when marker-tree outputs are expected.
- Added `.dockerignore` and a host-UID container smoke-test path so container outputs remain host-writable.
- Added local-validation hooks for summarize/safety/structural/package utilities.
- Added `docs/v0.2_completion_audit.md` documenting implemented, validated, deferred, and avoided roadmap items.

Release polish:

- Added MIT license metadata, citation metadata, contribution guidance, security notes, and release checklist.
- Added GitHub Actions static CI for Python compilation, shell syntax checks, bundled samplesheet validation, and tracked-size guardrails.
- Added GitHub issue templates and pull request checklist.
- Clarified README status so `v0.1.0-validated` is the first strict-validation milestone and `v0.2.0-dev` is the current development state.
- Added `docs/v0.3_analysis_roadmap.md` ranking future optional-analysis additions without copying whole external pipelines.

v0.3 priority-1 increment:

- Added `phageflow optional-summary` and `bin/optional_tool_summary.py` for conservative CheckV/Pharokka/geNomad/Phold/clinker artifact summaries.
- Added `optional_tool_summary.tsv` to new reports, report HTML/Markdown, runtime summaries, validation manifest, important-files manifest, and claim-evidence matrix.
- Added optional-summary integration to `summarize` and `package`.
- Extended validator coverage so expected CheckV/Pharokka/geNomad/Phold/clinker modules also require report-level optional summary rows; added `--expect-*-summary` flags for report-only checks.
- Reviewed Clinker static export feasibility and kept native HTML/alignment artifacts as the validated contract; automated SVG/PNG/PDF export remains deferred until a stable upstream CLI or separate browser-rendering contract is available.

v0.3 priority-2 increment:

- Added local reference-context reporting for samplesheets that mark rows as `role=reference`.
- Added nearest-reference and all query/reference metric tables, report integration, claim-evidence rows, runtime/validation manifest counters, and method limitations.
- Added validator support with `--expect-reference-context` and wired the bundled cohort validation runs to require it.
