import os, time, subprocess
import ms3
import ray
import json
from ray.exceptions import TaskCancelledError

### Arch-Dependant parameters to check

DATA_FOLDER = os.path.abspath("./mscz")
JSON_FOLDER = os.path.abspath("./other_sources/metadata")
# DATA_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/
MUSESCORE_CMD = ms3.get_musescore("auto")
# MUSESCORE_CMD = "/usr/local/bin/AppImg???"
# MUSESCORE_CMD = "/home/erwan/.local/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"

NB_THREADS = 2
JSON_FILENAMES = os.listdir(JSON_FOLDER)
# MSCZ_FILENAMES = set([v for _,v in os.scandir(DATA_FOLDER)]) 
# optimize this with scandir

OUTPUT_PATHS = dict(
    conversion=os.path.abspath("./mscx"),
    events=os.path.abspath("./events"),
    notes=os.path.abspath("./notes"),
    measures=os.path.abspath("./measures"),
    labels=os.path.abspath("./labels"),
    metadata=os.path.abspath("./metadata"),
    logs=os.path.abspath("./logs"),
    errors=os.path.abspath("./logs/errors"),
    temp=os.path.abspath("./logs/temp"),
    # composers = os.path.abspath('./composers')
)

for dir in OUTPUT_PATHS.values():
    if not os.path.exists(dir):
        os.makedirs(dir)


@ray.remote
def process_chunk(low, high):
    # print("Instance received files to work on : ", JSON_FILENAMES[low:high])

    for i in range(low, high):
        json_filename = JSON_FILENAMES[i]
        ID, _ = os.path.splitext(json_filename)
        json_file = os.path.join(JSON_FOLDER, json_filename)
        with open(json_file, "r", encoding='utf-8') as f:
            jsondict = json.load(f)
        mscz_file = os.path.join(DATA_FOLDER, ID + ".mscz")
        json_outfile = os.path.join(OUTPUT_PATHS["metadata"], ID + ".json")

        if "__terminated__" in jsondict :
            continue
        try:
            if not os.path.exists(mscz_file): # make set to improve perf
                raise Exception(".mscz file not found")
            # TODO make this an optional
            result = subprocess.run(
                [MUSESCORE_CMD, "--score-meta", mscz_file],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise Exception(result.stderr)
            parsed = ms3.Score(mscz_file, read_only=True, ms=MUSESCORE_CMD)
            # convert to new format
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            jsondict['__error__'] = [str(e)] # append if previously ?
            jsondict['__has_error__'] = True
            jsondict['__terminated__'] = True
            with open(json_outfile, "w", encoding='utf-8') as f:
                json.dump(jsondict, f)
            continue

        tsv_name = f"{ID}.tsv"
        dataframes = dict(
            events=parsed.mscx.events(),
            notes=parsed.mscx.notes(),
            measures=parsed.mscx.measures(),
            labels=parsed.mscx.labels(),
        )
        for facet, df in dataframes.items():
            if df is None:
                continue
            tsv_path = os.path.join(OUTPUT_PATHS[facet], tsv_name)
            df.to_csv(tsv_path, sep="\t", index=False) # to pickle all of them

        # open zip file - go through all 4 features - tsv feature - add to zip - finish zip

        mscore_metadict = json.loads(result.stdout)
        jsondict['scoremeta_metdata'] = mscore_metadict
        
        for k,v in parsed.mscx.metadata.items():
          jsondict['ms3_data_'+str(k)]  = str(v)
        # jsondict['ms3_data'] = parsed.mscx.metadata
        
        jsondict['__error__'] = [] # keep if there is a value already
        jsondict['__has_error__'] = False
        jsondict['__terminated__'] = True
        with open(json_outfile, "w", encoding='utf-8') as f:
            json.dump(jsondict, f)
    return


def main():
    ray.init(ignore_reinit_error=True)

    n_files = len(JSON_FILENAMES[:20])
    chunk_size = (n_files // NB_THREADS) + 1
    futures = [
        process_chunk.remote(i * chunk_size, min((i + 1) * chunk_size, n_files))
        for i in range(NB_THREADS)
    ]
    ray.get(futures)


if __name__ == "__main__":
    main()
