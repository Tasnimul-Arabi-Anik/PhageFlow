# Public Example Data Policy

This policy defines how PhageFlow can use public example data for software validation without bloating the repository or turning workflow output into biological interpretation.

## Purpose

Public example data should demonstrate that PhageFlow can run on real, externally sourced inputs and produce the expected software artifacts. These examples support workflow validation, output-schema review, and reproducibility checks. They do not establish taxonomy, host range, infectivity, safety status, or manuscript-grade biological conclusions.

## Allowed Input Types

Allowed examples:

- One complete assembled phage genome FASTA for a minimal single-genome run.
- A small related phage cohort FASTA or samplesheet for cohort-mode validation.
- A host-linked example where host metadata are public and can be used for context-only host reporting.
- A small optional heavy-tool subset for database-backed wrapper validation.

Deferred examples:

- Raw-read datasets until PhageFlow has a read-input contract.
- Metagenomic discovery datasets until a separate discovery workflow exists.
- Large public database mirrors committed into Git.
- Examples that require confidential, unpublished, restricted, or license-unclear data.

## Recording Accessions And Sources

For each public example, record provenance in a small text or TSV manifest, not in prose scattered across multiple files. Required fields:

```text
example_id
source_database_or_repository
accession_or_record_id
source_url_or_landing_page
retrieval_date
retrieval_command_or_manual_download_note
input_file_name
input_sha256
input_bytes
license_or_terms_checked
citation_or_reference
intended_validation_scope
```

Use stable public landing pages where possible. If an accession, file, or source changes, create a new example manifest entry rather than silently replacing the old record.

## Avoiding Large Files In Git

Do not commit large downloaded FASTA files, database files, tool outputs, or result archives.

Recommended pattern:

```text
docs/public_examples/<example_id>.tsv
docs/public_examples/<example_id>_commands.md
```

The manifest and command log can be tracked in Git. Downloaded inputs and generated results should remain outside the repository, for example:

```text
data/public_examples/<example_id>/
results/public_examples/<example_id>/
```

If a tiny public input is proposed for tracking, it must pass the repository-size gate in `.github/workflows/ci.yml` and its source, license, citation, checksum, and intended validation scope must be documented.

## Recording Checksums

Record SHA256 checksums for every externally downloaded input used in a validation run:

```bash
sha256sum data/public_examples/<example_id>/*
```

For completed PhageFlow outputs, prefer existing report manifests and sanitized inventory utilities:

```bash
bash bin/phageflow summarize \
  --outdir results/public_examples/<example_id> \
  --output results/public_examples/<example_id>_summary.json

bash bin/phageflow package \
  --outdir results/public_examples/<example_id> \
  --output results/public_examples/<example_id>_phageflow_package.tar.gz
```

Do not paste table contents, sequence strings, taxonomy values, host-prediction values, feature names, or annotation values into the policy or release notes.

## Recording Database Versions

For optional heavy tools, record the local database path and database provenance separately from the workflow command. Required fields:

```text
tool
database_root
database_path_parameter
database_version_or_release
database_retrieval_date
database_manifest_path
database_sha256_or_manifest_checksum_if_available
database_license_or_terms_checked
database_citation_or_reference
```

When using the PhageFlow database manager, keep the generated database manifest under the user-chosen database root and cite it in the validation notes:

```bash
bash bin/phageflow db status --db-root "$PHAGEFLOW_DB_ROOT"
bash bin/phageflow db run-args --db-root "$PHAGEFLOW_DB_ROOT" --tools all --shell
```

Database preparation is not a biological-validation result. It only records that the local database resources needed by optional wrappers were prepared or detected.

## Recording Commands

Every public example should have a command log that includes:

- PhageFlow git commit.
- Input manifest path.
- Workflow command.
- Validator command.
- Optional database argument command, if used.
- Runtime environment notes such as local, container, or remote workstation.
- Validation outcome.

Example structure:

```text
Example ID:
PhageFlow commit:
Input manifest:
Run command:
Validation command:
Database manifest:
Outcome:
Interpretation boundary:
```

Commands should use placeholder paths in user-facing docs unless the path is intentionally public and portable.

## Separating Software Validation From Biological Interpretation

Public example runs can support these claims:

- The workflow accepts the documented input type.
- Required output directories, tables, figures, manifests, and logs are produced.
- The strict validator passes with the correct expectation flags.
- Optional wrapper artifacts are present when the corresponding optional module was explicitly enabled and completed.

Public example runs must not be used alone to claim:

- Correct taxonomy or classification.
- Host range or host specificity.
- Infectivity, efficacy, or wet-lab outcome.
- Safety status or therapeutic suitability.
- Manuscript-grade biological conclusions.

Any biological interpretation must be written as a separate domain-review effort with appropriate references and expert review.

## Updating Release Evidence

Before a release that cites public example data, update:

```text
docs/validation_status.md
docs/release_checklist.md
docs/v<release>_real_data_validation.md
RELEASE_NOTES.md
```

Release evidence should include:

- Example IDs and validation scope.
- Retrieval dates and input checksums.
- PhageFlow commit.
- Workflow and validator commands.
- Database versions for optional heavy tools.
- Clear statement that the evidence supports software/workflow validation only.

Do not tag a release as real-data validated until the example provenance, commands, checksums, validator outcome, and interpretation boundary are all recorded.
