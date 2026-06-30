# PhageFlow Analysis Capability Matrix

Date: 2026-07-01

This matrix separates validated lightweight defaults from heavy optional modules, import-only summaries, and deferred ideas. The intent is to keep PhageFlow comprehensive without making the default workflow slow, database-heavy, or biologically overclaimed.

## Lightweight Default

| Area | Current capability | Main artifacts | Boundary |
| --- | --- | --- | --- |
| Input QA | FASTA/samplesheet normalization and validation. | `00_inputs/validation_summary.tsv`, normalized samplesheet. | Input-contract validation only. |
| Genome architecture | Length, GC, ambiguous bases, GC/AT skew, longest N run, longest homopolymer, terminal-repeat heuristics. | `fasta_stats_combined.tsv`. | Descriptive assembly/genome metrics only. |
| ORF summary | Lightweight ORF prediction on both strands, ORF density, strand balance, length summaries. | `orf_summary_combined.tsv`, per-sample GFF/FAA/FFN. | QA-grade ORF calls; heavy annotation should use a consistent external annotator. |
| Codon composition | Codon usage, GC3, top codons. | `codon_summary_combined.tsv`. | Composition summary only. |
| Cohort redundancy | SHA256 duplicate groups and k-mer Jaccard similarity. | `cohort_pairwise_similarity.tsv`, duplicate groups. | Redundancy/context, not taxonomy. |
| Intergenomic similarity | BLASTN pairwise identity, coverage, similarity and distance matrices. | `intergenomic_similarity_*.tsv`. | Local pairwise comparison only. |
| Local reference context | Query/reference comparison against user-supplied local references. | `reference_context_*.tsv`. | Not public database discovery or classification. |
| Pangenome | Native MMseqs clustering default and RBH-BLASTP sensitivity backend. | `pangenome_summary.tsv`, `presence_absence.tsv`. | Method-dependent orthogroups. |
| Host context | Supplied host metadata, GC/tetranucleotide context, optional CRISPR spacer matching. | `host_context.tsv`, `host_codon_adaptation.tsv`, `crispr_spacer_*.tsv`. | Supplied-host context, not host-range proof. |
| Report QA | HTML/Markdown report, figures, manifests, software versions, claim-evidence matrix. | `99_report/`. | Software-validation evidence only. |

## Heavy Optional Wrappers

| Area | Tool support | How enabled | Boundary |
| --- | --- | --- | --- |
| tRNA calls | tRNAscan-SE | `--run_trnascan true` | Calls summarized as artifacts; no tRNA biology interpretation. |
| Lifestyle screen | BACPHLIP | `--run_bacphlip true` | Probabilities are optional evidence only. |
| Safety/feature screens | ABRicate | `--run_abricate true` | Hit names and feature values are not interpreted by PhageFlow. |
| Genome quality | CheckV | `--run_checkv true --checkv_db PATH` | Quality/completeness artifacts only. |
| Annotation | Pharokka | `--run_pharokka true --pharokka_db PATH` | Preferred heavy annotation path for formal reporting; summary remains conservative. |
| Classification context | geNomad | `--run_genomad true --genomad_db PATH` | Classification/taxonomy values are external-tool evidence. |
| Structural annotation | Phold | `--run_phold true --phold_db PATH` | Structural annotation artifacts summarized; values are not reinterpreted. |
| Synteny visualization | clinker | `--run_clinker true` with Pharokka outputs | HTML/alignment artifacts summarized; no gene-order interpretation. |
| Host prediction | iPHoP | `--run_iphop true --iphop_db PATH` | Host prediction evidence only; not host-range proof. |
| Marker phylogeny | MAFFT/IQ-TREE/trimAl or simple backend | `--run_marker_tree true` | Marker-tree context, not standalone taxonomy. |

## Import-Only Summaries

| Area | Supported input | Command/path | Boundary |
| --- | --- | --- | --- |
| Optional-tool artifact inventory | Existing optional output directories. | `phageflow optional-summary --root RUN` | Presence, shape, size, checksum only. |
| Optional-tool metric counts | Existing optional output directories. | `phageflow optional-metrics --root RUN` | Counted stable fields only; raw values are not printed. |
| Pangenome sensitivity | Completed MMseqs/RBH or other completed-run pangenome comparisons. | `phageflow pangenome-sensitivity --left RUN_A --right RUN_B --import-to-report RUN_A` | Metric deltas only. |
| Structural artifacts | Existing Phold-like structural directories. | `phageflow structural-summary --outdir RUN` | Artifact classes, shapes, sizes, checksums. |
| PhaBOX/PhaBOX2 | Completed PhaBOX/PhaBOX2 result directory named or passed as `<sample_id>.phabox`. | `--phabox-artifact PATH` or `05_optional/phabox/<sample_id>.phabox`. | Import-only counts/checksums; wrapper execution deferred. |

## Deferred

| Candidate | Why deferred |
| --- | --- |
| PhaBOX/PhaBOX2 wrapper execution | Valuable but database/CLI contract should be validated separately before PhageFlow runs it. Import-only support is implemented now. |
| vConTACT2-style network taxonomy | Useful for publication context but heavier, database-dependent, and easy to overclaim. |
| Read-based termini or packaging inference | Requires raw reads and separate validation data; current FASTA-only termini heuristics are intentionally limited. |
| Metagenomic viral discovery | Different input contract from assembled phage genome analysis. |
| Automated public-database taxonomy assignment | Requires database/version policy and stronger provenance guarantees. |

## Next High-Value Additions

1. Functional-category count summaries from consistent heavy annotation outputs, especially Pharokka/PHROG-style tables.
2. Optional import summary for vConTACT2-style network outputs, if users already have completed network analyses.
3. A small release checklist for deciding whether an output is default, heavy optional, import-only, or deferred.
