import os, time, subprocess
import ms3
import ray
import json
from zipfile import ZipFile

### Arch-Dependant parameters to check

MSCZ_FOLDER = os.path.abspath("./mscz")
# MSCZ_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/

JSON_FOLDER = os.path.abspath("./other_sources/metadata") # change to same as OUTPUT_PATHS['metadata'] to rewrite (and proper handling of stop/restart)

MUSESCORE_CMD = ms3.get_musescore("auto")
# MUSESCORE_CMD = "/usr/local/bin/AppImg???"
# MUSESCORE_CMD = "/home/erwan/.local/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"

NB_THREADS = 2
FULL_METADATA = True
JSON_IDS = set([os.path.splitext(v.name)[0] for v in os.scandir(JSON_FOLDER)]) 
MSCZ_IDS = set([os.path.splitext(v.name)[0] for v in os.scandir(MSCZ_FOLDER)])
JSON_IDS=JSON_IDS.intersection(MSCZ_IDS)
JSON_FILENAMES=[v+".json" for v in JSON_IDS]

OUTPUT_PATHS = dict(
    conversion=os.path.abspath("./converted_mscz"),
    features=os.path.abspath("./features"),
    metadata=os.path.abspath("./metadata"),
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
        mscz_file = os.path.join(MSCZ_FOLDER, ID + ".mscz")
        converted_mscz_file = os.path.join(OUTPUT_PATHS["conversion"], ID + ".mscz")
        json_outfile = os.path.join(OUTPUT_PATHS['metadata'], ID + ".json")

        if "__terminated__" in jsondict :
            continue
        score_meta=[]
        try:
            if FULL_METADATA:
                score_meta = subprocess.run(
                    [MUSESCORE_CMD, "--score-meta", mscz_file],
                    capture_output=True,
                    text=True,
                )
                if score_meta.returncode != 0:
                    raise Exception(score_meta.stderr)
            convert = subprocess.run(
                [MUSESCORE_CMD, "-o", converted_mscz_file, mscz_file],
                capture_output=True,
                text=True,
            )
            if convert.returncode != 0:
                raise Exception(convert.stderr)
            
            parsed = ms3.Score(mscz_file, read_only=True, ms=MUSESCORE_CMD)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            if '__error__' in jsondict:
                jsondict['__error__'].append(str(e))
            else:
                jsondict['__error__']=[str(e)]

            jsondict['__has_error__'] = True
            jsondict['__terminated__'] = True
            with open(json_outfile, "w", encoding='utf-8') as f:
                json.dump(jsondict, f)
            continue

        zip_features_file = os.path.join(OUTPUT_PATHS["features"], f"{ID}.zip")
        features_dict=dict(
        events=parsed.mscx.events(),
        notes=parsed.mscx.notes(),
        measures=parsed.mscx.measures(),
        labels=parsed.mscx.labels(),
        )
        
        with ZipFile(zip_features_file, 'w') as myzip:
            for name,feature in features_dict.items():
                if feature is not None:
                    feature.to_csv(f"{name}.tsv", sep="\t", index=False)
                    myzip.write(f"{name}.tsv")
                    os.remove(f"{name}.tsv")

        if FULL_METADATA:
            mscore_metadict = json.loads(score_meta.stdout)
            jsondict['scoremeta_metadata'] = mscore_metadict
        
        # To change once no NATypes left
        for k,v in parsed.mscx.metadata.items():
          jsondict['ms3_data_'+str(k)]  = str(v)
        # jsondict['ms3_data'] = parsed.mscx.metadata
        
        if not '__error__' in jsondict:
            jsondict['__error__']=[]
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
