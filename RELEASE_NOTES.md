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

## v0.2.0-dev

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
