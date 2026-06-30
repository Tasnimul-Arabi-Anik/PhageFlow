# Publication Analysis Gap Review

Date checked: 2026-06-25

This review compares PhageFlow against analyses that repeatedly appear in bacteriophage genome characterization and comparative genomics papers. The goal is not to make the default workflow bulky; it is to keep a compact default while providing optional publication-grade modules when the user has the required databases and compute.

## Current Coverage

| Publication analysis area | PhageFlow status | Current or added route | Practical interpretation |
| --- | --- | --- | --- |
| Genome QC and basic genome statistics | Covered | `01_qc/fasta_stats` and report figures | Suitable for genome length, contig count, GC content, N50, and ambiguous-base reporting. |
| ORF prediction for lightweight testing | Covered, not final-grade | `02_annotation/lightweight_orfs` | Good for smoke tests and pangenome scaffolding; final papers should use consistent phage annotation such as Pharokka across all genomes. |
| Standardized phage annotation | Optional | `--run_pharokka true --pharokka_db ...` | Pharokka is a rapid standardized bacteriophage annotation tool and reports CDS, tRNA/tmRNA, CRISPR, PHROG, CARD, and VFDB-linked outputs depending on database availability. |
| Structural-homology annotation | Added optional hook | `--run_phold true` after Pharokka | Phold can improve annotation of less-characterized phage proteins using structure-informed searches. This is biologically valuable when many proteins remain hypothetical. |
| Genome quality/completeness and host contamination | Optional | `--run_checkv true --checkv_db ...` | CheckV is still important for quality tiering, completeness, terminal repeats, and host-contamination evidence. |
| Lifestyle prediction | Optional | `--run_bacphlip true` | Present, but the report should later parse probabilities into the dashboard instead of leaving only raw logs. |
| tRNA screening | Optional | `--run_trnascan true` | Present and useful for genome description and host-adaptation discussion. |
| AMR/virulence screening | Optional | `--run_abricate true --abricate_db vfdb/card/...` | Present, but final interpretation needs database-specific parsing and cautious wording because hits are not equivalent to phenotype. |
| Taxonomy, viral hallmarks, provirus/topology evidence | Added optional hook | `--run_genomad true --genomad_db ...` | geNomad adds virus/plasmid classification, viral taxonomy, hallmark genes, topology, genetic code, and integrated-virus evidence. |
| Cohort redundancy and duplicate screening | Covered | `04_comparative/cohort_similarity` | Useful for avoiding duplicate genomes and documenting cohort composition. |
| Pangenome/orthogroup analysis | Covered | `--pangenome_method mmseqs` or `rbh_blastp` | MMseqs is the scalable default; RBH-BLASTP is a conservative sensitivity analysis. |
| Synteny/gene-order visualization | Added optional hook | `--run_clinker true` after Pharokka | clinker can generate publication-quality comparative gene-order figures from GenBank files. Use for small to moderate cohorts, not hundreds of full genomes. |
| Whole-genome ANI/intergenomic similarity | Covered as lightweight local screen | `04_comparative/intergenomic_similarity` | BLASTN all-vs-all identity, reciprocal aligned fractions, conservative similarity score, similarity matrix, distance matrix, report table, and high-resolution heatmap are now generated. This is not a drop-in VIRIDIC replacement, but it addresses a common comparative-genomics expectation without a heavy database dependency. |
| Marker-gene phylogeny | Added optional module | `--run_marker_tree true` with marker FASTA or annotation-derived marker headers | Builds MAFFT-aligned marker trees, Newick outputs, high-resolution report figures, and topology consistency checks against BLASTN intergenomic distance. IQ-TREE2 is preferred for publication; a simple built-in engine supports validation. |
| Whole-proteome/genome-sharing network taxonomy | Missing | Not implemented | Useful for high-level taxonomy but heavier. Candidate tools include vConTACT2 or PhaBOX-like classification approaches. |
| Host prediction beyond supplied host | Improved optional host-context module | Host metadata, GC delta, tetranucleotide cosine, and optional CRISPR-spacer/protospacer matching from supplied spacer FASTA | Still not a full host-prediction system; future additions could include prophage similarity, host database matching, and optional iPHoP/PhaBOX-style host prediction. |
| Codon adaptation to host | Added host-context module output | Host-linked codon cosine, RSCU cosine, CAI-like score, preferred-codon match, and host-phage codon-distance figures | Useful as supporting host-context evidence when a host genome is supplied; not proof of host range or infectivity. |
| Protein structure prediction | Not default | Phold hook is more practical than AlphaFold for routine annotation | AlphaFold-style per-protein structures are too heavy for a compact default pipeline. Phold provides a more scalable publication-grade annotation route. |

## Enrichment Added In This Pass

- Added optional `GENOMAD` Nextflow process for taxonomy, hallmark genes, topology, provirus, and mobile-element context.
- Added optional `PHOLD` Nextflow process, automatically downstream of Pharokka, for structure-informed phage protein annotation.
- Added optional `CLINKER_SYNTENY` Nextflow process, automatically downstream of Pharokka, for comparative gene-order/synteny visualization.
- Added native BLASTN intergenomic similarity with reciprocal coverage-aware scoring, matrices, method note, report tables, and TIFF/PDF/SVG/PNG heatmap output.
- Added optional marker-gene phylogeny for terminase large subunit, portal protein, and major capsid/head protein markers.
- Added host-context codon adaptation/RSCU outputs and optional CRISPR spacer matching from existing spacer FASTA inputs.
- Updated `README.md` with publication-enrichment commands.
- Updated software version capture to include `genomad`, `phold`, and `clinker`.

## Next Highest-Value Additions

1. Parse optional tool outputs into the main dashboard. Running tools is useful, but publication value increases when the report summarizes CheckV quality, BACPHLIP probabilities, geNomad taxonomy, Pharokka function categories, and Phold annotation improvement.
2. Add prophage similarity or host-database matching to complement the supplied-host CRISPR/codon evidence.
3. Add an optional dedicated taxonomy similarity backend for users who want VIRIDIC-like or other formal phage taxonomy outputs beyond the lightweight BLASTN screen.

## Sources Checked

1. PhaBOX describes an integrated phage analysis scope that includes contig identification, lifestyle prediction, taxonomic classification, host prediction, and feature visualization: https://arxiv.org/abs/2303.15707
2. CheckV estimates viral genome completeness, host contamination, and closed-genome evidence for viral contigs: https://www.nature.com/articles/s41587-020-00774-7
3. Pharokka is described as a rapid standardized annotation tool for bacteriophage genomes/metagenomes and uses phage-oriented annotation resources including PHANOTATE/PHROGs/CARD/VFDB outputs: https://github.com/gbouras13/pharokka
4. Phold performs bacteriophage annotation using protein structural homology and is designed to improve annotation, especially for less-characterized phages: https://github.com/gbouras13/phold
5. geNomad provides virus/plasmid identification, viral taxonomy, provirus detection, topology, hallmark genes, genetic-code prediction, and functional annotation summaries: https://github.com/apcamargo/genomad
6. clinker generates publication-quality gene-cluster comparison figures from GenBank/GFF inputs and is practical for small to moderate comparative synteny displays: https://github.com/gamcil/clinker
