import pandas as pd
import numpy as np

def parse_variant_file(dataframe):
    who_lineages = []
    for var in dataframe["pango_lineage"]:
        if "," in var:
            for temp in var.split(","):
                if not "[" in var:
                    who_lineages.append(temp)
                    who_lineages.append(temp+".*")
                else:
                    parent=temp[0]
                    child=temp[2:-1].split("|")
                    for c in child:
                        who_lineages.append(parent + str(c))
                        who_lineages.append(parent+str(c)+".*")
        else:
            who_lineages.append(var)
    return who_lineages
    

def unnest(df, col, reset_index=False):
# from https://stackoverflow.com/questions/21160134/flatten-a-column-with-value-of-type-list-while-duplicating-the-other-columns-va
    import pandas as pd
    col_flat = pd.DataFrame([[i, x] 
                       for i, y in df[col].apply(list).iteritems() 
                           for x in y], columns=['I', col])
    col_flat = col_flat.set_index('I')
    df = df.drop(col, 1)
    df = df.merge(col_flat, left_index=True, right_index=True)
    if reset_index:
        df = df.reset_index(drop=True)
    return df


def find_sample_size(table, lineage, vcf_file):


    if table != 'n/a':
        strain_tsv_df = pd.read_csv(table, delim_whitespace=True,
                                    usecols=['file', 'num_seqs'])

        # Reference mode
        if lineage != 'n/a':
            num_seqs = strain_tsv_df[strain_tsv_df['file'].str.startswith(
                lineage + ".qc.")]['num_seqs'].values
            sample_size = num_seqs[0]

        # user-uploaded fasta
        else:
            filename_to_match = vcf_file.split(".sorted")[0] \
                # looks like "strain.qc"
            num_seqs = strain_tsv_df[strain_tsv_df['file'].str.startswith(
                filename_to_match)]['num_seqs'].values
            sample_size = num_seqs[0]

    # user-uploaded vcf
    elif table == 'n/a' and lineage == 'n/a':
        sample_size = 'n/a'

    return sample_size



    
def parse_INFO(df): # return INFO dataframe with named columns, including EFF split apart
    # parse INFO column
    
    # sort out problematic sites tag formats   
    df['INFO'] = df['INFO'].str.replace('ps_filter;', 'ps_filter=;')
    df['INFO'] = df['INFO'].str.replace('ps_exc;', 'ps_exc=;')
    df['INFO'] = df['INFO'].str.replace('=n/a', '') #why is this here?
    df['INFO'] = df['INFO'].str.replace('mat_pep_id;', 'mat_pep_id=;')
    df['INFO'] = df['INFO'].str.replace('mat_pep_desc;', 'mat_pep_desc=;')
    df['INFO'] = df['INFO'].str.replace('mat_pep_acc', 'mat_pep_acc=')

    # make 'INFO' column easier to extract attributes from:
    # split at ;, form dataframe
    info = df['INFO'].str.split(pat=';').apply(pd.Series)
    for column in info.columns:
        split = info[column].str.split(pat='=').apply(pd.Series)
        title = split[0].drop_duplicates().tolist()[0]
        if isinstance(title, str):
            title = title.lower()
            content = split[1]
            # ignore "tag=" in column content
            info[column] = content
            # make attribute tag as column label
            info.rename(columns={column: title}, inplace=True)

    # parse EFF entry in INFO
    # series: extract everything between parentheses as elements of a
    # list
    def keep_both_protein_names(eff_string):
        #print("")
        #print("")
        eff_list = eff_string.split(",")

        #print("GIVEN:", eff_list)
        # if any records in the row contain '|p.', take only those records
        EFF_records_list = [s for s in eff_list if '|p.' in s]
        # if no records contain '|p.', take the "intergenic" record
        if len(EFF_records_list)==0:
            EFF_records_list = [s for s in eff_list if 'intergenic_region' in s]
        #print("")
        #print("RETURN:", EFF_records_list)
        return EFF_records_list
        
    info["eff_result"] = [keep_both_protein_names(x) for x in info['eff']] 

    #concatenate info and df horizontally to return just one object
    df = pd.concat([df, info], axis=1)
    df = df.drop(columns="INFO")
                 
    #next, duplicate relevant INFO rows
    df = unnest(df, "eff_result", reset_index=True)
    
    # expand the contents of eff_result into separate columns, named as in the 
    # VCF header
    eff_info = df['eff_result'].str.findall('\((.*?)\)').str[0]
    # split at pipe, form dataframe
    eff_info = eff_info.str.split(pat='|').apply(pd.Series)
    num_cols = len(eff_info.columns)
    eff_info_cols = ['Effect_Impact','Functional_Class','Codon_Change','Amino_Acid_Change','Amino_Acid_length','Gene_Name','Transcript_BioType','Gene_Coding','Transcript_ID','Exon_Rank','Genotype ERRORS', 'Genotype WARNINGS'][:num_cols]
    eff_info.columns = eff_info_cols

    df = pd.concat([df, eff_info], axis=1)
    df = df.drop(columns='eff_result')
    
    # create a "Names" column that holds the amino acid name (minus 'p.')
    # if there is one, or the nucleotide level name if not
    df["Names"] = df['Amino_Acid_Change'].str.rsplit(pat='/').apply(
        pd.Series)[0].str.replace("p.", "", regex=True)
    
    # split df['Amino_Acid_Change'] into two columns: one for HGVS amino acid
    # names, and the righthand column for nucleotide-level names
    df['Amino_Acid_Change'][~df['Amino_Acid_Change'].str.contains('/')] = '/' + df['Amino_Acid_Change']
    hgvs = df['Amino_Acid_Change'].str.rsplit(pat='/').apply(pd.Series)
    hgvs.columns = ["hgvs_protein", "hgvs_nucleotide"]
    df = pd.concat([df, hgvs], axis=1)
    
    # make adjustments to the nucleotide names
    # 1) change 'c.' to 'g.' for nucleotide names ### double check that we want this
    df["hgvs_nucleotide"] = df["hgvs_nucleotide"].str.replace("c.", "g.", regex=True) 
    df["hgvs_nucleotide"] = df["hgvs_nucleotide"].str.replace("n.", "g.", regex=True) 
    # 2) change nucleotide names of the form "g.C*4378A" to g.C4378AN;
    asterisk_mask = df["hgvs_nucleotide"].str.contains('\*')
    df["hgvs_nucleotide"][asterisk_mask] = 'g.' + df['REF'] + df['POS'] + \
                                     df['ALT']
    # 3) change 'Gene_Name' to "intergenic" where names contain a "*"
    df['Gene_Name'][asterisk_mask] = "intergenic"
    
    #rename some columns
    df = df.rename(columns={'Gene_Name': "vcf_gene", 'Functional_Class': "mutation_type"})

    return(df)
    
    
    
