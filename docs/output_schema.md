# PhageFlow Output Schema

This guide summarizes the main files produced under `99_report/` and `99_report/tables/`. It is intended for software review, run auditing, and downstream parser development. It does not define biological truth, taxonomy, host range, infectivity, safety, or manuscript-grade conclusions.

PhageFlow table schemas are stable enough for completed-run review, but optional modules can produce `not_run`, `skipped`, `available_no_table_rows`, or no-result rows depending on enabled tools and available inputs. Treat table values as software artifacts unless a separate domain-validation plan is in place.

## Report-Level Files

### `index.html`

- Purpose: Human-readable dashboard for the completed run.
- When produced: Every successful workflow run.
- Important content groups: Run status cards, key table previews, figure links, limitations.
- Interpretation boundary: Dashboard summaries are workflow evidence only.
- Related validator flag: Always required by `bin/validate_phageflow_run.py`.

### `phageflow_report.md`

- Purpose: Markdown companion report for lightweight review and packaging.
- When produced: Every successful workflow run.
- Important content groups: Run summary, key output pointers, limitations.
- Interpretation boundary: Does not replace domain review.
- Related validator flag: Always required by `bin/validate_phageflow_run.py`.

### `important_files.tsv`

- Purpose: Manifest of key report, QA, table, method-note, and figure files.
- When produced: Every successful workflow run.
- Important columns: `category`, `path`, `description`.
- Interpretation boundary: File inventory only; descriptions are not biological claims.
- Related validator flag: Always required by `bin/validate_phageflow_run.py`.

### `software_versions.tsv`

- Purpose: Captures detected runtime and optional-tool versions or availability status.
- When produced: Every successful workflow run.
- Important columns: `tool`, `version_or_status`.
- Interpretation boundary: Provenance and reproducibility evidence only.
- Related validator flag: Always required; optional-module expectation flags also inspect this file for relevant tool availability.

### `params.json`

- Purpose: Captures selected report/workflow parameters and summary counters.
- When produced: Every successful workflow run.
- Important fields: Pangenome method, marker-tree settings, similarity thresholds, host-context settings, optional summary counters.
- Interpretation boundary: Parameter provenance only. Current PhageFlow writes `params.json`; it does not write `parameters.tsv`.
- Related validator flag: Always required by `bin/validate_phageflow_run.py`.

### `runtime_summary.tsv`

- Purpose: Compact key-value summary of report generation and major row counts.
- When produced: Every successful workflow run.
- Important columns: `metric`, `value`.
- Interpretation boundary: Runtime/report accounting only.
- Related validator flag: Always required by `bin/validate_phageflow_run.py`.

### `validation_manifest.json`

- Purpose: Report-level QA manifest with Boolean and count checks from report generation.
- When produced: Every successful workflow run.
- Important fields: `report_complete`, `figures_generated`, `figure_manifest_rows`, row-count fields for major table groups.
- Interpretation boundary: Completeness metadata only. Current PhageFlow writes `validation_manifest.json`; it does not write `validation_manifest.tsv`.
- Related validator flag: Always required; the strict validator requires `report_complete` to be true when the file exists.

## Core Tables

### `validation_summary.tsv`

- Purpose: Summarizes normalized input validation.
- When produced: Every successful workflow run.
- Important columns or groups: Input counts, validation status, role/metadata checks.
- Interpretation boundary: Input-contract validation only.
- Related validator flag: Always required as `00_inputs/validation_summary.tsv` and copied into `99_report/tables/`.

### `fasta_stats_combined.tsv`

- Purpose: Combined genome-level FASTA statistics.
- When produced: Every successful workflow run.
- Important columns or groups: Sample ID, contig/genome length metrics, GC metrics, N content, N50, exact-terminal-repeat heuristics.
- Interpretation boundary: Descriptive assembly statistics only; terminal-repeat heuristics are not packaging inference.
- Related validator flag: Always required.

### `orf_summary_combined.tsv`

