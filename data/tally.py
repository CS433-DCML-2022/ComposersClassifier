import argparse
import os
from typing import Tuple

import ray
import json
import pandas as pd


@ray.remote
def read_json(ID: str,
              json_file: str,
              scores_folder: str,
              conversion_folder: str,
              features_folder: str,
              ) -> Tuple[str, dict]:
    # print(f"Looking up {json_file}")
    with open(json_file, "r", encoding='utf-8') as f:
        jsondict = json.load(f)
    score_name = ID + ".mscz"
    original_mscz_file = os.path.join(scores_folder, score_name)
    converted_mscz_file = os.path.join(conversion_folder, score_name)
    zip_features_file = os.path.join(features_folder, ID + ".zip")

    result = {}
    original = os.path.isfile(original_mscz_file)
    result['original'] = original
    if original:
        result['terminated'] = "__terminated__" in jsondict
        if 'last_error' in jsondict:
            result['last_error'] = jsondict['last_error']
        if os.path.isfile(converted_mscz_file):
            result['converted'] = os.stat(converted_mscz_file).st_size
        if os.path.isfile(zip_features_file):
            result['features'] = os.stat(zip_features_file).st_size
    return ID, result


def main(args):
    ray.init(num_cpus=int(args.num_cpus))

    json_folder = os.path.abspath(args.json_folder)
    ORIGINAL_SCORES_FOLDER = ray.put(os.path.abspath(args.scores_folder))
    CONVERSION_FOLDER = ray.put(os.path.abspath(args.conversion_folder))
    FEATURES_FOLDER = ray.put(os.path.abspath(args.features_folder))

    print("Collecting futures...")
    futures = []
    for entry in os.scandir(json_folder):
        if not entry.is_file():
            continue
        ID = os.path.splitext(entry.name)[0]
        json_file = entry.path
        futures.append(read_json.remote(ID=ID,
                                        json_file=json_file,
                                        scores_folder=ORIGINAL_SCORES_FOLDER,
                                        conversion_folder=CONVERSION_FOLDER,
                                        features_folder=FEATURES_FOLDER,
                                        ))
    print(f"Processing {len(futures)} JSON files on {args.num_cpus} CPUs.")
    records = {}
    while len(futures):
        finished, futures = ray.wait(futures)
        for ID, row in ray.get(finished):
            records[ID] = row

    tallied = pd.DataFrame.from_dict(records, orient='index')
    tallied.index.rename('ID', inplace=True)
    tallied.loc[:, ['converted', 'features']] = tallied[['converted', 'features']].astype('Int64')
    tallied.to_csv('tallied.tsv', sep='\t')
    print(f"'{os.path.abspath('tallied.tsv')}' successfully written.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process JSON AND MSCZ.""")
    parser.add_argument('-s', '--scores_folder', default='./mscz')
    parser.add_argument('-j', '--json_folder', default='./metadata')
    parser.add_argument('-c', '--conversion_folder', default='./converted_mscz')
    parser.add_argument('-f', '--features_folder', default='./features')
    parser.add_argument('-n', '--num_cpus', default=12, help='Number of CPUs to be used in parallel.')

    args = parser.parse_args()
    main(args)
