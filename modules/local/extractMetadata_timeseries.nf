process extractMetadata_timeseries {
    tag { "Extracting Metadata and IDS different weeks" }

    publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.tsv.gz", mode: 'copy'

    input:
      path(metadata)

    output:
      path("*.tsv.gz")
      path("*.txt"), emit: ids

    script:
      """
      extract_timeseries_metadata.py --startdate ${params.startdate} --enddate ${params.enddate} --table ${metadata} --window 7
      """
}