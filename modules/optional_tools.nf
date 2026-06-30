process TRNASCAN {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/trnascan", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.trnascan.tsv"), emit: table
    tuple val(sample_id), path("${sample_id}.trnascan.log"), emit: log

    script:
    """
    tRNAscan-SE -B -o "${sample_id}.trnascan.tsv" "${fasta}" > "${sample_id}.trnascan.log" 2>&1
    """
}

process BACPHLIP {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/bacphlip", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.bacphlip.log"), emit: log

    script:
    """
    bacphlip -i "${fasta}" > "${sample_id}.bacphlip.log" 2>&1
    """
}

process CHECKV {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/checkv", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.checkv"), emit: checkv_dir

    script:
    """
    if [ -z "${params.checkv_db}" ]; then
        echo "ERROR: --checkv_db is required when --run_checkv true" >&2
        exit 1
    fi
    checkv end_to_end "${fasta}" "${sample_id}.checkv" \
        -d "${params.checkv_db}" \
        -t ${task.cpus}
    """
}

process ABRICATE {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/abricate", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.abricate.tsv"), emit: table

    script:
    """
    abricate --db "${params.abricate_db}" "${fasta}" > "${sample_id}.abricate.tsv"
    """
}

process PHAROKKA {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/pharokka", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.pharokka"), emit: pharokka_dir

    script:
    """
    if [ -z "${params.pharokka_db}" ]; then
        echo "ERROR: --pharokka_db is required when --run_pharokka true, --run_phold true, or --run_clinker true" >&2
        exit 1
    fi
    pharokka.py \
        -i "${fasta}" \
        -o "${sample_id}.pharokka" \
        -d "${params.pharokka_db}" \
        -t ${task.cpus} \
        --force
    """
}
process GENOMAD {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/genomad", mode: 'copy'

    input:
    tuple val(sample_id), path(fasta), val(role), val(host_id), val(accession)

    output:
    tuple val(sample_id), path("${sample_id}.genomad"), emit: genomad_dir
    tuple val(sample_id), path("${sample_id}.genomad.log"), emit: log

    script:
    def splitArg = (params.genomad_splits as Integer) > 0 ? "--splits ${params.genomad_splits}" : ""
    """
    set -euo pipefail
    if [ -z "${params.genomad_db}" ]; then
        echo "ERROR: --genomad_db is required when --run_genomad true" >&2
        exit 1
    fi
    GENOMAD_BIN="${params.genomad_bin}"
    if ! command -v "\${GENOMAD_BIN}" >/dev/null 2>&1; then
        echo "ERROR: genomad not found. Install it with conda/mamba or pass --genomad_bin /path/to/genomad." >&2
        exit 127
    fi
    "\${GENOMAD_BIN}" end-to-end --cleanup ${splitArg} ${params.genomad_extra_args} \
        "${fasta}" "${sample_id}.genomad" "${params.genomad_db}" \
        > "${sample_id}.genomad.log" 2>&1
    """
}

process PHOLD {
    tag "${sample_id}"
    publishDir "${params.outdir}/05_optional/phold", mode: 'copy'

    input:
    tuple val(sample_id), path(pharokka_dir)

    output:
    tuple val(sample_id), path("${sample_id}.phold"), emit: phold_dir
    tuple val(sample_id), path("${sample_id}.phold.log"), emit: log

    script:
    """
    set -euo pipefail
    PHOLD_BIN="${params.phold_bin}"
    if ! command -v "\${PHOLD_BIN}" >/dev/null 2>&1; then
        echo "ERROR: phold not found. Install it with conda/mamba or pass --phold_bin /path/to/phold." >&2
        exit 127
    fi
    GBK_FILE=\$(find "${pharokka_dir}" -type f \\( -name '*.gbk' -o -name '*.gb' \\) | sort | head -n 1)
    if [ -z "\${GBK_FILE}" ]; then
        echo "ERROR: no GenBank file found in Pharokka output: ${pharokka_dir}" >&2
        exit 1
    fi
    "\${PHOLD_BIN}" run \
        -i "\${GBK_FILE}" \
        -o "${sample_id}.phold" \
        -t ${task.cpus} \
        ${params.phold_extra_args} \
        > "${sample_id}.phold.log" 2>&1
    """
}

