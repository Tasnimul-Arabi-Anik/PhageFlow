# Release Checklist

Use this checklist before tagging a PhageFlow release.

## Metadata

- [ ] `README.md` status matches the intended release label.
- [ ] `RELEASE_NOTES.md` includes the release date and validation summary.
- [ ] `CITATION.cff` version and date are current.
- [ ] Release validation evidence is recorded in `docs/v0.4_release_validation.md` or the current release-equivalent file.
- [ ] `LICENSE` is present and matches the intended distribution terms.
- [ ] GitHub issue templates and PR template are present.

## Validation

- [ ] Python utilities compile.
- [ ] Shell scripts pass syntax checks.
- [ ] Bundled samplesheets validate.
- [ ] Full local validation suite passes.
- [ ] Container smoke test passes when Docker is available.
- [ ] Package export works from a completed run.
- [ ] Public example-data provenance is recorded before any real-data validation release, including source, accession or record ID, retrieval date, input checksum, command log, database versions when used, and interpretation boundary.

## Scope Boundaries

- [ ] Release notes state software/workflow validation only.
- [ ] Biological interpretation and manuscript-grade conclusions are not claimed.
- [ ] Optional heavy tools are clearly marked as optional.
- [ ] Any required external databases are user-provided local paths or explicitly prepared with `bin/phageflow db prepare` under a user-chosen database root.
- [ ] `docs/analysis_capability_matrix.md` matches the release state.

## Analysis Scope Gate

Use this gate before adding or promoting a new analysis:

- [ ] Default analysis: runs without large databases, heavy installs, or external services; has bundled validation data; produces conservative software-artifact claims only.
- [ ] Heavy optional wrapper: disabled by default; dependency and database paths are explicit; database preparation is explicit and manifest-backed; software versions are captured; validator can require expected outputs; docs describe limitations.
- [ ] Import-only summary: does not run the external tool; accepts completed output directories/files; reports counts, shapes, checksums, or broad summaries without raw sensitive values; package/summarize behavior is tested.
- [ ] Deferred: requires raw reads, public database policy, unstable CLI/output contracts, large unvalidated databases, or a separate biological-validation dataset.
- [ ] Promotion path is documented if an import-only feature should later become a runnable wrapper.

## GitHub Release

- [ ] Main branch is clean and pushed.
- [ ] CI passes on GitHub.
- [ ] Release tag is created from the intended commit.
- [ ] Release description links validation evidence and limitations.
