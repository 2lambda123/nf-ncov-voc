#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

@author: zohaib

This script extracts metadata for each VOC, VOI and VUM from the
provided Metadata file based on the assigned lineages. This script
also filters sequences based on the provided criteria.


"""

import argparse
import pandas as pd
import csv
import datetime as dt

def parse_args():
    parser = argparse.ArgumentParser(
        description='Extracts Variants of Concern and Interest from '
                    'Metadata file')
    parser.add_argument('--table', type=str, default=None,
                        help='Metadata file (.tsv) format')
    #parser.add_argument('--voc', type=str, default=None,
    #                    help='VOC e.g. B.1.1.7')
    parser.add_argument('--samplingsize', type=int, default=0,
                        help='Sample size, if "0" all sequences '
                             'extracted; Default=0')
    parser.add_argument('--startdate', type=str, default=None,
                        help='Date of submission from (yyyy-mm-dd); '
                             'Default=None')
    parser.add_argument('--enddate', type=str, default=None,
                        help='Date of submission to (yyyy-mm-dd); '
                             'Default=None')
    parser.add_argument('--window', type=int, default=None,
                        help='Number of days between start and end date '
                             'Default=7')                           
    return parser.parse_args()


def sub_sampling(dataframe, subsampling):
    if (subsampling > 0) and (dataframe.shape[0] > subsampling):
        dataframe = dataframe.sample(n=subsampling, replace=False)
    return dataframe


def write_ids(dataframe, start_date, end_date):
    ids = dataframe['isolate'].tolist()
    with open( str(start_date)+ "_" + str(end_date) + ".txt", 'w') as \
            filehandle:
        filehandle.writelines("%s\n" % id for id in ids)


def write_metadata(dataframe, start_date, end_date):
    dataframe.to_csv( str(start_date)+ "_" + str(end_date) + 
                     "_Metadata.csv.gz", sep="\t", compression='gzip',
                     quoting=csv.QUOTE_NONE, index=False, header=True)


def filter_metadata(dataframe):
    dataframe = dataframe[dataframe['host_scientific_name'].str.lower() ==
                          'Homo sapiens'.lower()]
    if 'length' in dataframe.columns:
        dataframe = dataframe[dataframe['length'] >= 29000]        
    return dataframe


if __name__ == '__main__':
    args = parse_args()
    

    Metadata = pd.read_csv(args.table, sep="\t", low_memory=False, compression='gzip',
                           parse_dates=['sample_collection_date'])

    if 'sample_collection_date' in Metadata.columns:
        Metadata['sample_collection_date'] = pd.to_datetime(Metadata[
                                            'sample_collection_date'],
                                            format='%Y-%m-%d',
                                            errors='coerce')

        sdate = pd.to_datetime(args.startdate, format='%Y-%m-%d')
        edate = pd.to_datetime(args.enddate, format='%Y-%m-%d')
        window=args.window

    #Metadata = Metadata[Metadata['sample_collection_date'].isin(pd.date_range(sdate, edate))]
    #Metadata = Metadata.sort_values('sample_collection_date')
    #Metadata = Metadata.reset_index()
    """ Filtering for human associated and consensus sequence of
        at least 29Kb """
    print(len(Metadata))
    Metadata = filter_metadata(dataframe=Metadata)
    print(len(Metadata))
    while sdate <= edate:
        query_date = sdate + pd.DateOffset(days=6)
        print(sdate, query_date)
        sub_meta = Metadata.query('sample_collection_date >= @sdate and sample_collection_date <= @query_date')
        print(len(sub_meta))
        sub_meta = sub_sampling(dataframe=sub_meta, subsampling=args.samplingsize)
        
        write_ids(dataframe=sub_meta, start_date=str(sdate)[:10], end_date=str(query_date)[:10])
        write_metadata(dataframe=sub_meta, start_date=str(sdate)[:10], end_date=str(query_date)[:10])
        
        sdate += pd.DateOffset(days=window)
    
    