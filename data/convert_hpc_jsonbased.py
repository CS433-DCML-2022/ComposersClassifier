import argparse
import os, subprocess
from typing import Optional

import ms3 # pip install git+https://github.com/johentsch/ms3@corpus_structure
import ray
import json
from zipfile import ZipFile


@ray.remote
def process_file(ID: str,
                 json_file: str,
                 mscz_file: str,
                 conversion_folder: str,
                 features_folder: str,
                 conversion_errors_folder: str,
                 parsing_errors_folder: str,
                 musescore: str,
                 skip: bool = True,
                 more: bool = True
                 ) -> None:
    print(f"Parsing ID {ID}")
    zip_features_file = os.path.join(features_folder, ID + ".zip")
    if skip and os.path.isfile(zip_features_file):
        print(f"Skipped ID {ID} because features are already available.")
        return

    with open(json_file, "r", encoding='utf-8') as f:
        jsondict = json.load(f)

    def write_json(error: Optional[str] = None):
        nonlocal jsondict
        jsondict['__terminated__'] = True
        if error is not None:
            jsondict['last_error'] = str(error)
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(jsondict, f)

    converted_mscz_file = os.path.join(conversion_folder, ID + ".mscz")
    conversion_error_file = os.path.join(conversion_errors_folder, ID)
    if skip and os.path.isfile(conversion_error_file):
        print(f"Skipped ID {ID} because file with conversion errors is present.")
        return
    if skip and os.path.isfile(converted_mscz_file):
        print(f"ID {ID}: Skipped conversion because converted file is already present.")
    else:
        try:
            convert = subprocess.run(
                [musescore, "-o", converted_mscz_file, mscz_file],
                capture_output=True,
                text=True,
            )
            if convert.returncode != 0:
                raise Exception(convert.stderr)
        except Exception as e:
            exception = str(e)
            with open(conversion_error_file, 'w', encoding='utf-8') as f:
                f.write(exception)
            write_json(exception)
            print(f"ID {ID} could not be converted. Stored errors as {conversion_error_file}:\n{exception}")
            return

    parsing_errors_file = os.path.join(parsing_errors_folder, ID)

    try:
        parsed = ms3.Score(level='i')
        with ms3.capture_parse_logs(parsed.logger, level='i') as capturer:
            parsed.parse_mscx(converted_mscz_file, read_only=True)
            log_messages = capturer.content_list
        if os.path.isfile(zip_features_file):
            os.remove(zip_features_file)
        for facet, dataframe in (('events', parsed.mscx.events()),
                                 ('notes', parsed.mscx.notes()),
                                 ('measures', parsed.mscx.measures()),
                                 ('labels', parsed.mscx.labels()),
                                 ):
            if dataframe is not None:
                dataframe.to_csv(zip_features_file,
                                 sep='\t',
                                 index=False,
                                 mode='a',
                                 compression=dict(method='zip',
                                                  archive_name=facet + '.tsv'))
        with ZipFile(zip_features_file, 'a') as myzip:
            myzip.writestr('log.txt', '\n'.join(log_messages))
        print(zip_features_file + ' written.')
    except Exception as e:
        exception = str(e)
        with open(parsing_errors_file, 'w', encoding='utf-8') as f:
            f.write(exception)
        write_json(exception)
        print(f"ID {ID} could not be parsed. Stored errors as {parsing_errors_file}:\n{exception}")
        return

    jsondict['ms3_metadata'] = parsed.mscx.metadata

    error = None
    if more:
        score_meta = subprocess.run(
            [musescore, "--score-meta", converted_mscz_file],
            capture_output=True,
            text=True,
        )
        if score_meta.returncode == 0:
            jsondict['musescore_metadata'] = json.loads(score_meta.stdout)
        else:
            error = score_meta.stderr

    write_json(error)
    print(json_file + ' overwritten.')
    return


def main(args):
    ray.init(ignore_reinit_error=True, num_cpus=int(args.num_cpus))

    mscz_folder = os.path.abspath(args.scores_folder)
    json_folder = os.path.abspath(args.json_folder)
    CONVERSION_FOLDER = ray.put(os.path.abspath(args.conversion_folder))
    FEATURES_FOLDER = ray.put(os.path.abspath(args.features_folder))
    CONVERSION_ERRORS_FOLDER = ray.put(os.path.abspath((args.unconvertible)))
    PARSING_ERRORS_FOLDER = ray.put(os.path.abspath((args.unparseable)))
    musescore = ms3.get_musescore(args.musescore)
    MUSESCORE = ray.put(musescore)
    SKIP = ray.put(not args.all)
    MORE = ray.put(not args.skip)

    def make_id2path_dict(path):
        print("Gathering files from" + path)
        return {os.path.splitext(entry.name)[0]: entry.path for entry in os.scandir(path) if entry.is_file()}

    json_files = make_id2path_dict(json_folder)
    mscz_files = make_id2path_dict(mscz_folder)
    ALL_IDS = set(json_files.keys()).intersection(set(mscz_files.keys()))


    for dir in ray.get([CONVERSION_FOLDER, FEATURES_FOLDER, CONVERSION_ERRORS_FOLDER, PARSING_ERRORS_FOLDER]):
        if not os.path.exists(dir):
            os.makedirs(dir)

    n_files = len(ALL_IDS)
    print(f"Overlap between JSON and MSCZ files: {n_files}")
    futures = [
        process_file.remote(ID=ID,
                            json_file=json_files[ID],
                            mscz_file=mscz_files[ID],
                            conversion_folder=CONVERSION_FOLDER,
                            features_folder=FEATURES_FOLDER,
                            conversion_errors_folder=CONVERSION_ERRORS_FOLDER,
                            parsing_errors_folder=PARSING_ERRORS_FOLDER,
                            musescore=MUSESCORE,
                            skip=SKIP,
                            more=MORE)
        for ID in ALL_IDS
    ]
    ray.get(futures)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Process JSON AND MSCZ.""")
    parser.add_argument('-s', '--scores_folder', default='./mscz')
    parser.add_argument('-j', '--json_folder', default='./metadata')
    parser.add_argument('-c', '--conversion_folder', default='./converted_mscz')
    parser.add_argument('-f', '--features_folder', default='./features')
    parser.add_argument('-u', '--unconvertible', default='./conversion_errors')
    parser.add_argument('-p', '--unparseable', default='./parsing_errors')
    parser.add_argument('-n', '--num_cpus', default=12, help='Number of CPUs to be used in parallel.')
    parser.add_argument('-m', '--musescore', default="./MuseScore-3.6.2.548021370-x86_64.AppImage", help='MuseScore executable.')
    parser.add_argument('-a', '--all', action='store_true', help='Do not skip JSON files that include the key __terminated__')
    parser.add_argument('--skip', action='store_true', help='Skip the second call to MuseScore that extracts more '
                                                            'metadata from the score after the conversion.')

    args = parser.parse_args()
    main(args)
