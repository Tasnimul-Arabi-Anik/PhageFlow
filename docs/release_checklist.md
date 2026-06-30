# Release Checklist

Use this checklist before tagging a PhageFlow release.

## Metadata

- [ ] `README.md` status matches the intended release label.
- [ ] `RELEASE_NOTES.md` includes the release date and validation summary.
- [ ] `CITATION.cff` version and date are current.
- [ ] `LICENSE` is present and matches the intended distribution terms.
- [ ] GitHub issue templates and PR template are present.

## Validation

- [ ] Python utilities compile.
- [ ] Shell scripts pass syntax checks.
- [ ] Bundled samplesheets validate.
- [ ] Full local validation suite passes.
- [ ] Container smoke test passes when Docker is available.
- [ ] Package export works from a completed run.

## Scope Boundaries

- [ ] Release notes state software/workflow validation only.
- [ ] Biological interpretation and manuscript-grade conclusions are not claimed.
- [ ] Optional heavy tools are clearly marked as optional.
- [ ] Any required external databases are user-provided local paths.

## GitHub Release

- [ ] Main branch is clean and pushed.
- [ ] CI passes on GitHub.
- [ ] Release tag is created from the intended commit.
- [ ] Release description links validation evidence and limitations.