- Purpose: Summary of lightweight ORF prediction outputs.
- When produced: Every successful workflow run.
- Important columns or groups: Sample ID, ORF count, coding density, strand balance, ORF length summaries.
- Interpretation boundary: Lightweight ORF calls support workflow QA and scaffolding; use a consistent phage annotation backend before manuscript biological interpretation.
- Related validator flag: Always required.

### `codon_summary_combined.tsv`

- Purpose: Combined coding-sequence and codon-composition summary.
- When produced: Every successful workflow run.
- Important columns or groups: Sample ID, coding sequence counts, codon totals, GC3/composition metrics.
- Interpretation boundary: Descriptive sequence-composition evidence only.
- Related validator flag: Always required.

### `cohort_similarity_summary.tsv`

- Purpose: Summarizes k-mer similarity and duplicate-screen status for the cohort.
- When produced: Every successful workflow run, including single-genome runs with skipped/singleton status.
- Important columns or groups: Cohort size, pair count, duplicate/near-duplicate status, maximum similarity metrics.
- Interpretation boundary: Local redundancy and similarity screening only; not taxonomy or species assignment.
- Related validator flag: Always required.

### `cohort_pairwise_similarity.tsv`

- Purpose: Pairwise k-mer similarity source table.
- When produced: Every successful workflow run; can be empty for single-genome contexts.
- Important columns or groups: Sample pair identifiers and k-mer similarity metrics.
- Interpretation boundary: Local pairwise similarity only.
- Related validator flag: Required table; zero data rows are allowed for single-genome contexts.

### `cohort_duplicate_groups.tsv`

- Purpose: Duplicate or near-duplicate group summary used by the report.
- When produced: Every successful workflow run.
- Important columns or groups: Group ID, member samples, duplicate status.
- Interpretation boundary: Workflow duplicate-screen evidence only.
- Related validator flag: Included in `important_files.tsv`; not currently a required strict-validator table.

## Intergenomic Similarity Tables

### `intergenomic_similarity_summary.tsv`

- Purpose: Summarizes BLASTN-derived intergenomic similarity status and top-level metrics.
- When produced: Every successful workflow run; single-genome runs are marked skipped/singleton.
- Important columns or groups: Status, sample counts, pair counts, maximum identity/coverage/similarity metrics.
- Interpretation boundary: Conservative local similarity summary; not a formal VIRIDIC replacement or public taxonomy assignment.
- Related validator flag: Always required.

### `intergenomic_similarity_pairs.tsv`

- Purpose: Pairwise BLASTN identity, aligned fraction, and conservative similarity score table.
- When produced: When intergenomic similarity is enabled; can have zero rows for single-genome runs.
- Important columns or groups: Query/reference sample pair, identity, reciprocal aligned fractions, similarity score.
- Interpretation boundary: Local whole-genome similarity evidence only.
- Related validator flag: Required table; zero data rows are allowed for single-genome contexts.

### `intergenomic_similarity_matrix.tsv`

- Purpose: Matrix form of BLASTN-derived similarity scores.
- When produced: Every successful workflow run when report generation completes.
- Important columns or groups: Sample ID rows and sample ID columns.
- Interpretation boundary: Visualization/report source only; not biological classification.
- Related validator flag: Always required and contributes to `report_complete`.

### `intergenomic_distance_matrix.tsv`

- Purpose: Distance-matrix transform used for marker-tree consistency checks and reporting.
- When produced: Every successful workflow run when intergenomic similarity artifacts exist.
- Important columns or groups: Sample ID rows and sample ID columns.
- Interpretation boundary: Derived software metric only.
- Related validator flag: Always required.

### `intergenomic_similarity_note.md`

- Purpose: Method note describing the intergenomic similarity calculation.
- When produced: Every successful workflow run.
- Important content groups: Method, thresholds, limitations.
- Interpretation boundary: Method documentation only.
- Related validator flag: Listed in `important_files.tsv`; not a TSV schema.

