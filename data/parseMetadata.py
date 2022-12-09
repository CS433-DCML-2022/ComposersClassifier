import csv
import os
import argparse
import sys
from ray_NER import basic_clean

''' Parse initial tally tsv into slim composers tsv'''

def fix_nulls(s):
    for line in s:
        yield line.replace('\0', ' ')

def main(args):
    csv.field_size_limit(sys.maxsize)
    saveDel = args.save_deleted_in_csv == 'True'

    csv_dir = os.path.abspath(args.csv_file)
    slim_csv_dir = os.path.abspath('./slim_' + args.csv_file.lstrip('./'))
    if saveDel: deleted_csv_dir = os.path.abspath('./del_' + args.csv_file.lstrip('./'))

    #process large tsv line by line
    with open(csv_dir) as f_in, open(slim_csv_dir, "w+") as f_out:
        writer = csv.writer(f_out, delimiter=',', lineterminator='\n')
        reader = csv.reader(fix_nulls(f_in), delimiter=",")
        if saveDel: f_out2 = open(deleted_csv_dir, "w+"); del_writer = csv.writer(f_out2, delimiter='\t', lineterminator='\n')        
        for line in reader:
            ID,composers = line[0],line[3].split(';')
            cleanComposers = [basic_clean(composer) for composer in composers]
            #remove duplicates
            #if no composers reamining post-clean, don't write?
            #write all good composers?
            if len(cleanComposers) > 0:
                cleanComposers = [x for x in cleanComposers if x]
                if len(cleanComposers) > 0:
                    cleanComposers = list(set(cleanComposers))
                    cleanComposers = '; '.join(cleanComposers)
                    writer.writerow([ID,cleanComposers])
                else: 
                    if saveDel: del_writer.writerow([ID,composers])
            else:
                if saveDel: del_writer.writerow([ID,composers])
                # print("No remaining composers for ID: " + str(ID) + ", Deleted: " + str(composers))
                # del_writer.writerow([ID,[composer + " :" + basic_clean(composer,debug=True) for composer in composers]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process Metadata CSV.""")
    parser.add_argument('-t', '--csv_file', default='./metadata.csv')
    parser.add_argument('-d', '--save_deleted_in_csv', default='False')
    args = parser.parse_args()
    main(args)
