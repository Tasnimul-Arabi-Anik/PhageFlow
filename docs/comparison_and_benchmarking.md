# Comparison And Benchmarking Guide

PhageFlow does not replace specialized phage-analysis tools. Its role is to orchestrate lightweight default analyses, call selected heavy tools only when explicitly enabled, import completed external artifacts, validate the report contract, package outputs, and document provenance.

Use this guide to explain where PhageFlow fits, what it currently supports, and what still needs future validation before stronger claims can be made.

## Positioning Summary

| Tool or workflow | Primary role | PhageFlow relationship | Current support level | Boundary or limitation | Future validation needed |
| --- | --- | --- | --- | --- | --- |
| Pharokka | Phage genome annotation and standardized annotation outputs. | Optional annotation wrapper and source of compatible functional-category summaries. | Optional wrapper. | Requires explicit executable and database path; PhageFlow summarizes artifacts conservatively and does not reinterpret gene/product values. | Public example run with recorded Pharokka database version, command, optional summary rows, functional-category summary, and validator evidence. |
| CheckV | Viral genome quality, completeness, contamination, and closed-genome evidence. | Optional quality wrapper with report-level artifact summary. | Optional wrapper. | Requires explicit database path; quality values remain external-tool evidence. | Public heavy-tool subset confirming CheckV output capture and `--expect-publication-optionals` validation. |
| geNomad | Virus/plasmid classification context, taxonomy context, provirus/topology and hallmark-gene outputs. | Optional wrapper for completed geNomad artifacts and summary rows. | Optional wrapper. | Requires explicit database path; taxonomy/classification values are not treated as PhageFlow conclusions. | Database-versioned optional run with artifact summary, software-version capture, and validator evidence. |
| Phold | Structure-informed phage protein annotation. | Optional structure wrapper downstream of Pharokka-style annotation. | Optional wrapper. | Requires explicit database path and compatible upstream annotation output; no-hit outputs are artifact states, not biological conclusions. | Public subset confirming Phold output directory, no-hit handling if applicable, software version capture, and `--expect-phold` validation. |
| iPHoP | Database-backed host-prediction evidence. | Disabled-by-default optional host-prediction wrapper. | Optional wrapper. | Requires explicit database path; host predictions are not host-range proof. | Public host-prediction smoke run with recorded database manifest and `--expect-iphop` validation. |
| PhaBOX/PhaBOX2 | Integrated phage classification, host/lifestyle context, annotation, and related summaries. | Disabled-by-default optional wrapper and import-compatible artifact summary. | Optional wrapper plus import-aware summaries. | Requires explicit database path; taxonomy, lifestyle, host, and annotation values remain external-tool evidence. | Public heavy optional run with database provenance and `--expect-phabox` validation. |
| vConTACT2 | Whole-proteome network context and viral clustering/classification workflows. | Completed-output import is supported through network-summary style counts. Runnable execution remains deferred. | Import-only summary; runnable wrapper deferred. | PhageFlow does not run vConTACT2 or assign network taxonomy; it summarizes completed overview/network artifacts without interpreting cluster labels. | Stable runtime/database contract, small validation dataset, provenance policy, and validator expectations before adding a runnable wrapper. |
| multiPhATE2 | Integrated phage annotation workflow combining multiple annotation resources. | External workflow that can complement PhageFlow but is not wrapped. | Deferred or external comparison only. | Running or importing multiPhATE2 outputs would need a defined output contract, database policy, and license/provenance review. | Decide whether support should be import-only or runnable; then add sample outputs, schema expectations, and validation coverage. |
| nf-core-style workflows | Community workflow practices for configuration, profiles, CI, metadata, and reproducibility. | Design reference for workflow structure and release hygiene, not a direct dependency. | Design pattern reference. | PhageFlow is not currently packaged as an nf-core workflow; adopting nf-core conventions would require broader restructuring. | Optional future packaging review: profiles, schema, linting, containers, CI matrix, and release metadata. |

