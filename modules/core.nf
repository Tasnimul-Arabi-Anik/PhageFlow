process VALIDATE_SAMPLESHEET {
    tag "validate_inputs"
    publishDir "${params.outdir}/00_inputs", mode: 'copy'

    input:
    val input_path

    output:
    path "samplesheet.normalized.tsv", emit: samplesheet
    path "validation_summary.tsv", emit: validation

    script:
    """
    python3 ${projectDir}/bin/validate_samplesheet.py \
        --input "${input_path}" \
        --outdir .
    """
}

process FASTA_STATS {
    tag "${sample_id}"
    publishDir "${params.outdir}/01_qc/fasta_stats", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.fasta_stats.tsv"), emit: stats

    script:
    """
    python3 ${projectDir}/bin/fasta_stats.py \
        --sample-id "${sample_id}" \
        --fasta "${fasta}" \
        --output "${sample_id}.fasta_stats.tsv"
    """
}

process SIMPLE_ORF_PREDICT {
    tag "${sample_id}"
    publishDir "${params.outdir}/02_annotation/lightweight_orfs", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.faa"), emit: faa
    tuple val(sample_id), path("${sample_id}.ffn"), emit: ffn
    tuple val(sample_id), path("${sample_id}.gff"), emit: gff
    tuple val(sample_id), path("${sample_id}.orf_summary.tsv"), emit: summary

    script:
    """
    python3 ${projectDir}/bin/simple_orf_predict.py \
        --sample-id "${sample_id}" \
        --fasta "${fasta}" \
        --min-aa ${params.min_orf_aa} \
        --faa "${sample_id}.faa" \
        --ffn "${sample_id}.ffn" \
        --gff "${sample_id}.gff" \
        --summary "${sample_id}.orf_summary.tsv"
    """
}

process CODON_USAGE {
    tag "${sample_id}"
    publishDir "${params.outdir}/03_codon_usage", mode: 'copy'

    input:
    tuple val(sample_id), path(ffn)

    output:
    tuple val(sample_id), path("${sample_id}.codon_counts.tsv"), emit: counts
    tuple val(sample_id), path("${sample_id}.codon_summary.tsv"), emit: summary

    script:
    """
    python3 ${projectDir}/bin/codon_usage.py \
        --sample-id "${sample_id}" \
        --ffn "${ffn}" \
        --counts "${sample_id}.codon_counts.tsv" \
        --summary "${sample_id}.codon_summary.tsv"
    """
}

process BUILD_REPORT {
    tag "report"
    publishDir "${params.outdir}/99_report", mode: 'copy'

    input:
    path validation
    path fasta_stats
    path orf_summaries
    path codon_summaries
    path cohort_summary
    path cohort_pairwise
    path cohort_duplicates
    path intergenomic_summary
    path intergenomic_pairs
    path intergenomic_similarity_matrix
    path intergenomic_distance_matrix
    path intergenomic_note
    path marker_summary
    path marker_presence
    path marker_topology
    path marker_provenance
    path marker_note
    path marker_trees
    path pangenome_summary
    path pangenome_presence_absence
    path pangenome_metadata
    path host_context
    path host_adaptation
    path host_rscu
    path crispr_matches
    path crispr_summary

    output:
    path "index.html", emit: html
    path "phageflow_report.md", emit: markdown
    path "figures", emit: figures
    path "tables", emit: tables
    path "important_files.tsv", emit: important_files
    path "validation_manifest.json", emit: validation_manifest
    path "software_versions.tsv", emit: software_versions
    path "params.json", emit: params_json
    path "runtime_summary.tsv", emit: runtime_summary

    script:
    def fastaArgs = fasta_stats.collect { "--fasta-stats ${it}" }.join(' ')
    def orfArgs = orf_summaries.collect { "--orf-summary ${it}" }.join(' ')
    def codonArgs = codon_summaries.collect { "--codon-summary ${it}" }.join(' ')
    """
    python3 ${projectDir}/bin/build_report.py \
        --validation "${validation}" \
        ${fastaArgs} \
        ${orfArgs} \
        ${codonArgs} \
        --cohort-summary "${cohort_summary}" \
        --cohort-pairwise "${cohort_pairwise}" \
        --cohort-duplicates "${cohort_duplicates}" \
        --intergenomic-summary "${intergenomic_summary}" \
        --intergenomic-pairs "${intergenomic_pairs}" \
        --intergenomic-similarity-matrix "${intergenomic_similarity_matrix}" \
        --intergenomic-distance-matrix "${intergenomic_distance_matrix}" \
        --intergenomic-note "${intergenomic_note}" \
        --marker-summary "${marker_summary}" \
        --marker-presence "${marker_presence}" \
        --marker-topology "${marker_topology}" \
        --marker-provenance "${marker_provenance}" \
        --marker-note "${marker_note}" \
        --marker-trees "${marker_trees}" \
        --pangenome-summary "${pangenome_summary}" \
        --pangenome-presence-absence "${pangenome_presence_absence}" \
        --pangenome-metadata "${pangenome_metadata}" \
        --host-context "${host_context}" \
        --host-adaptation "${host_adaptation}" \
        --host-rscu "${host_rscu}" \
        --crispr-matches "${crispr_matches}" \
        --crispr-summary "${crispr_summary}" \
        --pangenome-method "${params.pangenome_method}" \
        --output-mode "${params.output_mode}" \
        --min-orf-aa ${params.min_orf_aa} \
        --kmer-size ${params.kmer_size} \
        --duplicate-jaccard ${params.duplicate_jaccard} \
        --run-intergenomic-similarity ${params.run_intergenomic_similarity} \
        --ani-min-identity ${params.ani_min_identity} \
        --ani-min-aln-len ${params.ani_min_aln_len} \
        --ani-max-evalue ${params.ani_max_evalue} \
        --ani-max-genomes ${params.ani_max_genomes} \
        --run-marker-tree ${params.run_marker_tree} \
        --marker-source "${params.marker_source}" \
        --marker-kinds "${params.marker_kinds}" \
        --marker-min-genomes ${params.marker_min_genomes} \
        --marker-tree-engine "${params.marker_tree_engine}" \
        --marker-bootstrap ${params.marker_bootstrap} \
        --run-crispr-spacer-match ${params.run_crispr_spacer_match} \
        --crispr-min-identity ${params.crispr_min_identity} \
        --crispr-min-coverage ${params.crispr_min_coverage} \
        --host-min-orf-aa ${params.host_min_orf_aa} \
        --host-use-prodigal ${params.host_use_prodigal} \
        --pan-min-seq-id ${params.pan_min_seq_id} \
        --pan-min-coverage ${params.pan_min_coverage} \
        --output-html index.html \
        --output-md phageflow_report.md \
        --figures-dir figures \
        --important-files important_files.tsv \
        --validation-manifest validation_manifest.json \
        --software-versions software_versions.tsv \
        --params-json params.json \
        --runtime-summary runtime_summary.tsv
    """
}
