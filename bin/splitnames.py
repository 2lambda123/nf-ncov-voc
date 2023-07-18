#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 15:03:49 2023

@author: madeline

If args.ingvf, the attributes completed by this script are: 
['multi_aa_name', 'multiaa_comb_mutation']

This script is specific to Pokay functional annotations for
SARS-CoV-2, to harmonize Pokay mutation names with VCF mutation names.
"""

import argparse
import pandas as pd
import numpy as np
from functions import separate_attributes, rejoin_attributes, \
    split_names, unnest_multi
from functions import empty_attributes, gvf_columns

def parse_args():
    parser = argparse.ArgumentParser(
        description='Splits composite mutation names in specified files')
    parser.add_argument('--ingvf', type=str, default=None,
                        help='Path to the GVF file output of vcf2gvf.py')
    parser.add_argument('--functional_annotations', type=str,
                        default=None, help='TSV file of functional '
                                           'annotations')
    parser.add_argument('--outgvf', type=str,
                        help='Filename for the output gvf file')
    parser.add_argument('--out_functions', type=str,
                        help='Filename for the output functional \
                        annotations file')
    parser.add_argument('--names_to_split', type=str,
                        default=None,
                        help='.tsv of multi-aa mutation names to '
                             'split up into individual aa names')
    return parser.parse_args()


if __name__ == '__main__':

    args = parse_args()
    
    # split names in gvf file
    
    # read in gvf file
    gvf = pd.read_csv(args.ingvf, sep='\t', names=gvf_columns, index_col=False)

    # remove pragmas and original header row
    pragmas = gvf[gvf['#seqid'].astype(str).str.contains("##")]
    pragmas.columns = range(9)
    pragmas = pragmas.fillna('')
    gvf = gvf[~gvf['#seqid'].astype(str).str.contains("#")]

    # expand #attributes into columns to edit separately
    gvf = separate_attributes(gvf)

    # split names in "Names" attribute into separate rows
    gvf = split_names(args.names_to_split, gvf, col_to_split='Name')
    
    # rename IDs: rows with the same entry in 'Name'
    # get the same ID
    gvf['ID'] = 'ID_' + gvf.groupby('Name', sort=False).ngroup().astype(str)
    
    # merge attributes back into a single column
    gvf = rejoin_attributes(gvf, empty_attributes)

    # discard temporary columns
    gvf = gvf[gvf_columns]
    
    # add pragmas to gvf
    # columns are now 0, 1, ...
    final_gvf = pd.DataFrame(np.vstack([gvf.columns, gvf]))
    final_gvf = pragmas.append(final_gvf)
    
    # save modified file to .gvf
    filepath = args.outgvf
    print("Saved as: ", filepath)
    print("")
    final_gvf.to_csv(filepath, sep='\t', index=False, header=False)



    # split names in functional annotations file
    
    # read in functional annotations file
    df = pd.read_csv(args.functional_annotations, sep='\t', header=0)
    # remove any leading/trailing spaces
    for column in df.columns:
        df[column] = df[column].astype(str).str.strip()
    col_order = df.columns
    
    # split names in "comb_mutation" column
    
    # data cleaning: fix parsing error
    df['comb_mutation'] = df['comb_mutation'].str.replace(
        "B.1.617.2\\tT19R", "T19R", regex=False)
    # data cleaning: remove quotation marks, spaces
    for x in ["'", " "]:
        df['comb_mutation'] = df['comb_mutation'].str.replace(x, '')
    
    # load names_to_split file
    names_to_split_df = pd.read_csv(args.names_to_split, sep='\t', header=0)
    # remove spaces and quotation marks from 'split_into' column
    for x in [' ', "'"]:
        names_to_split_df['split_into'] = names_to_split_df[
            'split_into'].str.replace(x, "")
    # make names_to_split_df into a dictionary
    split_dict = dict(zip(names_to_split_df.name, names_to_split_df.split_into))

    # do str.replace on 'comb_mutation' and 'mutation' columns
    for name in split_dict.keys():
        df['comb_mutation'] = df['comb_mutation'].str.replace(
            name, split_dict[name])
        df['mutation'] = df['mutation'].str.replace(
            name, split_dict[name])
    
    # unnest "mutation" column so each mutation name gets its
    # own row
    df['mutation'] = df['mutation'].str.split(',')
    df = unnest_multi(df, ['mutation'], reset_index=True)
    
    df = df[col_order]
    
    # save modified file
    filepath = args.out_functions
    print("Saved as: ", filepath)
    print("")
    df.to_csv(filepath, sep='\t', index=False, header=True)