## What PhageFlow Adds Around Specialized Tools

PhageFlow is strongest when it provides:

- A lightweight default path for quick single-genome and small-cohort software validation.
- A single report bundle with figures, tables, manifests, software versions, parameters, runtime summaries, and checksums.
- Strict completed-run validation with explicit optional expectation flags.
- Sanitized summaries of optional outputs without printing raw annotation, taxonomy, host-prediction, feature, or sequence values.
- Package and summarize utilities for completed runs.
- Clear boundaries between workflow validation and biological interpretation.

Specialized tools remain the authoritative source for their own domain-specific outputs. PhageFlow records and validates their presence, shape, versions, and integration into the report contract.

## Benchmarking Approach

Do not benchmark PhageFlow as a replacement for annotation, classification, host prediction, or quality tools. Benchmark it as a workflow and reporting layer.

Recommended benchmark questions:

| Question | Suggested evidence | Boundary |
| --- | --- | --- |
| Does the default workflow run reproducibly on bundled and public examples? | Local validation command, GitHub CI, report manifests, checksums. | Software execution only. |
| Does the report contract stay stable across single-genome and cohort modes? | `99_report/tables/`, `99_report/figures/`, `validation_manifest.json`, strict validator. | Output completeness, not biological correctness. |
| Are optional modules captured when explicitly enabled? | Optional output directories, `optional_tool_summary.tsv`, `optional_tool_metrics.tsv`, software versions, matching `--expect-*` flags. | Artifact capture only. |
| Are heavy databases documented and reproducible? | `bin/phageflow db status`, database manifest, retrieval date, database version, generated run arguments. | Database availability/provenance, not result interpretation. |
| Are public examples reviewable without storing large files in Git? | Public example-data manifest, input checksums, command logs, release evidence note. | Provenance and reproducibility only. |

## Suggested Benchmark Tiers

Tier 1: bundled lightweight validation

- Run `bash bin/run_local_validation.sh`.
- Confirm strict validation passes.
- Use this tier for routine code and documentation release hygiene.

Tier 2: public lightweight real-data validation

- Use one single-genome public example and one small public cohort.
- Record source, retrieval date, checksum, command, commit, and validator output.
- Use this tier for a future `v0.5.0` real-data software-validation release.

Tier 3: database-backed optional validation

- Use a small public subset and explicitly supplied local databases.
- Validate CheckV, Pharokka, geNomad, Phold, iPHoP, PhaBOX/PhaBOX2, or a selected subset.
- Use this tier only when database versions and compute requirements are recorded.

Tier 4: external workflow comparison

- Compare PhageFlow report packaging and validation against outputs from external workflows such as vConTACT2-style network analysis or multiPhATE2-style annotation.
- Prefer import-only summaries first.
- Add runnable wrappers only after the scope gate, output contract, and validation data are available.

## Support-Level Definitions

Default:

- Runs in the normal lightweight workflow without large databases or heavy optional dependencies.

Optional wrapper:

- Disabled by default.
- Requires explicit `--run_* true` and executable/database inputs when needed.
- Writes outputs under the PhageFlow report contract.
- Has validator expectations for completed outputs.

Import-only:

- Does not run the external tool.
- Reads completed external artifacts and reports counts, shapes, checksums, or broad categories.
- Avoids raw values and biological interpretation.

Deferred:

- Not implemented as a runnable or import path.
- Requires a stronger input contract, database/version policy, license/provenance review, runtime validation, or biological-validation plan.

## Practical Recommendation

Keep PhageFlow's default lightweight and validated. Add heavy comparisons in layers:

1. Record public example-data policy and provenance.
2. Run public lightweight examples.
3. Run selected heavy optional tools with explicit local databases.
4. Import completed external workflow artifacts where safe.
5. Only then consider new runnable wrappers.

This keeps the pipeline comprehensive without making routine runs fragile or overclaiming what the software validation proves.
