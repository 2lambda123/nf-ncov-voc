process POSTPROCESSING {

  tag {"linking output files to rsync"}


  script:
      """
      ln -s /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/${params.outdir}${params.prefix}/annotation_vcfTogvf/* /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/latest_gvf/
      ln -s /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/${params.outdir}${params.prefix}/surveillance_surveillanceRawTsv/* /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/latest_tsv/
      ln -s /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/${params.outdir}${params.prefix}/surveillance_surveillancePDF/* /scratch/mzanwar/COVID-MVP/nf_ncov_voc_viralai/nf-ncov-voc/latest_pdf/
      """
}