process CLINKER_SYNTENY {
    tag "clinker_synteny"
    publishDir "${params.outdir}/05_optional/clinker_synteny", mode: 'copy'

    input:
    path pharokka_dirs

    output:
    path "gbk_files.txt", emit: gbk_files
    path "clinker_synteny.html", emit: html
    path "clinker_alignments.txt", emit: alignments
    path "clinker_synteny.log", emit: log
    path "clinker_synteny_note.md", emit: note

    script:
    """
    set -euo pipefail
    find . -type f \\( -name '*.gbk' -o -name '*.gb' \\) | sort > gbk_files.txt
    GBK_COUNT=\$(wc -l < gbk_files.txt | tr -d ' ')
    if [ "\${GBK_COUNT}" -lt "${params.clinker_min_genomes}" ]; then
        cat > clinker_synteny_note.md <<EOF
# clinker Synteny Skipped

Found \${GBK_COUNT} GenBank file(s), but --clinker_min_genomes is ${params.clinker_min_genomes}.
Run with at least two annotated phage genomes for a comparative synteny figure.
EOF
        cat > clinker_synteny.html <<EOF
<!doctype html><html><body><h1>clinker Synteny Skipped</h1><p>Found \${GBK_COUNT} GenBank file(s); at least ${params.clinker_min_genomes} required.</p></body></html>
EOF
        : > clinker_alignments.txt
        : > clinker_synteny.log
        exit 0
    fi
    CLINKER_BIN="${params.clinker_bin}"
    if ! command -v "\${CLINKER_BIN}" >/dev/null 2>&1; then
        echo "ERROR: clinker not found. Install it with conda/mamba or pass --clinker_bin /path/to/clinker." >&2
        exit 127
    fi
    xargs "\${CLINKER_BIN}" \
        -p clinker_synteny.html \
        -o clinker_alignments.txt \
        ${params.clinker_extra_args} \
        < gbk_files.txt \
        > clinker_synteny.log 2>&1
    cat > clinker_synteny_note.md <<EOF
# clinker Synteny

Generated a publication-oriented comparative gene-order visualisation from \${GBK_COUNT} Pharokka GenBank file(s).
Use the HTML output interactively and export SVG/other static formats if journal-specific figure editing is needed.
EOF
    """
}

process OPTIONAL_TOOL_SUMMARY {
    tag "optional_tool_summary"
    publishDir "${params.outdir}/05_optional/summary", mode: 'copy'

    input:
    path samplesheet
    path trnascan_artifacts
    path bacphlip_artifacts
    path checkv_artifacts
    path abricate_artifacts
    path pharokka_artifacts
    path genomad_artifacts
    path genomad_logs
    path phold_artifacts
    path phold_logs
    path clinker_artifacts

    output:
    path "optional_tool_summary.tsv", emit: summary
    path "optional_tool_summary.json", emit: summary_json

    script:
    def trnascanArgs = trnascan_artifacts.collect { "--trnascan-artifact ${it}" }.join(' ')
    def bacphlipArgs = bacphlip_artifacts.collect { "--bacphlip-artifact ${it}" }.join(' ')
    def checkvArgs = checkv_artifacts.collect { "--checkv-artifact ${it}" }.join(' ')
    def abricateArgs = abricate_artifacts.collect { "--abricate-artifact ${it}" }.join(' ')
    def pharokkaArgs = pharokka_artifacts.collect { "--pharokka-artifact ${it}" }.join(' ')
    def genomadArgs = genomad_artifacts.collect { "--genomad-artifact ${it}" }.join(' ')
    def genomadLogArgs = genomad_logs.collect { "--genomad-log ${it}" }.join(' ')
    def pholdArgs = phold_artifacts.collect { "--phold-artifact ${it}" }.join(' ')
    def pholdLogArgs = phold_logs.collect { "--phold-log ${it}" }.join(' ')
    def clinkerArgs = clinker_artifacts.collect { "--clinker-artifact ${it}" }.join(' ')
    """
    python3 ${projectDir}/bin/optional_tool_summary.py \
        --samplesheet "${samplesheet}" \
        ${trnascanArgs} \
        ${bacphlipArgs} \
        ${checkvArgs} \
        ${abricateArgs} \
        ${pharokkaArgs} \
        ${genomadArgs} \
        ${genomadLogArgs} \
        ${pholdArgs} \
        ${pholdLogArgs} \
        ${clinkerArgs} \
        --output optional_tool_summary.tsv \
        --summary-json optional_tool_summary.json
    """
}
