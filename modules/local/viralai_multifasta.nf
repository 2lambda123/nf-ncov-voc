process VIRALAIFASTA {

  tag {"FETCH_Multifasta"}

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.xz", mode: 'copy'
  
  output:
      path("*.xz"), emit: seq

  script:
      """
      viralai_fetch_fasta_url.py --seq fasta_drl.txt
      dnastack files download -i fasta_drl.txt
      """
}