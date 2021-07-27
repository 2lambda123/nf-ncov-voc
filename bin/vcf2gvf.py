#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 23 11:06:22 2021

@author: madeline
"""

'''
This script converts VCF files that have been annotated by snpEFF into GVF files, including the functional annotation.
'''

import argparse
import pandas as pd
import re
import glob
import os
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description='Converts snpEFF-annotated VCF files to GVF files with functional annotation')
    parser.add_argument('--vcfdir', type=str, default=None,
                        help='Path to folder containing snpEFF-annotated VCFs files')
    #filepath can be absolute (~/Desktop/test/22_07_2021/) or relative (./22_07_2021/)
    parser.add_argument('--pokay', type=str, default='functional_annotation_V.0.2.tsv',
                        help='Anoosha\'s parsed pokay .tsv file')
    parser.add_argument('--clades', type=str, default='clade_defining_mutations.tsv',
                        help='.tsv of clade-defining mutations')
    parser.add_argument('--outdir', type=str, default='./gvf_files/',
                        help='Output directory for finished GVF files: folder will be created if it doesn\'t already exist')
    return parser.parse_args()


gvf_columns = ['#seqid','#source','#type','#start','#end','#score','#strand','#phase','#attributes']


def vcftogvf(var_data, strain):
    
    df = pd.read_csv(var_data, sep='\t', header=65)    
    new_df = pd.DataFrame(index=range(0,len(df)),columns=gvf_columns)

    #parse EFF column
    eff_info = df['INFO'].str.findall('\((.*?)\)') #series: extract everything between parentheses as elements of a list
    eff_info = eff_info.apply(pd.Series)[0] #take first element of list
    eff_info = eff_info.str.split(pat='|').apply(pd.Series) #split at pipe, form dataframe

    #hgvs names
    hgvs = eff_info[3].str.rsplit(pat='c.').apply(pd.Series)
    hgvs_protein = hgvs[0].str[:-1]
    hgvs_protein.replace(r'^\s+$', np.nan, regex=True)
    hgvs_nucleotide = 'c.' + hgvs[1]
    new_df['#attributes'] = new_df['#attributes'].astype(str) + 'Name=' + hgvs_protein + ';'
    new_df['#attributes'] = new_df['#attributes'].astype(str) + 'nt_name=' + hgvs_nucleotide + ';'
    new_df['#attributes'] = new_df['#attributes'].astype(str) + 'gene=' + eff_info[5] + ';' #gene names
    new_df['#attributes'] = new_df['#attributes'].astype(str) + 'mutation_type=' + eff_info[1] + ';' #mutation type 
    
    #columns copied straight from Zohaib's file
    for column in ['REF','ALT']:
        key = column.lower()
        if key=='ref':
            key = 'Reference_seq'
        elif key=='alt':
            key = 'Variant_seq'
        new_df['#attributes'] = new_df['#attributes'].astype(str) + key + '=' + df[column].astype(str) + ';'

    #add ao, dp, ro
    info = df['INFO'].str.split(pat=';').apply(pd.Series) #split at ;, form dataframe
    new_df['#attributes'] = new_df['#attributes'] + info[5].str.lower() + ';' #ao
    new_df['#attributes'] = new_df['#attributes'] + info[7].str.lower() + ';' #dp
    new_df['#attributes'] = new_df['#attributes'] + info[28].str.lower() + ';' #ro
    
    #add strain name
    new_df['#attributes'] = new_df['#attributes'] + 'viral_lineage=' + strain + ';'

    #add WHO strain name
    alt_strain_names = {'B.1.1.7': 'Alpha', 'B.1.351': 'Beta', 'P.1': 'Gamma', 'B.1.617.2': 'Delta', 'B.1.427': 'Epsilon', 'B.1.429': 'Epsilon', 'P.2': 'Zeta', 'B.1.525': 'Eta', 'P.3': 'Theta', 'B.1.526': 'Iota', 'B.1.617.1': 'Kappa'}
    #mapped_alt_strains = df['strain'].map(alt_strain_names)
    #new_df['#attributes'] = new_df['#attributes'] + 'who_label=' + mapped_alt_strains + ';'
    new_df['#attributes'] = new_df['#attributes'] + 'who_label=' + alt_strain_names.get(strain) + ';'

    #add VOC/VOI designation
    if mapped_alt_strains.all() in {'Alpha', 'Beta', 'Gamma', 'Delta'}:
        new_df['#attributes'] = new_df['#attributes'] + 'status=VOC;'
    else:
        new_df['#attributes'] = new_df['#attributes'] + 'status=VOI;'
    
    #remove starting NaN; leave trailing ';'
    new_df['#attributes'] = new_df['#attributes'].str[3:]
    
    #fill in other GVF columns
    new_df['#seqid'] = df['#CHROM']
    new_df['#source'] = '.'
    new_df['#type'] = info[40].str.split(pat='=').apply(pd.Series)[1]
    new_df['#start'] = df['POS']
    new_df['#end'] = (df['POS'] + df['ALT'].str.len() - 1).astype(str)  #this needs fixing
    new_df['#score'] = '.'
    new_df['#strand'] = '+'
    new_df['#phase'] = '.'
    
    new_df = new_df[gvf_columns] #only keep the columns needed for a gvf file
    
    return new_df



#takes 3 arguments: an output file of vcftogvf.py, Anoosha's annotation file from Pokay, and the clade defining mutations tsv.
def add_functions(gvf, annotation_file, clade_file, strain):

    #load files into Pandas dataframes
    df = pd.read_csv(annotation_file, sep='\t', header=0) #load functional annotations spreadsheet

    clades = pd.read_csv(clade_file, sep='\t', header=0, usecols=['strain', 'mutation']) #load entire GVF file for modification
    clades = clades.loc[clades.strain == strain]
    attributes = gvf["#attributes"].str.split(pat=';').apply(pd.Series)

    hgvs_protein = attributes[0].str.split(pat='=').apply(pd.Series)[1]
    hgvs_nucleotide = attributes[1].str.split(pat='=').apply(pd.Series)[1]
    gvf["mutation"] = hgvs_protein.str[2:] #drop the prefix


    #merge annotated vcf and functional annotation files by 'mutation' column in the gvf
    for column in df.columns:
        df[column] = df[column].str.lstrip()
    merged_df = pd.merge(df, gvf, on=['mutation'], how='right') #add functional annotations
    merged_df = pd.merge(clades, merged_df, on=['mutation'], how='right') #add clade-defining mutations


    #collect all mutation groups (including reference mutation) in a column, sorted alphabetically
    #this is more roundabout than it needs to be; streamline with grouby() later
    merged_df["mutation_group"] = merged_df["comb_mutation"].astype(str) + ", '" + merged_df["mutation"].astype(str) + "'"
    mutation_groups = merged_df["mutation_group"].str.split(pat=',').apply(pd.Series)
    mutation_groups = mutation_groups.apply(lambda s:s.str.replace("'", ""))
    mutation_groups = mutation_groups.apply(lambda s:s.str.replace(" ", ""))
    mutation_groups = mutation_groups.transpose() 
    sorted_df = mutation_groups
    for column in mutation_groups.columns:
        sorted_df[column] = mutation_groups.sort_values(by=column, ignore_index=True)[column]
    sorted_df = sorted_df.transpose()
    
    #since they're sorted, put everything back into a single cell, don't care about dropna
    df3 = sorted_df.apply(lambda x :','.join(x.astype(str)),axis=1)
    unique_groups = df3.drop_duplicates() #92 unique groups
    unique_groups_multicol = sorted_df.drop_duplicates() #92 unique groups, not all members of which might be present in the gvf file
    merged_df["mutation_group_labeller"] = df3 #for sanity checking
    
    #make a unique id for mutation groups that have all members represented in the vcf
    #for groups with missing members, delete those functional annotations
    merged_df["id"] = 'NaN'
    id_num = 0
    for row in range(unique_groups.shape[0]):
        group_mutation_set = set(unique_groups_multicol.iloc[row])
        group_mutation_set = {x for x in group_mutation_set if (x==x and x!='nan')} #remove nan and 'nan' from set
        gvf_all_mutations = set(gvf['mutation'].unique())
        indices = merged_df[merged_df.mutation_group_labeller == unique_groups.iloc[row]].index.tolist()
        if group_mutation_set.issubset(gvf_all_mutations): #if all mutations in the group are in the vcf file, include those rows and give them an id
            merged_df.loc[merged_df.mutation_group_labeller == unique_groups.iloc[row], "id"] = "ID_" + str(id_num)
            id_num += 1
        else:
            merged_df = merged_df.drop(indices) #if not, drop group rows, leaving the remaining indices unchanged

    #change semicolons in function descriptions to colons
    merged_df['function_description'] = merged_df['function_description'].str.replace(';',':')
    #add key-value pairs to attributes column
    for column in ['function_category', 'source', 'citation', 'comb_mutation', 'function_description']:
        key = column.lower()
        merged_df[column] = merged_df[column].fillna('') #replace NaNs with empty string
        if column in ['function_category', 'citation', 'function_description']:
            merged_df["#attributes"] = merged_df["#attributes"].astype(str) + key + '=' + '"' + merged_df[column].astype(str) + '"' + ';'
        else:
            merged_df["#attributes"] = merged_df["#attributes"].astype(str) + key + '=' + merged_df[column].astype(str) + ';'

    #change clade-defining attribute to True/False depending on content of 'strain' column
    merged_df.loc[merged_df.strain == strain, "#attributes"] = merged_df.loc[merged_df.strain == strain, "#attributes"].astype(str)  + "clade_defining=True;"
    merged_df.loc[merged_df.strain != strain, "#attributes"] = merged_df.loc[merged_df.strain != strain, "#attributes"].astype(str)  + "clade_defining=False;"

    #add ID to attributes
    merged_df["#attributes"] = 'ID=' + merged_df['id'].astype(str) + ';' + merged_df["#attributes"].astype(str)
    
    
    #get list of names in tsv but not in functional annotations, and vice versa, saved as a .tsv
    tsv_names = gvf["mutation"].unique()
    pokay_names = df["mutation"].unique()
    print(str(np.setdiff1d(tsv_names, pokay_names).shape[0]) + "/" + str(tsv_names.shape[0]) + " mutation names were not found in pokay")
    in_pokay_only = pd.DataFrame({'in_pokay_only':np.setdiff1d(pokay_names, tsv_names)})
    in_tsv_only = pd.DataFrame({'in_tsv_only':np.setdiff1d(tsv_names, pokay_names)})
    leftover_names = in_tsv_only
    leftover_names["strain"] = strain
    
    clade_names = clades["mutation"].unique()
    leftover_clade_names = pd.DataFrame({'unmatched_clade_names':np.setdiff1d(clade_names, tsv_names)})
    leftover_clade_names["strain"] = strain
    
    return merged_df, leftover_names, gvf["mutation"].tolist(), leftover_clade_names
    
      

if __name__ == '__main__':
    
    args = parse_args()
    
    if not os.path.exists(args.vcfdir):
        print("VCF file folder not found")
        
    annotation_file = args.pokay
    clade_file = args.clades
    outdir = args.outdir
    
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    print("Processing vcf files in " + args.vcfdir + " ...")
    print("")
    
    pragmas = pd.DataFrame([['##gff-version 3'], ['##gvf-version 1.10'], ['##species NCBI_Taxonomy_URI=http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=2697049']]) #pragmas are in column 0

    for file in glob.glob(args.vcfdir + '/*.vcf'): #get all .vcf files
        print("Processing: " + file)
        
        #get strain name
        pat = r'.*?' + args.vcfdir + '(.*)_ids.*'
        match = re.search(pat, file)
        strain = match.group(1)
        print("strain: ", strain)
        
        #create gvf from annotated vcf (ignoring pragmas for now)
        gvf = vcftogvf(file, strain)
        #add functional annotations
        annotated_gvf, leftover_names, mutations, leftover_clade_names = add_functions(gvf, annotation_file, clade_file, strain)
        annotated_gvf = annotated_gvf[gvf_columns]
        #add pragmas to df, then save to .gvf
        annotated_gvf = pd.DataFrame(np.vstack([annotated_gvf.columns, annotated_gvf])) #columns are now 0, 1, ...
        final_gvf = pragmas.append(annotated_gvf)
        filepath = outdir + strain + ".annotated.gvf"
        print("saved as: ", filepath)
        print("")
        final_gvf.to_csv(filepath, sep='\t', index=False, header=False)
        
    print("Processing complete.")
        