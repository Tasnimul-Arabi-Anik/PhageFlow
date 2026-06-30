process COHORT_SIMILARITY {
    tag "cohort_similarity"
    publishDir "${params.outdir}/04_comparative/cohort_similarity", mode: 'copy'

    input:
    path samplesheet

    output:
    path "cohort_pairwise_similarity.tsv", emit: pairwise
    path "cohort_duplicate_groups.tsv", emit: duplicates
    path "cohort_similarity_summary.tsv", emit: summary

    script:
    """
    python3 ${projectDir}/bin/cohort_similarity.py \
        --samplesheet "${samplesheet}" \
        --kmer-size ${params.kmer_size} \
        --duplicate-jaccard ${params.duplicate_jaccard} \
        --pairwise cohort_pairwise_similarity.tsv \
        --duplicates cohort_duplicate_groups.tsv \
        --summary cohort_similarity_summary.tsv
    """
}


process INTERGENOMIC_SIMILARITY {
    tag "intergenomic_similarity"
    publishDir "${params.outdir}/04_comparative/intergenomic_similarity", mode: 'copy'

    input:
    path samplesheet

    output:
    path "intergenomic_similarity_pairs.tsv", emit: pairs
    path "intergenomic_similarity_matrix.tsv", emit: similarity_matrix
    path "intergenomic_distance_matrix.tsv", emit: distance_matrix
    path "intergenomic_similarity_summary.tsv", emit: summary
    path "intergenomic_similarity_note.md", emit: note

    script:
    """
    BLASTN_BIN="${params.blastn_bin}"
    MAKEBLASTDB_BIN="${params.makeblastdb_bin}"
    if ! command -v "\${BLASTN_BIN}" >/dev/null 2>&1; then
        for candidate in \
            /home/anik/phage_project/.conda-envs/phage-compare/bin/blastn \
            /home/anik/miniforge3/envs/pangenome/bin/blastn \
            /home/anik/miniconda3/envs/pangenome/bin/blastn; do
            if [ -x "\${candidate}" ]; then
                BLASTN_BIN="\${candidate}"
                break
            fi
        done
    fi
    if ! command -v "\${MAKEBLASTDB_BIN}" >/dev/null 2>&1; then
        for candidate in \
            /home/anik/phage_project/.conda-envs/phage-compare/bin/makeblastdb \
            /home/anik/miniforge3/envs/pangenome/bin/makeblastdb \
            /home/anik/miniconda3/envs/pangenome/bin/makeblastdb; do
            if [ -x "\${candidate}" ]; then
                MAKEBLASTDB_BIN="\${candidate}"
                break
            fi
        done
    fi
    if ! command -v "\${BLASTN_BIN}" >/dev/null 2>&1 || ! command -v "\${MAKEBLASTDB_BIN}" >/dev/null 2>&1; then
        echo "ERROR: blastn/makeblastdb not found. Use -profile conda/docker or pass --blastn_bin and --makeblastdb_bin." >&2
        exit 127
    fi

    python3 ${projectDir}/bin/intergenomic_similarity.py \
        --samplesheet "${samplesheet}" \
        --blastn-bin "\${BLASTN_BIN}" \
        --makeblastdb-bin "\${MAKEBLASTDB_BIN}" \
        --threads ${task.cpus} \
        --min-identity ${params.ani_min_identity} \
        --min-aln-len ${params.ani_min_aln_len} \
        --max-evalue ${params.ani_max_evalue} \
        --max-genomes ${params.ani_max_genomes} \
        --pairs intergenomic_similarity_pairs.tsv \
        --similarity-matrix intergenomic_similarity_matrix.tsv \
        --distance-matrix intergenomic_distance_matrix.tsv \
        --summary intergenomic_similarity_summary.tsv \
        --note intergenomic_similarity_note.md
    """
}

