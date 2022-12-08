import argparse
import os
from typing import Tuple

import ray
import json
import pandas as pd
import csv


#Collects all relevant fields to be written to tsv to be processed later
#saves the need to process all files again if composer processing script updates
def get_all_relevant_fields(jsondict: dict) -> dict:

    #retrieve all possible composer fields
    possibleComposers = list()
    possibleTitles = list()
    possibleDescriptions = list()

    #composer fields
    ms3dict = jsondict.get("ms3_metadata")
    if ms3dict:
        field1 = ms3dict.get("composer")
        if field1:
            possibleComposers.append(field1)
        field2 = ms3dict.get("composer_text")
        if field2:
            possibleComposers.append(field2)
    mscoredict = jsondict.get("musescore_metadata")
    if mscoredict:
        mscoredict = mscoredict.get("metadata")
        field3 = mscoredict.get("composer")
        if field3:
            possibleComposers.append(field3)
        textDataField = mscoredict.get("textFramesData")
        if textDataField:
            textDataComposersList = textDataField.get("composers")
            if textDataComposersList:
                for textDataComposer in textDataComposersList:
                    if textDataComposer != '':
                        possibleComposers.append(textDataComposer)

    #retrieve other fields of interest for processing (all titles, subtitles and description fields)
    title1 = jsondict["title"]
    if title1:
        possibleTitles.append(title1)
    if ms3dict:
        title2 = ms3dict.get("title_text")
        if title2:
            possibleTitles.append(title2)

    desc1 = jsondict["description"]
    if desc1:
        possibleDescriptions.append(desc1)
    if mscoredict:
        title3 = mscoredict.get("title")
        if title3:
            possibleTitles.append(title3)
        if textDataField:
            subtitles = mscoredict.get("subtitles")
            if subtitles:
                for sub in subtitles:
                    if sub != '':
                        possibleDescriptions.append(sub)
            titles = mscoredict.get("titles")
            if titles:
                for t in titles:
                    if t != '':
                        possibleTitles.append(t)

    result = {}
    for column, values in zip(('composer', 'title', 'description') ,(possibleComposers,possibleTitles,possibleDescriptions)):
        # remove duplicates and combine into a single value
        deduplicated = set(values)
        value = '; '.join(deduplicated)
        if value != '':
            result[column] = value
    return result



@ray.remote
def read_json(ID: str,
              json_file: str,
              scores_folder: str,
              conversion_folder: str,
              features_folder: str,
              composer_mode: bool = False,
              ) -> Tuple[str, dict]:
    # print(f"Looking up {json_file}")
    with open(json_file, "r", encoding='utf-8') as f:
        jsondict = json.load(f)
    score_name = ID + ".mscz"
    original_mscz_file = os.path.join(scores_folder, score_name)
    converted_mscz_file = os.path.join(conversion_folder, score_name)
    zip_features_file = os.path.join(features_folder, ID + ".zip")
    if composer_mode:
        id_row = get_all_relevant_fields(jsondict)
    else:
        id_row = {}
        original = os.path.isfile(original_mscz_file)
        id_row['original'] = original
        if original:
            id_row['terminated'] = "__terminated__" in jsondict
            if os.path.isfile(converted_mscz_file):
                id_row['converted'] = os.stat(converted_mscz_file).st_size
            if os.path.isfile(zip_features_file):
                id_row['features'] = os.stat(zip_features_file).st_size
    return ID, id_row


def main(args):
    ray.init(num_cpus=int(args.num_cpus))

    json_folder = os.path.abspath(args.json_folder)
    ORIGINAL_SCORES_FOLDER = ray.put(os.path.abspath(args.scores_folder))
    CONVERSION_FOLDER = ray.put(os.path.abspath(args.conversion_folder))
    features_folder = os.path.abspath(args.features_folder)
    FEATURES_FOLDER = ray.put(features_folder)
    COMPOSER_MODE = ray.put(args.composer_mode)

    print("Collecting futures...")
    futures = []
    for entry in os.scandir(json_folder):
        if not entry.is_file():
            continue
        ID = os.path.splitext(entry.name)[0]
        if args.composer_mode:
            zip_features_file = os.path.join(features_folder, ID + ".zip")
            if not os.path.isfile(zip_features_file):
                continue
        json_file = entry.path
        futures.append(read_json.remote(ID=ID,
                                        json_file=json_file,
                                        scores_folder=ORIGINAL_SCORES_FOLDER,
                                        conversion_folder=CONVERSION_FOLDER,
                                        features_folder=FEATURES_FOLDER,
                                        composer_mode=COMPOSER_MODE,
                                        ))
    n_files = len(futures)
    print(f"Processing {n_files} JSON files on {args.num_cpus} CPUs.")
    records = dict(ray.get(futures))

    tallied = pd.DataFrame.from_dict(records, orient='index')
    tallied.index.rename('ID', inplace=True)
    if not args.composer_mode:
        tallied.loc[:, ['converted', 'features']] = tallied[['converted', 'features']].astype('Int64')
    zip_name = args.file_name + '.zip'
    csv_name = args.file_name + '.csv'
    tallied.to_csv(zip_name, escapechar='\\', quoting= csv.QUOTE_ALL, compression=dict(method='zip',
                                                  archive_name=csv_name))
    print(f"'{os.path.abspath(zip_name)}' successfully written.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process JSON AND MSCZ.""")
    parser.add_argument('--composer_mode', action='store_true', help="Setting this flag means going only through successfully parsed files and tallying composer, title and description fields. "
                                                            "Otherwise (by default), the script will go through all JSON files and tally information on which scores have been converted and parsed.")
    parser.add_argument('--file_name', default='tallied')
    parser.add_argument('-s', '--scores_folder', default='./mscz')
    parser.add_argument('-j', '--json_folder', default='./metadata')
    parser.add_argument('-c', '--conversion_folder', default='./converted_mscz')
    parser.add_argument('-f', '--features_folder', default='./features')
    parser.add_argument('-n', '--num_cpus', default=12, help='Number of CPUs to be used in parallel.')

    args = parser.parse_args()
    main(args)
