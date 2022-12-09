import csv
import os
import argparse
from ray_NER import basic_clean

''' Parse initial tally tsv into slim composers tsv'''

def main(args):

    saveDel = args.save_deleted_in_csv == 'True'

    tsv_dir = os.path.abspath(args.tsv_file)
    slim_tsv_dir = os.path.abspath('./slim_' + args.tsv_file.lstrip('./'))
    if saveDel: deleted_tsv_dir = os.path.abspath('./del_' + args.tsv_file.lstrip('./'))

    #process large tsv line by line
    with open(tsv_dir) as f_in, open(slim_tsv_dir, "w") as f_out:
        writer = csv.writer(f_out, delimiter='\t', lineterminator='\n')
        reader = csv.reader(f_in, delimiter="\t")
        if saveDel: f_out2 = open(deleted_tsv_dir, "w"); del_writer = csv.writer(f_out2, delimiter='\t', lineterminator='\n')        
        for line in reader:
            ID,composers = line[0],line[1].split(';')
            cleanComposers = [basic_clean(composer) for composer in composers if not (basic_clean(composer) == None)]
            #if no composers reamining post-clean, don't write?
            #write all good composers?
            if len(cleanComposers) > 0:
                writer.writerow([ID,cleanComposers])
            else:
                # print("No remaining composers for ID: " + str(ID) + ", Deleted: " + str(composers))
                if saveDel: del_writer.writerow([ID,composers])
                # del_writer.writerow([ID,[composer + " :" + basic_clean(composer,debug=True) for composer in composers]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process TSV.""")
    parser.add_argument('-t', '--tsv_file', default='./tallied.tsv')
    parser.add_argument('-d', '--save_deleted_in_csv', default='False')
    args = parser.parse_args()
    main(args)