process REFERENCE_CONTEXT {
    tag "reference_context"
    publishDir "${params.outdir}/04_comparative/reference_context", mode: 'copy'

    input:
    path samplesheet
    path cohort_pairwise
    path intergenomic_pairs
    path intergenomic_summary

    output:
    path "reference_context_summary.tsv", emit: summary
    path "reference_context_pairs.tsv", emit: pairs
    path "reference_context_nearest.tsv", emit: nearest
    path "reference_context_note.md", emit: note

    script:
    """
    python3 ${projectDir}/bin/reference_context.py \
        --samplesheet "${samplesheet}" \
        --cohort-pairwise "${cohort_pairwise}" \
        --intergenomic-pairs "${intergenomic_pairs}" \
        --intergenomic-summary "${intergenomic_summary}" \
        --summary reference_context_summary.tsv \
        --pairs reference_context_pairs.tsv \
        --nearest reference_context_nearest.tsv \
        --note reference_context_note.md
    """
}

process NO_INTERGENOMIC_SIMILARITY {
    tag "no_intergenomic_similarity"
    publishDir "${params.outdir}/04_comparative/intergenomic_similarity", mode: 'copy'

    input:
    path samplesheet

    output:
    path "intergenomic_similarity_pairs.tsv", emit: pairs
    path "intergenomic_similarity_matrix.tsv", emit: similarity_matrix
    path "intergenomic_distance_matrix.tsv", emit: distance_matrix
    path "intergenomic_similarity_summary.tsv", emit: summary
    path "intergenomic_similarity_note.md", emit: note

    script:
    """
    python3 ${projectDir}/bin/intergenomic_similarity.py \
        --samplesheet "${samplesheet}" \
        --skip-reason disabled_by_user \
        --pairs intergenomic_similarity_pairs.tsv \
        --similarity-matrix intergenomic_similarity_matrix.tsv \
        --distance-matrix intergenomic_distance_matrix.tsv \
        --summary intergenomic_similarity_summary.tsv \
        --note intergenomic_similarity_note.md
    """
}


process MARKER_PHYLOGENY {
    tag "marker_phylogeny"
    publishDir "${params.outdir}/04_comparative/marker_phylogeny", mode: 'copy'

    input:
    path samplesheet
    path faa_files
    path intergenomic_distance_matrix
    val marker_faa

    output:
    path "marker_tree_summary.tsv", emit: summary
    path "marker_presence.tsv", emit: presence
    path "marker_topology_consistency.tsv", emit: topology
    path "marker_provenance.tsv", emit: provenance
    path "marker_phylogeny_note.md", emit: note
    path "markers", emit: markers
    path "alignments", emit: alignments
    path "trees", emit: trees

    script:
    def faaArgs = faa_files.collect { "${it}" }.join(' ')
    """
    MARKER_FAA="${marker_faa}"
    MARKER_FAA_ARGS=""
    if [ -n "\${MARKER_FAA}" ] && [ "\${MARKER_FAA}" != "null" ] && [ "\${MARKER_FAA}" != "None" ]; then
        MARKER_FAA_ARGS="--marker-faa \${MARKER_FAA}"
    fi

    python3 ${projectDir}/bin/marker_phylogeny.py \
        --samplesheet "${samplesheet}" \
        --faa-files ${faaArgs} \
        \${MARKER_FAA_ARGS} \
        --marker-source "${params.marker_source}" \
        --marker-kinds "${params.marker_kinds}" \
        --marker-min-genomes ${params.marker_min_genomes} \
        --tree-engine "${params.marker_tree_engine}" \
        --bootstrap ${params.marker_bootstrap} \
        --mafft-bin "${params.mafft_bin}" \
        --trimal-bin "${params.trimal_bin}" \
        --iqtree-bin "${params.iqtree_bin}" \
        --intergenomic-distance-matrix "${intergenomic_distance_matrix}" \
        --markers-dir markers \
        --alignments-dir alignments \
        --trees-dir trees \
        --summary marker_tree_summary.tsv \
        --presence marker_presence.tsv \
        --topology marker_topology_consistency.tsv \
        --provenance marker_provenance.tsv \
        --note marker_phylogeny_note.md
    """
}

