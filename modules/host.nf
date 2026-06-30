process HOST_CONTEXT_LIGHT {
    tag "host_context"
    publishDir "${params.outdir}/06_host_context", mode: 'copy'

    input:
    val host_samplesheet
    path phage_samplesheet
    val crispr_spacers

    output:
    path "host_context.tsv", emit: table
    path "host_context_summary.md", emit: summary
    path "host_codon_adaptation.tsv", emit: adaptation
    path "host_codon_rscu.tsv", emit: rscu
    path "crispr_spacer_matches.tsv", emit: crispr_matches
    path "crispr_spacer_summary.tsv", emit: crispr_summary

    script:
    """
    python3 ${projectDir}/bin/host_context_light.py \
        --phage-samplesheet "${phage_samplesheet}" \
        --host-samplesheet "${host_samplesheet}" \
        --table host_context.tsv \
        --summary host_context_summary.md \
        --host-codon-adaptation host_codon_adaptation.tsv \
        --host-codon-rscu host_codon_rscu.tsv \
        --crispr-matches crispr_spacer_matches.tsv \
        --crispr-summary crispr_spacer_summary.tsv \
        --run-crispr-spacer-match ${params.run_crispr_spacer_match} \
        --crispr-spacers "${crispr_spacers}" \
        --crispr-min-identity ${params.crispr_min_identity} \
        --crispr-min-coverage ${params.crispr_min_coverage} \
        --host-min-orf-aa ${params.host_min_orf_aa} \
        --host-use-prodigal ${params.host_use_prodigal} \
        --prodigal-bin "${params.prodigal_bin}"
    """
}

process NO_HOST_CONTEXT {
    tag "no_host_context"
    publishDir "${params.outdir}/06_host_context", mode: 'copy'

    input:
    path phage_samplesheet

    output:
    path "host_context.tsv", emit: table
    path "host_context_summary.md", emit: summary
    path "host_codon_adaptation.tsv", emit: adaptation
    path "host_codon_rscu.tsv", emit: rscu
    path "crispr_spacer_matches.tsv", emit: crispr_matches
    path "crispr_spacer_summary.tsv", emit: crispr_summary

    script:
    """
    printf 'sample_id	host_id	host_found	phage_gc_pct	host_gc_pct	delta_gc_pct	tetranucleotide_cosine	host_taxon	host_accession	phage_cds_source	host_cds_source	phage_codons	host_codons	codon_cosine	codon_distance	rscu_cosine	rscu_distance	cai_like	preferred_codon_match_pct	crispr_spacer_hits	best_crispr_identity_pct
' > host_context.tsv
    printf 'sample_id	host_id	host_found	phage_cds_source	host_cds_source	phage_codons	host_codons	phage_gc3_pct	host_gc3_pct	delta_gc3_pct	codon_cosine	codon_distance	rscu_cosine	rscu_distance	cai_like	preferred_codon_match_pct	crispr_spacer_hits	best_crispr_identity_pct	interpretation
' > host_codon_adaptation.tsv
    printf 'sample_id	host_id	codon	amino_acid	phage_count	host_count	phage_rscu	host_rscu	rscu_delta
' > host_codon_rscu.tsv
    printf 'sample_id	host_id	spacer_id	spacer_source	target_contig	match_start	match_end	strand	spacer_length	aligned_length	identity_pct	coverage_pct	mismatches
' > crispr_spacer_matches.tsv
    printf 'metric	value
status	disabled
phages_evaluated	0
host_links_evaluated	0
spacer_matches	0
' > crispr_spacer_summary.tsv
    cat > host_context_summary.md <<'EOF'
# Host Context Summary

No host samplesheet was provided. Host-context, host-adaptation, and CRISPR-spacer comparisons were skipped.
EOF
    """
}
