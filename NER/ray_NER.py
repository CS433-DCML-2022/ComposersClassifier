import argparse
import os, subprocess
from typing import Optional

import ms3
import ray
import json
from zipfile import ZipFile


@ray.remote
def extract_composer(ID: str,
                 json_file: str,
                 json_with_composer_folder: str,
                 skip: bool = True,
                 ) -> None:
    print(f"Parsing ID {ID}")
    with open(json_file, "r", encoding='utf-8') as f:
        jsondict = json.load(f)
    if skip and "__first_composer__" in jsondict:
        print(f"Skipped ID {ID}")
        return

    json_file_with_composer = os.path.join(json_with_composer_folder, ID + ".json")

    def write_json(jsondict: dict, non_empty: bool):
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(jsondict, f)
        if non_empty:
            with open(json_file_with_composer, "w", encoding='utf-8') as f:
                json.dump(jsondict, f)


    first_composer = "unknown"
    # extract first_composer
    
    jsondict["first_composer"]=first_composer
    write_json(jsondict, first_composer!="unknown")
    print(json_file + f' overwritten, copied? {first_composer!="unknown"}')
    return


def main(args):
    ray.init(ignore_reinit_error=True, num_cpus=int(args.num_cpus))

    json_folder = os.path.abspath(args.json_folder)
    JSON_WITH_COMPOSER_FOLDER = ray.put(os.path.abspath(args.composer_folder))
    SKIP = ray.put(not args.all)

    def make_id2path_dict(path):
        print("Gathering files from" + path)
        return {os.path.splitext(entry.name)[0]: entry.path for entry in os.scandir(path) if entry.is_file()}

    json_files = make_id2path_dict(json_folder)
    ALL_IDS = set(json_files.keys())


    for dir in ray.get([JSON_WITH_COMPOSER_FOLDER]):
        if not os.path.exists(dir):
            os.makedirs(dir)

    n_files = len(ALL_IDS)
    print(f"Number of JSON files to handle: {n_files}")
    futures = [
        extract_composer.remote(ID=ID,
                            json_file=json_files[ID],
                            json_with_composer_folder=JSON_WITH_COMPOSER_FOLDER,
                            skip=SKIP)
        for ID in ALL_IDS
    ]
    ray.get(futures)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process JSON AND MSCZ.""")
    parser.add_argument('-j', '--json_folder', default='./metadata')
    parser.add_argument('-c', '--composer_folder', default='./metadata_with_composere')
    parser.add_argument('-n', '--num_cpus', default=12, help='Number of CPUs to be used in parallel.')
    parser.add_argument('-a', '--all', action='store_true', help='Do not skip JSON files that include the key __first_composer__')

    args = parser.parse_args()
    main(args)
