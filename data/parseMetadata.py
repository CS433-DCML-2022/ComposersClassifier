import csv
import os
import argparse
import sys
from ray_NER import basic_clean, initModelDict, namedEntityRecognition

'''Reduce metadata.csv into csv containing only clean composers'''

#removes null bytes on input
def fix_nulls(s):
    for line in s:
        yield line.replace('\0', ' ')

def main(args):
    csv.field_size_limit(sys.maxsize)
    saveDel = args.save_deleted_in_csv == 'True'
    parseTextNER = args.parse_text_fields == 'True'
    parseAll = args.parse_all_fields == 'True'

    if parseTextNER:
        modelDict = initModelDict()

    csv_dir = os.path.abspath(args.csv_file)
    slim_csv_dir = os.path.abspath('./slim_' + args.csv_file.lstrip('./'))
    slim_all_csv_dir = os.path.abspath('./slim_all_fields_' + args.csv_file.lstrip('./'))
    if parseAll: slim_csv_dir = slim_all_csv_dir

    if saveDel: deleted_csv_dir = os.path.abspath('./del_' + args.csv_file.lstrip('./'))
    if parseTextNER: ner_csv_dir = os.path.abspath('./ner_' + args.csv_file.lstrip('./')); error_csv_dir =os.path.abspath('./ner_error_' + args.csv_file.lstrip('./'))

    #process large csv line by line
    with open(csv_dir) as f_in, open(slim_csv_dir, "w+") as f_out:
        writer = csv.writer(f_out, delimiter=',', lineterminator='\n')
        reader = csv.reader(fix_nulls(f_in), delimiter=",")
        if saveDel: f_out2 = open(deleted_csv_dir, "w+"); del_writer = csv.writer(f_out2, delimiter='\t', lineterminator='\n')  
        if parseTextNER or parseAll: f_out3 = open(ner_csv_dir,  "w+"); ner_writer = csv.writer(f_out3, delimiter='\t', lineterminator='\n');  f_out4 = open(error_csv_dir, "w+"); error_csv_writer = csv.writer(f_out4, delimiter='\t', lineterminator='\n');  
        for line in reader:
            ID,composers = line[0],line[3].split(';')
            cleanComposers = [basic_clean(composer) for composer in composers]
            if len(cleanComposers) > 0:
                cleanComposers = [x for x in cleanComposers if x]
                #write all good composers
                if len(cleanComposers) > 0:
                    cleanComposers = list(set(cleanComposers))
                    cleanComposers = '; '.join(cleanComposers)
                    writer.writerow([ID,cleanComposers])
                    continue
                #else use alternative text fields if specified -t -a
                else: 
                    if parseTextNER or parseAll: 
                        title,desc = line[1].split(';'),line[2].split(';')
                        titleEntities,descEntities = None,None
                        if title:
                            titleEntities = namedEntityRecognition(ID," ".join(title), modelDict ,  checkKnown=False, composersDict=None,composersList=None, error_csv_writer=error_csv_writer)
                            if titleEntities: titleEntities = [basic_clean(x, strict=True,initials=True) for x in titleEntities if x]; titleEntities = list(set(titleEntities))
                            if titleEntities: titleEntities = "; ".join([x for x in titleEntities if x]).title()
                            if titleEntities and parseAll: writer.writerow([ID,titleEntities]); continue
                            else: titleEntities = None
                        if desc:
                            descEntities = namedEntityRecognition(ID," ".join(desc), modelDict , checkKnown=False, composersDict=None,composersList=None, error_csv_writer=error_csv_writer)
                            if descEntities: descEntities = [basic_clean(x, strict=True, initials=True) for x in descEntities if x]; descEntities = list(set(descEntities))
                            if descEntities: descEntities = "; ".join([x for x in descEntities if x]).title()
                            if descEntities and parseAll: writer.writerow([ID,descEntities]); continue
                            else: descEntities = None
                            
                        if not parseAll: ner_writer.writerow([ID,titleEntities,descEntities])
                    if saveDel: del_writer.writerow([ID,composers])
            else:
                if saveDel: del_writer.writerow([ID,composers])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process Metadata CSV.""")
    parser.add_argument('-c', '--csv_file', default='./metadata.csv')
    parser.add_argument('-d', '--save_deleted_in_csv', default='False')
    parser.add_argument('-t', '--parse_text_fields', default='False')
    parser.add_argument('-a', '--parse_all_fields', default='False')
    args = parser.parse_args()
    main(args)
