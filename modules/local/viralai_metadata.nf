process VIRALAIMETADATA {

  tag {"FETCH_Metadata"}

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.csv.gz", mode: 'copy'
  
  input:
        path(alias_key)
  
  output:
      path("*csv.gz"), emit: metadata

  script:
      """
      viralai_fetch_metadata.py --alias ${alias_key} --csv viralai.metadata.csv.gz
      """
}
