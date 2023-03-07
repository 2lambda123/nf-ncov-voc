#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// import modules
include {VIRALAIMETADATA       } from '../modules/local/viralai_metadata'
include {VIRALAIFASTA          } from '../modules/local/viralai_multifasta'


workflow viralaidata {
    take:

      ch_pangolin_alias

    main:

      VIRALAIMETADATA( ch_pangolin_alias )
      ch_metadata=VIRALAIMETADATA.out.metadata
      VIRALAIFASTA()
      ch_seq=VIRALAIFASTA.out.seq

    emit:
      ch_metadata
      ch_seq

}
