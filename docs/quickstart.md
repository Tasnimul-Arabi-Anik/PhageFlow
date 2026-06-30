# PhageFlow Quickstart

This guide is for a first-time user who wants to copy and paste commands from the repository root.

PhageFlow analyzes already sequenced bacteriophage genome FASTA files. It does not design genomes, modify hosts, expand host range, or provide wet-lab instructions.

## 1. Start Here

Open a terminal in the repository root, then run:

```bash
bash phageflow/install.sh
bash phageflow/bin/phageflow doctor
```


Optional publication tools can be installed later without rebuilding everything:

```bash
bash phageflow/bin/phageflow install --with publication
bash phageflow/bin/phageflow doctor --with publication
```

Use `--with lite` for tRNAscan-SE/BACPHLIP/ABRicate, `--with structure` for Phold, `--with phylogeny` for MAFFT/IQ-TREE/trimAl, or `--with all` for every optional group. These commands install executables only; large databases still need to be supplied through the workflow parameters.

What this does:

- Installs missing tools into `phageflow/.phageflow-env` if needed.
- Reuses existing tools from your `PATH` if they are already available.
- Prints versions for Nextflow, Python, MMseqs2, BLAST, pandas, matplotlib, and seaborn.

To remove the default PhageFlow environment later:

```bash
rm -rf phageflow/.phageflow-env
```

## 2. Run The Built-In Test

Run the bundled validation dataset:

```bash
bash phageflow/bin/phageflow test
```

Expected success message:

```text
PhageFlow validation passed.
```

Expected output folder:

```text
phageflow_test_results/
```

Open the main report:

```bash
ls phageflow_test_results/99_report/index.html
```

## 3. Run One Phage Genome

Use this command first if you only have one phage FASTA:

```bash
bash phageflow/bin/phageflow run \
  --input phageflow/assets/test_data/toy_phage_a.fasta \
  --pangenome_method none \
  --outdir beginner_single_phage_results
```

Validate the output:

```bash
bash phageflow/bin/phageflow validate --outdir beginner_single_phage_results
```

Create a sanitized artifact summary without rerunning the workflow:

```bash
bash phageflow/bin/phageflow summarize \
  --outdir beginner_single_phage_results \
  --output beginner_single_phage_summary.json
```

Create a report/QA package:

```bash
bash phageflow/bin/phageflow package \
  --outdir beginner_single_phage_results \
  --output beginner_single_phage_phageflow_package.tar.gz
```

Create a conservative optional-screen summary:

```bash
bash phageflow/bin/phageflow safety-summary \
  --outdir beginner_single_phage_results \
  --output beginner_single_phage_safety_summary.tsv
```

Create a conservative optional-tool artifact summary:

```bash
bash phageflow/bin/phageflow optional-summary \
  --root beginner_single_phage_results \
  --output beginner_single_phage_optional_tool_summary.tsv
```

Create a structural-artifact inventory if structural outputs are present:

```bash
bash phageflow/bin/phageflow structural-summary \
  --outdir beginner_single_phage_results \
  --output beginner_single_phage_structural_summary.tsv
```

Expected output:

```text
beginner_single_phage_results/99_report/index.html
beginner_single_phage_results/99_report/figures/
beginner_single_phage_results/99_report/tables/
beginner_single_phage_results/99_report/tables/optional_tool_summary.tsv
```

Use `--pangenome_method none` for a single genome because pangenome clustering is most useful for two or more related phage genomes.

## 4. Run A Small Comparative Cohort

Use a samplesheet when you have a query phage plus similar reference phages:

```bash
bash phageflow/bin/phageflow run \
  --input phageflow/assets/test_data/phage_samplesheet.tsv \
  --host_samplesheet phageflow/assets/test_data/host_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir beginner_cohort_host_results
```

Validate the output:

```bash
bash phageflow/bin/phageflow validate \
  --outdir beginner_cohort_host_results \
  --require-pangenome-rows
```

Summarize or package the completed cohort run:

```bash
bash phageflow/bin/phageflow summarize \
  --outdir beginner_cohort_host_results \
  --output beginner_cohort_host_summary.json

bash phageflow/bin/phageflow package \
  --outdir beginner_cohort_host_results \
  --output beginner_cohort_host_phageflow_package.tar.gz
```

When Docker is available, the container smoke test can be run separately:

```bash
bash phageflow/bin/phageflow container-smoke
```

If you run both MMseqs and RBH pangenome modes, compare their completed summaries without rerunning either workflow:

```bash
bash phageflow/bin/phageflow pangenome-sensitivity \
  --left results/my_phage_cohort_mmseqs \
  --right results/my_phage_cohort_rbh \
  --output pangenome_sensitivity.tsv
```

Expected output:

