import gc
import os, subprocess
from datetime import datetime
from typing import Optional

import ms3
import numpy as np
import ray
import json
from zipfile import ZipFile

from tqdm import tqdm

### Arch-Dependant parameters to check

MSCZ_FOLDER = os.path.abspath("./mscz")
# MSCZ_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/

JSON_FOLDER = os.path.abspath("./metadata") # change to same as OUTPUT_PATHS['metadata'] to rewrite (and proper handling of stop/restart)

#MUSESCORE_CMD = ms3.get_musescore("auto")
# MUSESCORE_CMD = "/usr/local/bin/AppImg???"
MUSESCORE_CMD = "./MuseScore-3.6.2.548021370-x86_64.AppImage"

def make_id2path_dict(path):
    print("Gathering files from" + path)
    return {os.path.splitext(entry.name)[0]: entry.path for entry in os.scandir(path) if entry.is_file()}

NB_THREADS = 32
FULL_METADATA = True
JSON_FILES = make_id2path_dict(JSON_FOLDER)
MSCZ_FILES = make_id2path_dict(MSCZ_FOLDER)
ALL_IDS = list(set(JSON_FILES.keys()).intersection(set(MSCZ_FILES.keys())))

OUTPUT_PATHS = dict(
    conversion=os.path.abspath("./converted_mscz"),
    features=os.path.abspath("./features"),
    metadata=os.path.abspath("./metadata"),
)
print(OUTPUT_PATHS)

for dir in OUTPUT_PATHS.values():
    if not os.path.exists(dir):
        os.makedirs(dir)


@ray.remote
def process_chunk(low: int, high: int) -> None:
    # print("Instance received files to work on : ", JSON_FILENAMES[low:high])
    for i in range(low, high):
        ID = ALL_IDS[i]
        json_file = JSON_FILES[ID]
        with open(json_file, "r", encoding='utf-8') as f:
            jsondict = json.load(f)
        if "__terminated__" in jsondict :
            continue
        mscz_file = MSCZ_FILES[ID]
        converted_mscz_file = os.path.join(OUTPUT_PATHS["conversion"], ID + ".mscz")
        json_outfile = os.path.join(OUTPUT_PATHS['metadata'], ID + ".json")

        def write_json(jsondict: dict, error: Optional[str] = None):
            nonlocal json_outfile
            jsondict['__terminated__'] = True
            if '__error__' not in jsondict:
                jsondict['__error__'] = []
            if error is not None:
                jsondict['__error__'].append(str(error))
                jsondict['__has_error__'] = True
            with open(json_outfile, "w", encoding='utf-8') as f:
                json.dump(jsondict, f)

        try:
            convert = subprocess.run(
                [MUSESCORE_CMD, "-o", converted_mscz_file, mscz_file],
                capture_output=True,
                text=True,
            )
            if convert.returncode != 0:
                raise Exception(convert.stderr)
            parsed = ms3.Score()
            with ms3.capture_parse_logs(parsed.logger, level='i') as capturer:
                parsed.parse_mscx(converted_mscz_file, read_only=True)
                log_messages = capturer.content_list
        except KeyboardInterrupt:
            raise
        except Exception as e:
            write_json(jsondict, error=e)
            continue
        jsondict['ms3_metadata'] = parsed.mscx.metadata
        zip_features_file = os.path.join(OUTPUT_PATHS["features"], f"{ID}.zip")
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

        error = None
        if FULL_METADATA:
            score_meta = subprocess.run(
                [MUSESCORE_CMD, "--score-meta", converted_mscz_file],
                capture_output=True,
                text=True,
            )
            if score_meta.returncode == 0:
                jsondict['musescore_metadata'] = json.loads(score_meta.stdout)
            else:
                error = score_meta.stderr

        write_json(jsondict, error)
    return


def main():
    ray.init(ignore_reinit_error=True)

    n_files = len(ALL_IDS)
    print(f"Overlap between JSON and MSCZ files: {n_files}")
    batch_size = NB_THREADS * NB_THREADS
    n_runs = n_files // batch_size + 1
    # n_files_per_thread = (n_files // NB_THREADS) + 1
    # n_runs = n_files_per_thread // NB_THREADS + 1
    relative_start_indices = np.arange(NB_THREADS)[..., np.newaxis] * NB_THREADS
    relative_indices = np.hstack([relative_start_indices,
                                  relative_start_indices + NB_THREADS - 1])
    for run in tqdm(range(n_runs)):
        start_index = run * batch_size
        indices = start_index + relative_indices
        if run + 1 == n_runs:
            # last run
            futures = [process_chunk.remote(low, min(high, n_files)) for low, high in indices]
        else:
            futures = [process_chunk.remote(low, high) for low, high in indices]
        print(f"{datetime.now()} Starting run {run+1}/{n_runs} @ index {start_index}")
        _ = ray.get(futures)
        gc.collect()


if __name__ == "__main__":
    main()