process NO_MARKER_PHYLOGENY {
    tag "no_marker_phylogeny"
    publishDir "${params.outdir}/04_comparative/marker_phylogeny", mode: 'copy'

    input:
    path samplesheet

    output:
    path "marker_tree_summary.tsv", emit: summary
    path "marker_presence.tsv", emit: presence
    path "marker_topology_consistency.tsv", emit: topology
    path "marker_provenance.tsv", emit: provenance
    path "marker_phylogeny_note.md", emit: note
    path "markers", emit: markers
    path "alignments", emit: alignments
    path "trees", emit: trees

    script:
    """
    python3 ${projectDir}/bin/marker_phylogeny.py \
        --samplesheet "${samplesheet}" \
        --skip-reason disabled_by_user \
        --markers-dir markers \
        --alignments-dir alignments \
        --trees-dir trees \
        --summary marker_tree_summary.tsv \
        --presence marker_presence.tsv \
        --topology marker_topology_consistency.tsv \
        --provenance marker_provenance.tsv \
        --note marker_phylogeny_note.md
    """
}

process MMSEQS_PANGENOME {
    tag "mmseqs_pangenome"
    publishDir "${params.outdir}/04_comparative/mmseqs_pangenome", mode: 'copy'

    input:
    path faa_files

    output:
    path "mmseqs_clusters.tsv", emit: clusters
    path "orthogroups.tsv", emit: orthogroups
    path "presence_absence.tsv", emit: presence_absence
    path "genome_metadata.tsv", emit: genome_metadata
    path "pangenome_summary.tsv", emit: summary

    script:
    def faaArgs = faa_files.collect { "${it}" }.join(' ')
    """
    cat ${faaArgs} > combined_proteins.faa

    MMSEQS_BIN="${params.mmseqs_bin}"
    if ! command -v "\${MMSEQS_BIN}" >/dev/null 2>&1; then
        for candidate in \
            /home/anik/miniforge3/envs/eggnog_mapper/bin/mmseqs \
            /home/anik/miniforge3/envs/pangenome/bin/mmseqs \
            /home/anik/miniconda3/envs/pangenome/bin/mmseqs; do
            if [ -x "\${candidate}" ]; then
                MMSEQS_BIN="\${candidate}"
                break
            fi
        done
    fi
    if ! command -v "\${MMSEQS_BIN}" >/dev/null 2>&1; then
        echo "ERROR: mmseqs not found. Use -profile conda/docker or pass --mmseqs_bin /path/to/mmseqs." >&2
        exit 127
    fi

    "\${MMSEQS_BIN}" easy-cluster combined_proteins.faa mmseqs_cluster tmp_mmseqs \
        --min-seq-id ${params.pan_min_seq_id} \
        -c ${params.pan_min_coverage} \
        --cov-mode ${params.pan_cluster_mode} \
        --threads ${task.cpus}
    cp mmseqs_cluster_cluster.tsv mmseqs_clusters.tsv
    python3 ${projectDir}/bin/mmseqs_pangenome_summary.py \
        --clusters mmseqs_clusters.tsv \
        --faa-files ${faaArgs} \
        --orthogroups orthogroups.tsv \
        --presence-absence presence_absence.tsv \
        --genome-metadata genome_metadata.tsv \
        --summary pangenome_summary.tsv
    """
}