```text
beginner_cohort_host_results/04_comparative/intergenomic_similarity/intergenomic_similarity_matrix.tsv
beginner_cohort_host_results/04_comparative/mmseqs_pangenome/pangenome_summary.tsv
beginner_cohort_host_results/06_host_context/host_context.tsv
beginner_cohort_host_results/99_report/index.html
beginner_cohort_host_results/99_report/figures/intergenomic_similarity_heatmap.tiff
beginner_cohort_host_results/99_report/figures/pangenome_presence_absence_heatmap.tiff
```


## 5. Optional Marker-Gene Tree

Use this when you have marker proteins for at least three related genomes:

```bash
bash phageflow/bin/phageflow run \
  --input phageflow/assets/test_data/marker_tree_samplesheet.tsv \
  --pangenome_method none \
  --run_marker_tree true \
  --marker_faa phageflow/assets/test_data/toy_marker_proteins.faa \
  --marker_source marker_faa \
  --marker_tree_engine simple \
  --outdir beginner_marker_tree_results
```

Validate the marker-tree output:

```bash
bash phageflow/bin/phageflow validate \
  --outdir beginner_marker_tree_results \
  --expect-marker-tree
```

Expected marker-tree outputs:

```text
beginner_marker_tree_results/04_comparative/marker_phylogeny/trees/terminase_large.nwk
beginner_marker_tree_results/99_report/tables/marker_tree_summary.tsv
beginner_marker_tree_results/99_report/figures/marker_tree_terminase_large.tiff
```

For publication runs, install phylogeny tools and use `--marker_tree_engine iqtree2` instead of `simple`.

## 6. Prepare Your Own Inputs

For one phage genome:

```bash
bash phageflow/bin/phageflow run \
  --input my_phage.fasta \
  --pangenome_method none \
  --outdir results/my_phage
```

For multiple phage genomes, create `phage_samplesheet.tsv`:

```text
sample_id	fasta	role	host_id	accession
my_phage	/path/to/my_phage.fasta	query	host_1
ref_phage_1	/path/to/ref_phage_1.fasta	reference
ref_phage_2	/path/to/ref_phage_2.fasta	reference
```

Then run:

```bash
bash phageflow/bin/phageflow run \
  --input phage_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/my_phage_cohort
```

If you also have a host genome, create `host_samplesheet.tsv`:

```text
host_id	fasta	taxon	accession
host_1	/path/to/host.fasta	Salmonella enterica
```

Then run:

```bash
bash phageflow/bin/phageflow run \
  --input phage_samplesheet.tsv \
  --host_samplesheet host_samplesheet.tsv \
  --pangenome_method mmseqs \
  --outdir results/my_phage_host_context
```

## 7. What To Read First

Start with these files:

```text
<outdir>/99_report/index.html
<outdir>/99_report/important_files.tsv
<outdir>/99_report/tables/fasta_stats_combined.tsv
<outdir>/99_report/tables/cohort_similarity_summary.tsv
<outdir>/99_report/tables/intergenomic_similarity_summary.tsv
<outdir>/99_report/tables/intergenomic_similarity_matrix.tsv
<outdir>/99_report/tables/marker_tree_summary.tsv
<outdir>/99_report/tables/marker_provenance.tsv
<outdir>/99_report/tables/marker_topology_consistency.tsv
<outdir>/99_report/tables/pangenome_summary.tsv
<outdir>/99_report/tables/host_context.tsv
<outdir>/99_report/tables/claim_evidence_matrix.tsv
```

The report figures are saved as PNG, TIFF, PDF, and SVG:

```text
<outdir>/99_report/figures/
```

## 8. Important Interpretation Notes

- BLASTN intergenomic similarity is useful for comparing related phage genomes because it combines nucleotide identity with reciprocal genome coverage.
- Marker-gene trees are useful for checking whether a conserved protein topology agrees with whole-genome similarity.
- The default MMseqs2 pangenome is useful for reproducible software testing and exploratory comparisons.
- The bundled lightweight ORF predictor keeps PhageFlow easy to run, but it can overpredict proteins.
- For final manuscript-grade pangenome biology, annotate every genome consistently with a phage-grade annotator such as Pharokka/PHANOTATE or Prodigal-GV, then interpret pangenome content.
- Host-context GC and tetranucleotide comparisons are supportive context, not proof of host range.

## 9. Troubleshooting

If `conda`, `mamba`, or `micromamba` is missing, install Miniconda or Mambaforge and rerun:

```bash
bash phageflow/install.sh
```

If a run fails, check:

```bash
ls -lah work/
tail -n 80 .nextflow.log
```

If validation fails, set the output folder name first, then inspect the validation report:

```bash
OUTDIR=beginner_cohort_host_results
cat "$OUTDIR/99_report/phageflow_validation_report.tsv"
```

If you want a removable environment outside the repository:

```bash
PHAGEFLOW_ENV_PREFIX=/tmp/phageflow-env bash phageflow/bin/phageflow install
PHAGEFLOW_ENV_PREFIX=/tmp/phageflow-env bash phageflow/bin/phageflow test
```

Remove it later with:

```bash
rm -rf /tmp/phageflow-env
```