## Local Reference Context Tables

### `reference_context_summary.tsv`

- Purpose: Summarizes comparison against user-supplied local reference rows.
- When produced: Every successful workflow run; status can indicate skipped when no references or no queries are supplied.
- Important columns or groups: Status, query/reference counts, pair counts, nearest-reference counts.
- Interpretation boundary: Local user-provided reference context only; not public database discovery or taxonomy assignment.
- Related validator flag: Required table; `--expect-reference-context` requires nonempty completed reference-context outputs.

### `reference_context_pairs.tsv`

- Purpose: All local query/reference metric pairs.
- When produced: When local reference rows and query rows are present; otherwise can be empty.
- Important columns or groups: Query sample, reference sample, similarity/distance metrics, duplicate flags.
- Interpretation boundary: Local comparison metrics only.
- Related validator flag: Required table; zero data rows are allowed unless reference context is expected.

### `reference_context_nearest.tsv`

- Purpose: Nearest local reference per query sample.
- When produced: When local query/reference comparisons complete; otherwise can be empty.
- Important columns or groups: Query sample, nearest reference, similarity/distance summary fields.
- Interpretation boundary: Nearest supplied reference only; not classification against public databases.
- Related validator flag: Required table; `--expect-reference-context` requires expected reference-context artifacts.

### `reference_context_note.md`

- Purpose: Method note for local reference-context calculations.
- When produced: Every successful workflow run.
- Important content groups: Scope, method, limitations.
- Interpretation boundary: Method documentation only.
- Related validator flag: Listed in `important_files.tsv`; not a TSV schema.

## Marker Phylogeny Tables

### `marker_tree_summary.tsv`

- Purpose: Summary of marker-gene phylogeny status.
- When produced: Every successful workflow run; status can be skipped when marker-tree mode is disabled or no suitable markers are available.
- Important columns or groups: Status, marker count, engine, generated tree count.
- Interpretation boundary: Marker trees require suitable markers and are not standalone classification.
- Related validator flag: Always required; `--expect-marker-tree` requires completed marker-tree outputs and TIFF tree figures.

### `marker_presence.tsv`

- Purpose: Candidate marker presence/absence and selection table.
- When produced: Every successful workflow run; can be empty when marker-tree mode is skipped.
- Important columns or groups: Marker kind, sample coverage, candidate status.
- Interpretation boundary: Marker-selection provenance only.
- Related validator flag: Required table; zero rows are allowed unless marker-tree outputs are expected.

### `marker_topology_consistency.tsv`

- Purpose: Compares marker-tree topology against intergenomic-distance context.
- When produced: When marker trees are built; can be empty otherwise.
- Important columns or groups: Marker, comparison status, consistency metrics.
- Interpretation boundary: Software consistency check only, not biological correctness.
- Related validator flag: Required table; `--expect-marker-tree` requires relevant marker-tree artifacts.

### `marker_provenance.tsv`

- Purpose: Alignment/tree provenance for marker-gene outputs.
- When produced: Every successful workflow run; can contain skipped status.
- Important columns or groups: Marker, alignment path, tree path, engine, status.
- Interpretation boundary: Provenance only.
- Related validator flag: Required table; `--expect-marker-tree` requires completed marker provenance.

### `marker_phylogeny_note.md`

- Purpose: Method note for marker-gene phylogeny.
- When produced: Every successful workflow run.
- Important content groups: Engine, marker-source behavior, limitations.
- Interpretation boundary: Method documentation only.
- Related validator flag: Listed in `important_files.tsv`; not a TSV schema.

## Pangenome Tables

### `pangenome_summary.tsv`

- Purpose: Summarizes pangenome backend status and orthogroup counts.
- When produced: Every successful workflow run.
- Important columns or groups: Method, status, core/accessory/singleton counts, sample count.
- Interpretation boundary: Orthogroups depend on selected backend and annotation consistency.
- Related validator flag: Always required; `--require-pangenome-rows` requires data rows.

