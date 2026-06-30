nextflow.enable.dsl = 2

include { VALIDATE_SAMPLESHEET; FASTA_STATS; SIMPLE_ORF_PREDICT; CODON_USAGE; BUILD_REPORT } from './modules/core'
include { COHORT_SIMILARITY; INTERGENOMIC_SIMILARITY; NO_INTERGENOMIC_SIMILARITY; REFERENCE_CONTEXT; MARKER_PHYLOGENY; NO_MARKER_PHYLOGENY; MMSEQS_PANGENOME; RBH_PANGENOME; NO_PANGENOME; RUN_LEGACY_SNAKEMAKE_PANGENOME } from './modules/comparative'
include { TRNASCAN; BACPHLIP; CHECKV; ABRICATE; PHAROKKA; GENOMAD; PHOLD; CLINKER_SYNTENY; IPHOP; OPTIONAL_TOOL_SUMMARY } from './modules/optional_tools'
include { HOST_CONTEXT_LIGHT; NO_HOST_CONTEXT } from './modules/host'

def paramEnabled(value) {
    if (value == null) {
        return false
    }
    if (value instanceof Boolean) {
        return value
    }
    def normalized = value.toString().trim().toLowerCase()
    return normalized in ['true', '1', 'yes', 'y', 'on']
}

