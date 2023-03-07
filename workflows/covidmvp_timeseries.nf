#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// import modules

include { BBMAP                         } from  '../modules/local/bbmap_reformat'
include { extractMetadata_timeseries    } from '../modules/local/extractMetadata_timeseries'
include { SEQKIT                        } from '../modules/local/seqkit'
include { SEQKITSTATS                   } from '../modules/local/seqkitstats'
include { MINIMAP2                      } from '../modules/local/minimap2'
include { FREEBAYES                     } from '../modules/local/freebayes'
include { SNPEFF               } from '../modules/local/snpeff'
include { tagProblematicSites  } from '../modules/local/custom'
include { annotate_mat_peptide } from '../modules/local/custom'
include { vcfTogvf             } from '../modules/local/custom'


workflow timeseries {
    take:
      ch_metadata
      ch_seq
      ch_ref
      ch_refgff
      ch_reffai
      ch_probvcf
      ch_geneannot
      ch_funcannot
      ch_genecoord
      ch_mutationsplit
      ch_variant


    main:
      
      extractMetadata_timeseries(ch_metadata)
      SEQKIT(extractMetadata_timeseries.out.ids.flatten().combine(ch_seq))
      ch_seq=SEQKIT.out.fasta
      
      BBMAP(ch_seq)
      ch_BBMap_combine=BBMAP.out.qcfasta.unique().collect()
      ch_BBMap=BBMAP.out.qcfasta
      SEQKITSTATS(ch_BBMap_combine)
      ch_stats=SEQKITSTATS.out.stats

      MINIMAP2(ch_BBMap.combine(ch_ref))
      ch_bam=MINIMAP2.out.bam
      ch_index=MINIMAP2.out.index
      
      FREEBAYES(ch_bam.combine(ch_ref).combine(ch_reffai),ch_index)
      ch_vcf=FREEBAYES.out.vcf

      tagProblematicSites(ch_vcf.combine(ch_probvcf))
      SNPEFF(tagProblematicSites.out.filtered_vcf)
      annotate_mat_peptide(SNPEFF.out.peptide_vcf.combine(ch_geneannot))
      ch_annotated_vcf=annotate_mat_peptide.out.annotated_vcf
      vcfTogvf(ch_annotated_vcf.combine(ch_funcannot).combine(ch_genecoord).combine(ch_mutationsplit).combine(ch_variant).combine(ch_stats))

}