### `presence_absence.tsv`

- Purpose: Orthogroup presence/absence matrix.
- When produced: Every successful workflow run; can be empty when pangenome mode is skipped.
- Important columns or groups: Orthogroup ID plus one column per sample.
- Interpretation boundary: Workflow pangenome artifact only; not a biological conclusion by itself.
- Related validator flag: Required table; zero rows are allowed unless pangenome rows are required.

### `genome_metadata.tsv`

- Purpose: Sample metadata accompanying pangenome outputs.
- When produced: Every successful workflow run with pangenome artifacts.
- Important columns or groups: Sample ID, role, host/accession metadata when supplied.
- Interpretation boundary: Input/run metadata only.
- Related validator flag: Always required.

## Host-Context Tables

### `host_context.tsv`

- Purpose: Host-linked composition and metadata context.
- When produced: Every successful workflow run; host-linked rows depend on supplied host metadata.
- Important columns or groups: Sample ID, host ID, GC/tetranucleotide composition fields, status.
- Interpretation boundary: Composition context only; not host-range proof or infectivity evidence.
- Related validator flag: Always required.

### `host_codon_adaptation.tsv`

- Purpose: Phage-host codon-adaptation and composition metrics.
- When produced: When host context/adaptation inputs are available; otherwise can be empty.
- Important columns or groups: Sample ID, host ID, codon-composition/adaptation metrics.
- Interpretation boundary: Composition/adaptation metrics only.
- Related validator flag: Required table; `--expect-host-adaptation` requires nonempty host-adaptation outputs and a TIFF figure.

### `host_codon_rscu.tsv`

- Purpose: Codon-level RSCU comparison table.
- When produced: When host codon adaptation is computed; otherwise can be empty.
- Important columns or groups: Sample ID, host ID, codon, phage/host RSCU fields.
- Interpretation boundary: Descriptive codon-composition comparison only.
- Related validator flag: Required table; zero rows are allowed unless host-adaptation outputs are expected.

### `crispr_spacer_matches.tsv`

- Purpose: Optional spacer/protospacer match table when CRISPR spacer matching is enabled.
- When produced: When `--run_crispr_spacer_match` is enabled and spacer inputs are provided; otherwise can be empty.
- Important columns or groups: Query/protospacer IDs, match identity/coverage fields, status.
- Interpretation boundary: Sequence-match evidence only; not host-range proof.
- Related validator flag: Required table; `--expect-crispr-hits` requires CRISPR hit outputs.

### `crispr_spacer_summary.tsv`

- Purpose: Summary status for optional CRISPR spacer matching.
- When produced: Every successful workflow run.
- Important columns or groups: Status, match counts, threshold parameters.
- Interpretation boundary: Software summary only.
- Related validator flag: Always required.

## Optional Tool Tables

### `optional_tool_summary.tsv`

- Purpose: Sanitized artifact inventory for optional tools.
- When produced: Every successful workflow run, with rows for expected/sample optional tool states.
- Important columns: `tool`, `scope`, `sample_id`, `status`, `artifact_count`, `primary_artifact_id`, `primary_artifact_type`, `records`, `columns`, `bytes`, `sha256`, `limitation`.
- Interpretation boundary: Counts, shapes, sizes, checksums, and broad artifact types only. It does not print or interpret annotation values, taxonomy labels, host-prediction values, feature names, or table cell values.
- Related validator flag: Required table; optional expectation flags such as `--expect-checkv-summary`, `--expect-iphop-summary`, and `--expect-optional` require matching available rows.

### `optional_tool_metrics.tsv`

- Purpose: Sanitized high-level metric counts from optional-tool artifacts.
- When produced: Every successful workflow run.
- Important columns: `tool`, `scope`, `sample_id`, `metric`, `status`, `value`, `source_records`, `source_columns`, `limitation`.
- Interpretation boundary: Metric counts only; no raw optional-tool values are printed or interpreted.
- Related validator flag: Required table; optional expectation flags require matching available metric rows.