process RBH_PANGENOME {
    tag "rbh_blastp_pangenome"
    publishDir "${params.outdir}/04_comparative/rbh_blastp_pangenome", mode: 'copy'

    input:
    path faa_files

    output:
    path "all_vs_all_blastp.tsv", emit: hits
    path "orthogroups.tsv", emit: orthogroups
    path "presence_absence.tsv", emit: presence_absence
    path "genome_metadata.tsv", emit: genome_metadata
    path "pangenome_summary.tsv", emit: summary

    script:
    def faaArgs = faa_files.collect { "${it}" }.join(' ')
    """
    BLASTP_BIN="${params.blastp_bin}"
    MAKEBLASTDB_BIN="${params.makeblastdb_bin}"
    if ! command -v "\${BLASTP_BIN}" >/dev/null 2>&1; then
        for candidate in \
            /home/anik/phage_project/.conda-envs/orf-compare/bin/blastp \
            /home/anik/phage_project/.conda-envs/phage-compare/bin/blastp \
            /home/anik/miniforge3/envs/pangenome/bin/blastp; do
            if [ -x "\${candidate}" ]; then
                BLASTP_BIN="\${candidate}"
                break
            fi
        done
    fi
    if ! command -v "\${MAKEBLASTDB_BIN}" >/dev/null 2>&1; then
        for candidate in \
            /home/anik/phage_project/.conda-envs/orf-compare/bin/makeblastdb \
            /home/anik/phage_project/.conda-envs/phage-compare/bin/makeblastdb \
            /home/anik/miniforge3/envs/pangenome/bin/makeblastdb; do
            if [ -x "\${candidate}" ]; then
                MAKEBLASTDB_BIN="\${candidate}"
                break
            fi
        done
    fi
    if ! command -v "\${BLASTP_BIN}" >/dev/null 2>&1 || ! command -v "\${MAKEBLASTDB_BIN}" >/dev/null 2>&1; then
        echo "ERROR: blastp/makeblastdb not found. Use -profile conda/docker or pass --blastp_bin and --makeblastdb_bin." >&2
        exit 127
    fi

    python3 ${projectDir}/bin/rbh_pangenome.py \
        --faa-files ${faaArgs} \
        --blastp-bin "\${BLASTP_BIN}" \
        --makeblastdb-bin "\${MAKEBLASTDB_BIN}" \
        --threads ${task.cpus} \
        --min-identity ${params.rbh_min_identity} \
        --min-query-cov ${params.rbh_min_query_cov} \
        --min-subject-cov ${params.rbh_min_subject_cov} \
        --max-evalue ${params.rbh_max_evalue} \
        --hits all_vs_all_blastp.tsv \
        --orthogroups orthogroups.tsv \
        --presence-absence presence_absence.tsv \
        --genome-metadata genome_metadata.tsv \
        --summary pangenome_summary.tsv
    """
}

process NO_PANGENOME {
    tag "no_pangenome"
    publishDir "${params.outdir}/04_comparative/no_pangenome", mode: 'copy'

    input:
    path samplesheet

    output:
    path "orthogroups.tsv", emit: orthogroups
    path "presence_absence.tsv", emit: presence_absence
    path "genome_metadata.tsv", emit: genome_metadata
    path "pangenome_summary.tsv", emit: summary

    script:
    """
    printf 'orthogroup\tcategory\tn_genomes\tn_proteins\tmembers\n' > orthogroups.tsv
    printf 'orthogroup\tcategory\tn_genomes\n' > presence_absence.tsv
    awk 'BEGIN{FS="\t"; OFS="\t"} NR==1{print "genome_id","genome_name","protein_count"; next} {print \$1,\$1,0}' "${samplesheet}" > genome_metadata.tsv
    cat > pangenome_summary.tsv <<EOF
metric	value
method	${params.pangenome_method}
genomes	0
proteins	0
orthogroups	0
core_orthogroups	0
accessory_orthogroups	0
singleton_orthogroups	0
status	skipped
EOF
    """
}

process RUN_LEGACY_SNAKEMAKE_PANGENOME {
    tag "legacy_snakemake_rbh_deprecated"
    publishDir "${params.outdir}/04_comparative/legacy_snakemake_rbh_deprecated", mode: 'copy'

    input:
    path samplesheet

    output:
    path "legacy_snakemake_pangenome_note.md", emit: note

    script:
    """
    if [ -z "${params.legacy_snakemake_config}" ]; then
        cat > legacy_snakemake_pangenome_note.md <<'EOF'
# Deprecated Legacy Snakemake Pangenome Backend

This backend is retained only for one-release parity checks with the previous workflow. It is not the normal PhageFlow path and was not executed because `--legacy_snakemake_config` was not provided.

Use native `--pangenome_method mmseqs` for scalable cohort pangenomics or `--pangenome_method rbh_blastp` for conservative reciprocal-best-hit comparison.
EOF
        exit 0
    fi

    snakemake \
        -s "${params.legacy_snakemake_dir}/workflow/Snakefile" \
        --configfile "${params.legacy_snakemake_config}" \
        --cores ${task.cpus}

    cat > legacy_snakemake_pangenome_note.md <<EOF
# Deprecated Legacy Snakemake Pangenome Backend

The legacy Snakemake pangenome workflow completed for parity checking only.

- Snakefile: `${params.legacy_snakemake_dir}/workflow/Snakefile`
- Config: `${params.legacy_snakemake_config}`
- Samplesheet visible to PhageFlow: `${samplesheet}`
EOF
    """
}
