process extractVariants {
  tag {"Extracting VOCs, VOIs and VUMs"}
  input:
      tuple path(variants), path(metadata)
  output:
      path("*.txt"), emit: lineages

  script:

    """
    parse_variants.py \
    --variants ${variants} \
    --metadata ${metadata} \
    --outfile metada_lineages.txt
    """
}

process grabIndex {

    tag { "grabing_SARS-CoV-2_index" }

    input:
      path(index_folder)

    output:
      file("*.fasta.*")

    script:
      """
      ln -sf $index_folder/*.fasta.* ./
      """
}


process extractMetadata {
  tag { "Extracting Metadata and IDS for VOCs, VOIs, & VUMs" }

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.tsv", mode: 'copy'

  input:
      path(metadata)
      each x

  output:
      path("*.tsv")
      path("*.txt"), emit: ids


  script:

  if( params.gisaid )
    """
    extract_metadata.py \
    --table ${metadata} \
    --voc ${x} \
    --gisaid True \
    --startdate ${params.startdate} \
    --enddate ${params.enddate}
    """

  else
    """
    extract_metadata.py \
    --table ${metadata} \
    --voc ${x}
    """

}


process tsvTovcf {

    tag {"${variants_tsv.baseName}"}

    publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.vcf", mode: 'copy'

    input:
        path(variants_tsv)

    output:
        path("*.vcf"), emit: vcf

    script:
      """
      ivar_variants_to_vcf.py ${variants_tsv} ${variants_tsv}.vcf
      """
}


process processGVCF {

  tag {"${gvcf.baseName}"}

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*variants.vcf", mode: 'copy'

  input:
      path(gvcf)

  output:
      path("*.variants.vcf"), emit: vcf
      path("*.consensus.vcf")
      path("*.txt")

  script:
    if( params.single_genome ){
      """
      process_gvcf.py -d 1 \
      -l 0 \
      -u 1 \
      -m ${gvcf.baseName}.mask.txt \
      -v ${gvcf.baseName}.variants.vcf \
      -c ${gvcf.baseName}.consensus.vcf ${gvcf}
      """
    }
    else{
      """
      process_gvcf.py -d ${params.var_MinDepth} \
      -l ${params.lower_ambiguityFrequency} \
      -u ${params.upper_ambiguityFrequency} \
      -m ${gvcf.baseName}.mask.txt \
      -v ${gvcf.baseName}.variants.vcf \
      -c ${gvcf.baseName}.consensus.vcf ${gvcf}
      """
    }
}


process tagProblematicSites {
    tag {"${vcf.baseName}"}

    publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.vcf", mode: 'copy'

    input:
        tuple(path(vcf), path(prob_vcf))

    output:
        path("*.vcf"), emit: filtered_vcf

    script:
      """
      problematic_sites_tag.py \
      --vcffile ${vcf} \
      --filter_vcf ${prob_vcf} \
      --output_vcf ${vcf.baseName}.filtered.vcf
      """
}


process annotate_mat_peptide {

    tag {"${peptide_vcf.baseName}"}

    publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.vcf", mode: 'copy'

    input:
        tuple(path(peptide_vcf), path(genome_gff))

    output:
        path("*.vcf"), emit: annotated_vcf

    script:
      """
      mature_peptide_annotation.py \
      --vcf_file ${peptide_vcf}\
      --annotation_file ${genome_gff}\
      --output_vcf ${peptide_vcf.baseName}.annotated.vcf
      """
}


process vcfTogvf {

  tag {"${annotated_vcf.baseName}"}

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.gvf", mode: 'copy'

  input:
      tuple(path(annotated_vcf), path(func_annot), path(clade_def), path(gene_coord), path(mutation_split))
      //each x

  output:
      path("*.gvf"), emit: gvf

  script:

  if( params.user ){
    """
      vcf2gvf.py --vcffile ${annotated_vcf} \
      --functional_annotations ${func_annot}\
      --clades ${clade_def}\
      --gene_positions ${gene_coord}\
      --names_to_split ${mutation_split}\
      --outvcf ${annotated_vcf.baseName}.gvf
    """
  }
  else{
    if( !params.single_genome ){
      """
        vcf2gvf.py --vcffile ${annotated_vcf}\
        --functional_annotations ${func_annot}\
        --clades ${clade_def}\
        --gene_positions ${gene_coord}\
        --names_to_split ${mutation_split}\
        --strain ${annotated_vcf.baseName.replaceAll(".qc.sorted.variants.normalized.filtered.SNPEFF.annotated","")}\
        --outvcf ${annotated_vcf.baseName}.gvf
      """
    }
    else{
      """
        vcf2gvf.py --vcffile ${annotated_vcf}\
        --functional_annotations ${func_annot}\
        --clades ${clade_def}\
        --gene_positions ${gene_coord}\
        --names_to_split ${mutation_split}\
        --outvcf ${annotated_vcf.baseName}.gvf
        """
    }

  }


}

process vcfTotsv {

    tag {"vcfTotsv${annotated_vcf.baseName}"}

    publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.tsv", mode: 'copy'

    input:
        path(annotated_vcf)

    output:
        path("*.tsv")

    script:
      """
      vcf2tsv.py ${annotated_vcf} ${annotated_vcf.baseName}.tsv
      """
}

process mutation_profile {

  tag {"${gvf.baseName}"}

  publishDir "${params.outdir}/${params.prefix}/${task.process.replaceAll(":","_")}", pattern: "*.tsv", mode: 'copy'

  input:
      tuple(gvf)

  output:
      path("*.tsv")

  script:

  if( params.user ){
    """
      vcf2gvf.py --vcffile ${annotated_vcf} \
      --functional_annotations ${func_annot}\
      --clades ${clade_def}\
      --gene_positions ${gene_coord}\
      --names_to_split ${mutation_split}\
      --outvcf ${annotated_vcf.baseName}.gvf
    """
  }
  else{
    if( !params.single_genome ){
      """
        vcf2gvf.py --vcffile ${annotated_vcf}\
        --functional_annotations ${func_annot}\
        --clades ${clade_def}\
        --gene_positions ${gene_coord}\
        --names_to_split ${mutation_split}\
        --strain ${annotated_vcf.baseName.replaceAll(".qc.sorted.variants.normalized.filtered.SNPEFF.annotated","")}\
        --outvcf ${annotated_vcf.baseName}.gvf
      """
    }
    else{
      """
        vcf2gvf.py --vcffile ${annotated_vcf}\
        --functional_annotations ${func_annot}\
        --clades ${clade_def}\
        --gene_positions ${gene_coord}\
        --names_to_split ${mutation_split}\
        --outvcf ${annotated_vcf.baseName}.gvf
        """
    }

  }


}
