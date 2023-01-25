#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: madeline

This script converts VCF files that have been annotated into GVF
files, including the functional annotation. Required user
input is a VCF file.


"""

import argparse
import pandas as pd
import numpy as np
import json
from functions import parse_INFO, find_sample_size, parse_variant_file, add_variant_information




def map_pos_to_gene_protein(pos, aa_names, GENE_PROTEIN_POSITIONS_DICT):
    """This function is inspired/lifted from Ivan's code.
    Map a series of nucleotide positions to SARS-CoV-2 genes.
    See https://www.ncbi.nlm.nih.gov/nuccore/MN908947.
    :param pos: Nucleotide position pandas series from VCF
    :param aa_names: aa_names pandas series
    :param GENE_PROTEIN_POSITIONS_DICT: Dictionary of gene positions from cov_lineages
    :type pos: int
    :return: series containing SARS-CoV-2 chromosome region names at each
    nucleotide position in ``pos``
    """
    # make a dataframe of the same length as
    # pos to put gene names in (+ other things)
    df = pos.astype(str).to_frame()

    # loop through genes dict to get gene names
    df["gene_names"] = df["POS"]
    for gene in GENE_PROTEIN_POSITIONS_DICT["genes"]:
        # get nucleotide coordinates for this gene
        start = GENE_PROTEIN_POSITIONS_DICT["genes"][gene]["coordinates"]["from"]
        end = GENE_PROTEIN_POSITIONS_DICT["genes"][gene]["coordinates"]["to"]
        # for all the mutations that are found in this region,
        # assign this gene name
        gene_mask = pos.astype(int).between(start, end, inclusive="both")
        if gene == "Stem-loop":  # no stem_loop entry in SARS-CoV-2.json
            df["gene_names"][gene_mask] = gene + ",3\' UTR"
        else:
            df["gene_names"][gene_mask] = gene
    # label all mutations that didn't belong to any gene as "intergenic"
    df["gene_names"][df["gene_names"].str.isnumeric()] = "intergenic"

    # loop through proteins dict to get protein names
    df["protein_names"] = df["POS"]
    for protein in GENE_PROTEIN_POSITIONS_DICT["proteins"]:
        start = GENE_PROTEIN_POSITIONS_DICT["proteins"][protein][
            "g.coordinates"]["from"]
        end = GENE_PROTEIN_POSITIONS_DICT["proteins"][protein]["g.coordinates"]["to"]
        protein_name = GENE_PROTEIN_POSITIONS_DICT["proteins"][protein]["name"]
        # get protein names for all mutations that are within range
        protein_mask = pos.astype(int).between(start, end, inclusive="both")
        df["protein_names"][protein_mask] = protein_name
    # label all mutations that didn't belong to any protein as "n/a"
    df["protein_names"][df["protein_names"].str.isnumeric()] = "n/a"

    return(df["gene_names"], df["protein_names"])


def clade_defining_threshold(threshold, df, sample_size):
    """Specifies the clade_defining attribute as True if AF >
    threshold, False if AF <= threshold, and n/a if the VCF is for a
    single genome """

    if sample_size == 1:
        df["#attributes"] = df["#attributes"].astype(str) + \
                            "clade_defining=n/a;"
    else:
        df.loc[df.AF > threshold, "#attributes"] = df.loc[
                                                       df.AF > threshold, "#attributes"].astype(
            str) + "clade_defining=True;"
        df.loc[df.AF <= threshold, "#attributes"] = df.loc[
                                                        df.AF <= threshold, "#attributes"].astype(
            str) + "clade_defining=False;"
    return df


gvf_columns = ['#seqid', '#source', '#type', '#start', '#end',
               '#score', '#strand', '#phase', '#attributes']
vcf_colnames = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL',
                'FILTER', 'INFO', 'FORMAT', 'unknown']


def vcftogvf(var_data, strain, GENE_PROTEIN_POSITIONS_DICT, names_to_split, sample_size):
    df = pd.read_csv(var_data, sep='\t', names=vcf_colnames)
    # remove pragmas
    df = df[~df['#CHROM'].str.contains("#")]
    # restart index from 0
    df = df.reset_index(drop=True)

    new_df = pd.DataFrame(index=range(0, len(df)), columns=gvf_columns)

    # fill in first 7 GVF columns, excluding 'type'
    new_df['#seqid'] = df['#CHROM']
    new_df['#source'] = '.'
    new_df['#start'] = df['POS']
    ### this needs fixing.. Checking if not required, we can delete this column. Or secify this doesnt clarify for ins/dels
    #new_df['#end'] = (df['POS'].astype(int) + df['ALT'].str.len() -
    #                  1).astype(str)
    new_df['#end'] = df['POS'] #'end' is not used in creating the COVID-MVP heatmap, but is a required GVF column
    new_df['#score'] = '.'
    new_df['#strand'] = '+'
    new_df['#phase'] = '.'

    info = parse_INFO(df)

    new_df["Names"] = info["Names"]
    new_df['nt_name'] = info["hgvs_nucleotide"]
    new_df['aa_name'] = info["hgvs_protein"]
    new_df['vcf_gene'] = info["vcf_gene"]
    new_df['mutation_type'] = info['mutation_type']

    # fill in 'type' column
    new_df['#type'] = info['type']

    # add 'INFO' attributes by name
    ### If the column attribute exists then parse and add. 
    info_cols_to_add = ['ps_filter', 'ps_exc', 'mat_pep_id',
                   'mat_pep_desc', 'mat_pep_acc']
    for column in list(set(info.columns) & set(info_cols_to_add)):
        # drop nans if they exist
        info[column] = info[column].fillna('')
        new_df['#attributes'] = new_df['#attributes'].astype(str) + \
            column + '=' + info[column].astype(str) + ';'

    # gene and protein name extraction
    gene_names, protein_names = map_pos_to_gene_protein(
        df['POS'].astype(int), new_df['aa_name'], GENE_PROTEIN_POSITIONS_DICT)
    new_df['#attributes'] = 'chrom_region=' + gene_names + ';'
    new_df['#attributes'] = new_df['#attributes'] + 'protein=' + \
        protein_names + ';'

    # add sample_size attribute
    new_df['#attributes'] = new_df['#attributes'] + "sample_size=" + \
                            str(sample_size) + ';'

    # add ro, ao, dp
    unknown = df['unknown'].str.split(pat=':').apply(pd.Series)

    
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'ro=' + unknown[3].astype(str) + ';'
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'ao=' + unknown[5].astype(str) + ';'
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'dp=' + info['dp'].astype(str) + ';'

    # add alternate frequency (AF) column for clade-defining cutoff (
    # af=ao/dp)
    # if there are no commas anywhere in the 'ao' column, calculate
    # AF straight out
    if unknown[5][unknown[5].str.contains(",")].empty:
        new_df['AF'] = unknown[5].astype(int) / info['dp'].astype(int)
    # if there is a comma, add the numbers together to calculate
    # alternate frequency
    else:
        new_df['added_ao'] = unknown[5].apply(lambda x: sum(map(int,
                                                                x.split(
                                                                    ','))))
        new_df['AF'] = new_df['added_ao'].astype(int) / info[
            'dp'].astype(int)

    # add Reference and Alternate alleles from VCF file
    for column in ['REF', 'ALT']:
        key = column.lower()
        if key == 'ref':
            key = 'Reference_seq'
        elif key == 'alt':
            key = 'Variant_seq'
        new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                                key + '=' + df[column].astype(str) + ';'
                                
    # get True/False/n/a designation for clade-defining status
    clade_threshold_gvf = clade_defining_threshold(args.clades_threshold,
                                             new_df, sample_size)                            
                                             
    ### MZA: This needs immediate attention with Paul and his group. Need to update the notion of mutations
    # split multi-aa names from the vcf into single-aa names (multi-row)
    new_df["multi_name"] = ''
    new_df["multiaa_comb_mutation"] = ''
    # load names_to_split spreadsheet
    multiaanames = pd.read_csv(names_to_split, sep='\t', header=0)
    # multi-aa names that are in the gvf (list form)
    names_to_separate = np.intersect1d(multiaanames, new_df[
                                                         'Names'].str[
                                                     2:])
    # now split the rows apart in-place
    for multname in names_to_separate:
        # relevant part of 'split_into' column
        splits = multiaanames[multiaanames['name'] == multname][
            'split_into'].copy()
        # list of names to split into
        splits_list_1 = splits.str.split(pat=',').tolist()[0]
        splits_list = [s.replace("'", '') for s in splits_list_1]
        # new_df index containing multi-aa name
        split_index = new_df.index.get_loc(new_df.index[new_df[
                                                            'Names'].str[
                                                        2:] == multname][
                                               0])
        # copy of rows to alter
        seprows = new_df.loc[[split_index]].copy()
        # delete original combined mutation rows
        new_df = new_df.drop(split_index)

        i = 0
        for sepname in splits_list:
            # single-aa name
            seprows['Names'] = "p." + sepname
            # original multi-aa name
            seprows["multi_name"] = multname
            # other single-aa names corresponding to this multi-aa
            # mutation
            seprows["multiaa_comb_mutation"] = splits.tolist()[
                0].replace("'" + sepname + "'", '').replace(",,",
                                                            ',').replace(
                "','", "', '").strip(',')
            new_df = pd.concat([new_df.loc[:split_index + i], seprows,
                                new_df.loc[
                                split_index + i:]]).reset_index(
                drop=True)
            i += 1

    # add attributes
    new_df['#attributes'] = 'Name=' + new_df["Names"] + ';' + new_df[
        '#attributes'].astype(str)
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'nt_name=' + new_df['nt_name'] + ';'
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'aa_name=' + new_df['aa_name'] + ';'
    # gene names
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'vcf_gene=' + new_df['vcf_gene'] + ';'
    # mutation type
    new_df['#attributes'] = new_df['#attributes'].astype(str) + \
                            'mutation_type=' + new_df[
                                'mutation_type'] + ';'

    # add strain name, multi-aa notes, sample_size
    new_df['#attributes'] = new_df[
                                '#attributes'] + 'viral_lineage=' + strain + ';'
    new_df['#attributes'] = new_df['#attributes'] + "multi_aa_name=" + \
                            new_df["multi_name"] + ';'

    new_df['#attributes'] = new_df[
                                '#attributes'] + "multiaa_comb_mutation=" + \
                            new_df["multiaa_comb_mutation"] + ';'
    new_df['#attributes'] = new_df[
                                '#attributes'] + "alternate_frequency=" + \
                            new_df['AF'].astype(str) + ';'

    # only keep the columns needed for a gvf file, plus
    # multiaa_comb_mutation to add to comb_mutation later
    new_df = new_df[gvf_columns + ['multiaa_comb_mutation', 'AF']]
    # new_df.to_csv('new_df.tsv', sep='\t', index=False, header=False)
    return new_df


# takes 3 arguments: the output df of vcftogvf.py, the functional
# annotation file, the strain name,
# and the names_to_split tsv.


def add_pokay_annotations(gvf, annotation_file, strain):
    attributes = gvf["#attributes"].str.split(pat=';').apply(pd.Series)

    # remember this includes nucleotide names where there are no
    # protein names
    gvf["mutation"] = attributes[0].str.split(pat='=').apply(pd.Series)[1]

    # merge annotated vcf and functional annotation files by
    # 'mutation' column in the gvf
    # load functional annotations spreadsheet
    df = pd.read_csv(annotation_file, sep='\t', header=0)

    for column in df.columns:
        df[column] = df[column].str.lstrip()
        # add functional annotations
    merged_df = pd.merge(df, gvf, on=['mutation'], how='right')

    # collect all mutation groups (including reference mutation) in a
    # column, sorted alphabetically
    # this is more roundabout than it needs to be; streamline with
    # grouby() later
    merged_df["mutation_group"] = merged_df["comb_mutation"].astype(
        str) + ", '" + merged_df["mutation"].astype(str) + "', " + \
                                  merged_df[
                                      'multiaa_comb_mutation'].astype(
                                      str)
    merged_df["mutation_group"] = merged_df[
        "mutation_group"].str.replace("nan, ", "")
    merged_df["mutation_group"] = merged_df[
        "mutation_group"].str.rstrip(' ').str.rstrip(',')

    # separate the mutation_group column into its own df with one
    # mutation per column
    mutation_groups = merged_df["mutation_group"].str.split(
        pat=',').apply(pd.Series)
    mutation_groups = mutation_groups.apply(
        lambda s: s.str.replace("'", ""))
    mutation_groups = mutation_groups.apply(
        lambda s: s.str.replace(" ", ""))
    # now each mutation has a column instead
    mutation_groups = mutation_groups.transpose()
    # sort each column alphabetically
    sorted_df = mutation_groups

    for column in mutation_groups.columns:
        sorted_df[column] = mutation_groups.sort_values(by=column,
                                                        ignore_index=True)[
            column]
    sorted_df = sorted_df.transpose()

    # since they're sorted, put everything back into a single cell,
    # don't care about dropna
    df3 = sorted_df.apply(lambda x: ','.join(x.astype(str)), axis=1)
    unique_groups = df3.drop_duplicates()
    unique_groups_multicol = sorted_df.drop_duplicates()
    # for sanity checking
    merged_df["mutation_group_labeller"] = df3

    # make a unique id for mutation groups that have all members
    # represented in the vcf
    # for groups with missing members, delete those functional
    # annotations
    merged_df["id"] = 'NaN'
    id_num = 0
    for row in range(unique_groups.shape[0]):
        group_mutation_set = set(unique_groups_multicol.iloc[row])
        # remove nan and 'nan' from set
        group_mutation_set = {x for x in group_mutation_set if (x == x
                                                                and x != 'nan')}
        gvf_all_mutations = set(gvf['mutation'].unique())
        indices = merged_df[merged_df.mutation_group_labeller ==
                            unique_groups.iloc[row]].index.tolist()
        # if all mutations in the group are in the vcf file, include
        # those rows and give them an id
        if group_mutation_set.issubset(gvf_all_mutations):
            merged_df.loc[merged_df.mutation_group_labeller ==
                          unique_groups.iloc[row], "id"] = "ID_" + \
                                                           str(id_num)
            id_num += 1
        else:
            # if not, drop group rows, leaving the remaining indices
            # unchanged
            merged_df = merged_df.drop(indices)

            # change semicolons in function descriptions to colons
    merged_df['function_description'] = merged_df[
        'function_description'].str.replace(';', ':')
    # change heteozygosity column to True/False
    merged_df['heterozygosity'] = merged_df['heterozygosity'] == \
                                  'heterozygous'
    # remove trailing spaces from citation
    merged_df['citation'] = merged_df['citation'].str.strip()
    # add key-value pairs to attributes column
    for column in ['function_category', 'source', 'citation',
                   'comb_mutation', 'function_description',
                   'heterozygosity']:
        key = column.lower()
        # replace NaNs with empty string
        merged_df[column] = merged_df[column].fillna('')
        merged_df["#attributes"] = merged_df["#attributes"].astype(
            str) + key + '=' + merged_df[column].astype(str) + ';'
    
    # add ID to attributes
    merged_df["#attributes"] = 'ID=' + merged_df['id'].astype(
        str) + ';' + merged_df["#attributes"].astype(str)

    if args.names:
        # get list of names in tsv but not in functional annotations,
        # and vice versa, saved as a .tsv
        tsv_names = gvf["mutation"].unique()
        functional_annotation_names = df["mutation"].unique()
        print(str(np.setdiff1d(tsv_names,
                               functional_annotation_names).shape[0])
              + "/" + str(tsv_names.shape[0]) + " mutation names were "
                                                "not found in "
                                                "functional_annotations")
        leftover_names = pd.DataFrame({'in_tsv_only': np.setdiff1d(
            tsv_names, functional_annotation_names)})
        leftover_names["strain"] = strain
        
        # Check this block and if not needed, we can take this out. 
        '''
        clade_names = clades["mutation"].unique()
        leftover_clade_names = pd.DataFrame({'unmatched_clade_names':np.setdiff1d(clade_names, tsv_names)})
        leftover_clade_names["strain"] = strain
        '''
        return merged_df[gvf_columns], leftover_names, gvf[
            "mutation"].tolist()  # , leftover_clade_names

    else:
        return merged_df[gvf_columns]


def parse_args():
    parser = argparse.ArgumentParser(
        description='Converts a annotated VCF file to a GVF '
                    'file with functional annotation')
    parser.add_argument('--vcffile', type=str, default=None,
                        help='Path to a snpEFF-annotated VCF file')
    parser.add_argument('--functional_annotations', type=str,
                        default=None, help='TSV file of functional '
                                           'annotations')
    parser.add_argument('--size_stats', type=str, default='n/a',
                        help='Statistics file for for size extraction')
    parser.add_argument('--clades', type=str, default=None,
                        help='TSV file of WHO strain names and '
                             'VOC/VOI status')
    parser.add_argument('--clades_threshold', type=float,
                        default=0.75,
                        help='Alternate frequency cutoff for '
                             'clade-defining mutations')
    parser.add_argument('--gene_positions', type=str,
                        default=None,
                        help='gene positions in JSON format')
    # --names_to_split needs updating: 13 January, 2023
    parser.add_argument('--names_to_split', type=str,
                        default=None,
                        help='.tsv of multi-aa mutation names to '
                             'split up into individual aa names')
    parser.add_argument('--strain', type=str,
                        default='n/a',
                        help='Lineage; user mode is if strain="n/a"')
    parser.add_argument('--outgvf', type=str,
                        help='Filename for the output GVF file')
    parser.add_argument("--names", help="Save mutation names without "
                                        "functional annotations to "
                                        "TSV files for "
                                        "troubleshooting purposes",
                        action="store_true")
    return parser.parse_args()


if __name__ == '__main__':

    args = parse_args()
    
    # Reading the gene & proetin coordinates of SARS-CoV-2 genome
    with open(args.gene_positions) as fp:
        GENE_PROTEIN_POSITIONS_DICT = json.load(fp)
    # Assigning the functional annotation file to a variable
    annotation_file = args.functional_annotations
    # Assigning the variant file to a variable
    clade_file = args.clades
    # Assigning the vcf file to a variable
    vcf_file = args.vcffile

    # print("Processing: " + vcf_file)

    # make empty list in which to store mutation names from all
    # strains in the folder together
    all_strains_mutations = []
    # empty dataframe to hold unmatched names
    leftover_df = pd.DataFrame()

    pragmas = pd.DataFrame([['##gff-version 3'], ['##gvf-version '
                                                  '1.10'], [
                                '##species NCBI_Taxonomy_URI=http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=2697049']])  # pragmas are in column 0

    

    sample_size = find_sample_size(args.size_stats, args.strain)
    

    # create gvf from annotated vcf (ignoring pragmas for now)
    gvf = vcftogvf(vcf_file, args.strain, GENE_PROTEIN_POSITIONS_DICT,
                   args.names_to_split, sample_size)
    # add functional annotations
    if args.names:
        annotated_gvf, leftover_names, mutations = add_pokay_annotations(gvf,
                                                                 annotation_file,
                                                                 clade_file,
                                                                 args.strain)
    else:
        pokay_annotated_gvf = add_pokay_annotations(gvf, annotation_file,
                                      args.strain)
        variant_annotated_gvf = add_variant_information(clade_file, pokay_annotated_gvf, sample_size, args.strain)

    # add pragmas to df, then save to .gvf
    # columns are now 0, 1, ...
    final_gvf = pd.DataFrame(np.vstack([variant_annotated_gvf.columns,
                                            variant_annotated_gvf]))
    final_gvf = pragmas.append(final_gvf)
    filepath = args.outgvf  # outdir + strain + ".annotated.gvf"
    print("Saved as: ", filepath)
    print("")
    final_gvf.to_csv(filepath, sep='\t', index=False, header=False)

    # get name troubleshooting reports
    if args.names:
        all_strains_mutations.append(mutations)
        leftover_df = leftover_df.append(leftover_names)
        # unmatched_clade_names = unmatched_clade_names.append(
        # leftover_clade_names)
        # save unmatched names (in tsv but not in
        # functional_annotations) across all strains to a .tsv file
        leftover_names_filepath = "leftover_names.tsv"
        leftover_df.to_csv(leftover_names_filepath, sep='\t',
                           index=False)
        print("")
        print("Mutation names not found in functional annotations "
              "file saved to " + leftover_names_filepath)
        '''
        #save unmatched clade-defining mutation names to a .tsv file
        leftover_clade_names_filepath = "leftover_clade_defining_names.tsv"
        unmatched_clade_names.to_csv(leftover_clade_names_filepath,sep='\t', index=False)
        print("Clade-defining mutation names not found in the annotated VCF saved to " + leftover_clade_names_filepath)
        '''
        # print number of unique mutations across all strains
        flattened = [val for sublist in all_strains_mutations for val in
                     sublist]
        arr = np.array(flattened)
        print("# unique mutations in VCF file: ",
              np.unique(arr).shape[0])

    print("")
    print("Processing complete.")
