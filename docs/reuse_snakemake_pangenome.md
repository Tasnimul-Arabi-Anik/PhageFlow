# Snakemake Pangenome Deprecation Notes

The repository contains an older Snakemake pangenome workflow in `../pangenome/`. PhageFlow no longer treats that workflow as a first-class execution path.

Current policy:

- Native Nextflow `mmseqs` is the default pangenome method.
- Native Nextflow `rbh_blastp` ports the conservative reciprocal-best-hit logic from the Snakemake workflow.
- `legacy_snakemake_rbh` remains available only for one-release parity checks with previous outputs.
- Future PhageFlow development should improve the native Nextflow modules rather than adding new behavior to the Snakemake workflow.

Reusable logic already ported or represented natively:

- Protein-level orthogroup inference.
- Presence/absence matrix generation.
- Genome metadata and pangenome summary tables.
- High-resolution pangenome heatmap generation.
- Report and validation contracts.

Practical recommendation:

Use `--pangenome_method mmseqs` for the main cohort-scale pangenome, then optionally run `--pangenome_method rbh_blastp` as a conservative sensitivity analysis.
