process FREYJA_DEMIX {
    tag "$meta.id"
    label 'process_low'

    conda "bioconda::freyja=1.4.12"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/freyja:1.4.2--pyhdfd78af_0':
        'quay.io/biocontainers/freyja:1.4.2--pyhdfd78af_0' }"

    input:
    tuple val(meta),  path(variants)
    tuple val(meta2), path(depths)
    tuple val(meta3), path(barcodes)
    tuple val(meta4), path(lineages_meta)

    output:
    tuple val(meta), path("*.tsv"), emit: demix
    path "versions.yml"           , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    freyja \\
        demix \\
        $args \\
        --output ${prefix}.tsv \\
        --barcodes $barcodes \\
        --meta $lineages_meta \\
        $variants \\
        $depths
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        freyja: \$(echo \$(freyja --version 2>&1) | sed 's/^.*version //' )
    END_VERSIONS
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.tsv
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        freyja: \$(echo \$(freyja --version 2>&1) | sed 's/^.*version //' )
    END_VERSIONS
    """

}