def add_variant_information(clade_file, merged_df, sample_size, strain):    
    # get clade_defining status, and then info from clades file
    # load clade-defining mutations file
    ### MZA: need to clean up this and add this into separate function "variant_info" 
    clades = pd.read_csv(clade_file, sep='\t', header=0)
    clades = clades.replace(np.nan, '', regex=True) #this is needed to append empty strings to attributes (otherwise datatype mismatch error)

    # find the relevant pango_lineage line in the clade file that
    # matches args.strain (call this line "var_to_match")
    ### replace this part with func "parse_variant_file" in functions.py
    #available_strains = parse_variant_file(clades)
    var_to_match = 'None'
    cladefile_strain = 'None'
    available_strains = []
    for var in clades['pango_lineage'].tolist():
        if "," in var:
            for temp in var.split(","):
                if "[" not in var:
                    available_strains.append(temp)
                    if strain.startswith(temp):
                        var_to_match = var
                else:
                    parent = temp[0]
                    child = temp[2:-3].split("|")
                    for c in child:
                        available_strains.append(parent + str(c))
                        available_strains.append(parent + str(c) + ".*")
                        if strain.startswith(parent + str(c)):
                            var_to_match = var
        else:
            available_strains.append(var)
            if strain.startswith(var):
                var_to_match = var
                
    # if strain in available_strains:
    if var_to_match !='None':
        print("var_to_match", var_to_match)
        # find the index of the relevant row
        var_index = clades.index[clades['pango_lineage'] == var_to_match].tolist()[0]
        print("var_index", var_index)
        print(clades.loc[var_index])
        # extract status, WHO strain name, etc. from clades file
        who_variant = clades.loc[var_index, 'variant']
        variant_type = clades.loc[var_index, 'variant_type']
        voi_designation_date = clades.loc[var_index, 'voi_designation_date']
        voc_designation_date = clades.loc[var_index, 'voc_designation_date']
        vum_designation_date = clades.loc[var_index, 'vum_designation_date']
        status = clades.loc[var_index, 'status']

        # add attributes from variant info file
        merged_df["#attributes"] = merged_df["#attributes"].astype(
            str) + "variant=" + who_variant + ';' + "variant_type=" + \
                                   variant_type + ';' + "voi_designation_date=" + \
                                   voi_designation_date + ';' + \
                                   "voc_designation_date=" + \
                                   voc_designation_date + ';' + \
                                   "vum_designation_date=" + \
                                   vum_designation_date + ';' + \
                                   "status=" + status + ';'
    else:
        merged_df["#attributes"] = merged_df["#attributes"].astype(
            str) + "clade_defining=n/a;" + "variant=n/a;" + \
                                   "variant_type=n/a;" + \
                                   "voi_designation_date=n/a;" + \
                                   "voc_designation_date=n/a;" + \
                                   "vum_designation_date=n/a;" + \
                                    "status=n/a;"
                                    
                                    
    return(merged_df)