### `functional_category_summary.tsv`

- Purpose: Broad functional-category counts from consistent heavy annotation outputs such as Pharokka category tables.
- When produced: Every successful workflow run; rows depend on available annotation artifacts.
- Important columns or groups: Sample ID, category, count, status, limitation.
- Interpretation boundary: Broad category counts only; not annotation-value interpretation.
- Related validator flag: Always required as a table; optional summaries can be inspected with optional expectation flags.

### `network_context_summary.tsv`

- Purpose: Import-only summary of completed network-analysis outputs, such as vConTACT2-style result directories.
- When produced: Only when `bin/phageflow network-summary --import-to-report` or the underlying utility imports a completed network context into a completed run.
- Important columns or groups: Artifact class, status, row/column or node/edge counts, file size/checksum fields.
- Interpretation boundary: Imported network artifact counts only. PhageFlow does not assign clusters, taxonomy, or biological meaning from these imports.
- Related validator flag: Not part of the core strict validator yet; included by `summarize` and `package` when imported.

## Report QA Tables

### `claim_evidence_matrix.tsv`

- Purpose: Maps software/workflow claims to supporting artifacts and limitations.
- When produced: Every successful workflow run.
- Important columns or groups: Claim, claim type, status, evidence path, limitation.
- Interpretation boundary: Software claim-to-artifact matrix only; it deliberately limits biological claims.
- Related validator flag: Always required.

### `figure_manifest.tsv`

- Purpose: Inventory of report figure exports.
- When produced: Every successful workflow run with report figures.
- Important columns: `figure_id`, `stem`, `extension`, `relative_path`, `bytes`, `sha256`.
- Interpretation boundary: Figure file provenance only; no visual interpretation.
- Related validator flag: Always required; strict validation checks that manifest rows cover generated PNG/TIFF/PDF/SVG files.

## Imported Completed-Run QA Tables

### `pangenome_sensitivity.tsv`

- Purpose: Completed-run comparison of pangenome summary metrics across two existing runs.
- When produced: Only when `bin/phageflow pangenome-sensitivity --import-to-report` is used.
- Important columns or groups: Metric name, left/right values, delta/status fields.
- Interpretation boundary: Method-sensitivity QA only; it does not decide which method is biologically correct.
- Related validator flag: Not part of the core strict validator; included by `summarize` and `package` when imported.

### `pangenome_sensitivity_summary.tsv`

- Purpose: Compact summary of imported pangenome-sensitivity comparison.
- When produced: Only when imported with `pangenome-sensitivity`.
- Important columns or groups: Row count, status counts, numeric delta counts, software-validation conclusion.
- Interpretation boundary: Completed-run QA only.
- Related validator flag: Not part of the core strict validator.

## Validator Flag Reference

- Always required by strict validation: `index.html`, `phageflow_report.md`, `important_files.tsv`, `validation_manifest.json`, `software_versions.tsv`, `params.json`, `runtime_summary.tsv`, and the core required tables in `bin/validate_phageflow_run.py`.
- `--require-pangenome-rows`: Requires populated pangenome presence/summary evidence.
- `--expect-reference-context`: Requires completed local reference-context outputs.
- `--expect-marker-tree`: Requires marker-tree outputs and TIFF tree figures.
- `--expect-host-adaptation`: Requires host codon-adaptation/RSCU outputs and host-adaptation TIFF figure.
- `--expect-crispr-hits`: Requires CRISPR spacer hit outputs.
- `--expect-optional`, `--expect-lite-optionals`, `--expect-publication-optionals`, and per-tool flags such as `--expect-iphop`: Require selected optional output directories/logs.
- Per-tool summary flags such as `--expect-checkv-summary` or `--expect-phabox-summary`: Require matching rows in `optional_tool_summary.tsv` and `optional_tool_metrics.tsv`.