workflow {
    if (!params.input) {
        exit 1, "Missing required input. Provide --input with a FASTA, FASTA directory, or samplesheet."
    }

    def allowed_pangenome_methods = ['none', 'mmseqs', 'rbh_blastp', 'legacy_snakemake_rbh']
    if (!allowed_pangenome_methods.contains(params.pangenome_method as String)) {
        exit 1, "Invalid --pangenome_method '${params.pangenome_method}'. Use one of: ${allowed_pangenome_methods.join(', ')}"
    }

    def allowed_output_modes = ['basic', 'important', 'all']
    if (!allowed_output_modes.contains(params.output_mode as String)) {
        exit 1, "Invalid --output_mode '${params.output_mode}'. Use one of: ${allowed_output_modes.join(', ')}"
    }

    resolved_input = params.input as String
    if (!resolved_input.startsWith('/')) {
        resolved_input = "${launchDir}/${resolved_input}"
    }
    input_ch = Channel.value(resolved_input)

    marker_faa_value = params.marker_faa ? params.marker_faa as String : 'null'
    if (marker_faa_value != 'null' && !marker_faa_value.startsWith('/')) {
        marker_faa_value = "${launchDir}/${marker_faa_value}"
    }

    crispr_spacers_value = params.crispr_spacers ? params.crispr_spacers as String : 'null'
    if (crispr_spacers_value != 'null' && !crispr_spacers_value.startsWith('/')) {
        crispr_spacers_value = "${launchDir}/${crispr_spacers_value}"
    }

    VALIDATE_SAMPLESHEET(input_ch)

    samples_ch = VALIDATE_SAMPLESHEET.out.samplesheet
        .splitCsv(header: true, sep: '\t')
        .map { row ->
            tuple(
                row.sample_id as String,
                file(row.fasta as String),
                (row.role ?: 'query') as String,
                (row.host_id ?: '') as String,
                (row.accession ?: '') as String
            )
        }

    FASTA_STATS(samples_ch)
    SIMPLE_ORF_PREDICT(samples_ch)
    CODON_USAGE(SIMPLE_ORF_PREDICT.out.ffn)
    COHORT_SIMILARITY(VALIDATE_SAMPLESHEET.out.samplesheet)

    if (paramEnabled(params.run_intergenomic_similarity)) {
        INTERGENOMIC_SIMILARITY(VALIDATE_SAMPLESHEET.out.samplesheet)
        intergenomic_summary_ch = INTERGENOMIC_SIMILARITY.out.summary
        intergenomic_pairs_ch = INTERGENOMIC_SIMILARITY.out.pairs
        intergenomic_similarity_matrix_ch = INTERGENOMIC_SIMILARITY.out.similarity_matrix
        intergenomic_distance_matrix_ch = INTERGENOMIC_SIMILARITY.out.distance_matrix
        intergenomic_note_ch = INTERGENOMIC_SIMILARITY.out.note
    } else {
        NO_INTERGENOMIC_SIMILARITY(VALIDATE_SAMPLESHEET.out.samplesheet)
        intergenomic_summary_ch = NO_INTERGENOMIC_SIMILARITY.out.summary
        intergenomic_pairs_ch = NO_INTERGENOMIC_SIMILARITY.out.pairs
        intergenomic_similarity_matrix_ch = NO_INTERGENOMIC_SIMILARITY.out.similarity_matrix
        intergenomic_distance_matrix_ch = NO_INTERGENOMIC_SIMILARITY.out.distance_matrix
        intergenomic_note_ch = NO_INTERGENOMIC_SIMILARITY.out.note
    }

    REFERENCE_CONTEXT(
        VALIDATE_SAMPLESHEET.out.samplesheet,
        COHORT_SIMILARITY.out.pairwise,
        intergenomic_pairs_ch,
        intergenomic_summary_ch
    )

    faa_collect_ch = SIMPLE_ORF_PREDICT.out.faa.map { sample_id, faa -> faa }.collect()

    if (paramEnabled(params.run_marker_tree)) {
        MARKER_PHYLOGENY(VALIDATE_SAMPLESHEET.out.samplesheet, faa_collect_ch, intergenomic_distance_matrix_ch, marker_faa_value)
        marker_summary_ch = MARKER_PHYLOGENY.out.summary
        marker_presence_ch = MARKER_PHYLOGENY.out.presence
        marker_topology_ch = MARKER_PHYLOGENY.out.topology
        marker_provenance_ch = MARKER_PHYLOGENY.out.provenance
        marker_note_ch = MARKER_PHYLOGENY.out.note
        marker_trees_ch = MARKER_PHYLOGENY.out.trees
    } else {
        NO_MARKER_PHYLOGENY(VALIDATE_SAMPLESHEET.out.samplesheet)
        marker_summary_ch = NO_MARKER_PHYLOGENY.out.summary
        marker_presence_ch = NO_MARKER_PHYLOGENY.out.presence
        marker_topology_ch = NO_MARKER_PHYLOGENY.out.topology
        marker_provenance_ch = NO_MARKER_PHYLOGENY.out.provenance
        marker_note_ch = NO_MARKER_PHYLOGENY.out.note
        marker_trees_ch = NO_MARKER_PHYLOGENY.out.trees
    }

    if (params.pangenome_method == 'mmseqs') {
        MMSEQS_PANGENOME(faa_collect_ch)
        pangenome_summary_ch = MMSEQS_PANGENOME.out.summary
        pangenome_presence_ch = MMSEQS_PANGENOME.out.presence_absence
        pangenome_metadata_ch = MMSEQS_PANGENOME.out.genome_metadata
    } else if (params.pangenome_method == 'rbh_blastp') {
        RBH_PANGENOME(faa_collect_ch)
        pangenome_summary_ch = RBH_PANGENOME.out.summary
        pangenome_presence_ch = RBH_PANGENOME.out.presence_absence
        pangenome_metadata_ch = RBH_PANGENOME.out.genome_metadata
    } else {
        NO_PANGENOME(VALIDATE_SAMPLESHEET.out.samplesheet)
        pangenome_summary_ch = NO_PANGENOME.out.summary
        pangenome_presence_ch = NO_PANGENOME.out.presence_absence
        pangenome_metadata_ch = NO_PANGENOME.out.genome_metadata
    }

    if (params.pangenome_method == 'legacy_snakemake_rbh') {
        RUN_LEGACY_SNAKEMAKE_PANGENOME(VALIDATE_SAMPLESHEET.out.samplesheet)
    }

    if (paramEnabled(params.run_trnascan)) {
        TRNASCAN(samples_ch)
        trnascan_artifacts_ch = TRNASCAN.out.table.map { sample_id, table -> table }.collect()
    } else {
        trnascan_artifacts_ch = Channel.value([])
    }

    if (paramEnabled(params.run_bacphlip)) {
        BACPHLIP(samples_ch)
        bacphlip_artifacts_ch = BACPHLIP.out.log.map { sample_id, log -> log }.collect()
    } else {
        bacphlip_artifacts_ch = Channel.value([])
    }

    if (paramEnabled(params.run_checkv)) {
        CHECKV(samples_ch)
        checkv_artifacts_ch = CHECKV.out.checkv_dir.map { sample_id, checkv_dir -> checkv_dir }.collect()
    } else {
        checkv_artifacts_ch = Channel.value([])
    }

    if (paramEnabled(params.run_abricate)) {
        ABRICATE(samples_ch)
        abricate_artifacts_ch = ABRICATE.out.table.map { sample_id, table -> table }.collect()
    } else {
        abricate_artifacts_ch = Channel.value([])
    }

    def needs_pharokka = paramEnabled(params.run_pharokka) || paramEnabled(params.run_phold) || paramEnabled(params.run_clinker)
    if (needs_pharokka) {
        PHAROKKA(samples_ch)
        pharokka_artifacts_ch = PHAROKKA.out.pharokka_dir.map { sample_id, pharokka_dir -> pharokka_dir }.collect()
    } else {
        pharokka_artifacts_ch = Channel.value([])
    }

    if (paramEnabled(params.run_genomad)) {
        GENOMAD(samples_ch)
        genomad_artifacts_ch = GENOMAD.out.genomad_dir.map { sample_id, genomad_dir -> genomad_dir }.collect()
        genomad_logs_ch = GENOMAD.out.log.map { sample_id, genomad_log -> genomad_log }.collect()
    } else {
        genomad_artifacts_ch = Channel.value([])
        genomad_logs_ch = Channel.value([])
    }

    if (paramEnabled(params.run_phold)) {
        PHOLD(PHAROKKA.out.pharokka_dir)
        phold_artifacts_ch = PHOLD.out.phold_dir.map { sample_id, phold_dir -> phold_dir }.collect()
        phold_logs_ch = PHOLD.out.log.map { sample_id, phold_log -> phold_log }.collect()
    } else {
        phold_artifacts_ch = Channel.value([])
        phold_logs_ch = Channel.value([])
    }

    if (paramEnabled(params.run_clinker)) {
        pharokka_dirs_ch = PHAROKKA.out.pharokka_dir.map { sample_id, pharokka_dir -> pharokka_dir }.collect()
        CLINKER_SYNTENY(pharokka_dirs_ch)
        clinker_artifacts_ch = CLINKER_SYNTENY.out.gbk_files
            .mix(CLINKER_SYNTENY.out.html)
            .mix(CLINKER_SYNTENY.out.alignments)
            .mix(CLINKER_SYNTENY.out.log)
            .mix(CLINKER_SYNTENY.out.note)
            .collect()
    } else {
        clinker_artifacts_ch = Channel.value([])
    }

    if (paramEnabled(params.run_iphop)) {
        IPHOP(samples_ch)
        iphop_artifacts_ch = IPHOP.out.iphop_dir.map { sample_id, iphop_dir -> iphop_dir }.collect()
        iphop_logs_ch = IPHOP.out.log.map { sample_id, iphop_log -> iphop_log }.collect()
    } else {
        iphop_artifacts_ch = Channel.value([])
        iphop_logs_ch = Channel.value([])
    }
    phabox_artifacts_ch = Channel.value([])

    OPTIONAL_TOOL_SUMMARY(
        VALIDATE_SAMPLESHEET.out.samplesheet,
        trnascan_artifacts_ch,
        bacphlip_artifacts_ch,
        checkv_artifacts_ch,
        abricate_artifacts_ch,
        pharokka_artifacts_ch,
        genomad_artifacts_ch,
        genomad_logs_ch,
        phold_artifacts_ch,
        phold_logs_ch,
        iphop_artifacts_ch,
        iphop_logs_ch,
        phabox_artifacts_ch,
        clinker_artifacts_ch
    )

    if (params.host_samplesheet && (params.host_samplesheet as String) != 'null') {
        resolved_host_input = params.host_samplesheet as String
        if (!resolved_host_input.startsWith('/')) {
            resolved_host_input = "${launchDir}/${resolved_host_input}"
        }
        host_input_ch = Channel.value(resolved_host_input)
        HOST_CONTEXT_LIGHT(host_input_ch, VALIDATE_SAMPLESHEET.out.samplesheet, crispr_spacers_value)
        host_context_ch = HOST_CONTEXT_LIGHT.out.table
        host_adaptation_ch = HOST_CONTEXT_LIGHT.out.adaptation
        host_rscu_ch = HOST_CONTEXT_LIGHT.out.rscu
        crispr_matches_ch = HOST_CONTEXT_LIGHT.out.crispr_matches
        crispr_summary_ch = HOST_CONTEXT_LIGHT.out.crispr_summary
    } else {
        NO_HOST_CONTEXT(VALIDATE_SAMPLESHEET.out.samplesheet)
        host_context_ch = NO_HOST_CONTEXT.out.table
        host_adaptation_ch = NO_HOST_CONTEXT.out.adaptation
        host_rscu_ch = NO_HOST_CONTEXT.out.rscu
        crispr_matches_ch = NO_HOST_CONTEXT.out.crispr_matches
        crispr_summary_ch = NO_HOST_CONTEXT.out.crispr_summary
    }

    fasta_stats_ch = FASTA_STATS.out.stats.map { sample_id, stats -> stats }.collect()
    orf_summary_ch = SIMPLE_ORF_PREDICT.out.summary.map { sample_id, summary -> summary }.collect()
    codon_summary_ch = CODON_USAGE.out.summary.map { sample_id, summary -> summary }.collect()

    BUILD_REPORT(
        VALIDATE_SAMPLESHEET.out.validation,
        fasta_stats_ch,
        orf_summary_ch,
        codon_summary_ch,
        COHORT_SIMILARITY.out.summary,
        COHORT_SIMILARITY.out.pairwise,
        COHORT_SIMILARITY.out.duplicates,
        intergenomic_summary_ch,
        intergenomic_pairs_ch,
        intergenomic_similarity_matrix_ch,
        intergenomic_distance_matrix_ch,
        intergenomic_note_ch,
        REFERENCE_CONTEXT.out.summary,
        REFERENCE_CONTEXT.out.pairs,
        REFERENCE_CONTEXT.out.nearest,
        REFERENCE_CONTEXT.out.note,
        marker_summary_ch,
        marker_presence_ch,
        marker_topology_ch,
        marker_provenance_ch,
        marker_note_ch,
        marker_trees_ch,
        pangenome_summary_ch,
        pangenome_presence_ch,
        pangenome_metadata_ch,
        host_context_ch,
        host_adaptation_ch,
        host_rscu_ch,
        crispr_matches_ch,
        crispr_summary_ch,
        OPTIONAL_TOOL_SUMMARY.out.summary,
        OPTIONAL_TOOL_SUMMARY.out.metrics,
        OPTIONAL_TOOL_SUMMARY.out.functional_categories
    )
}
