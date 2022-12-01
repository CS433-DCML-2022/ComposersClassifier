import os, time, subprocess
import ms3
import ray
import json
from ray.exceptions import TaskCancelledError

### Arch-Dependant parameters to check

DATA_FOLDER = os.path.abspath("./mscz")
# DATA_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/
MUSESCORE_CMD = ms3.get_musescore("auto")
# MUSESCORE_CMD = "/usr/local/bin/AppImg???"
# MUSESCORE_CMD = "/home/erwan/.local/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"

NB_THREADS = 2
MSCZ_FILENAMES = os.listdir(DATA_FOLDER)
MSCZ_FILENAMES_LEFT = []

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

FAILED_IDS = os.path.abspath("./logs/failed_IDs.txt")
SUCCESS_IDS = os.path.abspath("./logs/success_IDs.txt")


for dir in OUTPUT_PATHS.values():
    if not os.path.exists(dir):
        os.makedirs(dir)
for f in [FAILED_IDS, SUCCESS_IDS]:
    if not os.path.exists(f):
        open(f, "w", encoding="utf-8").close()


@ray.remote
def process_chunk(low, high, worker_id):
    # print("Instance received files to work on : ", MSCZ_FILENAMES_LEFT[low:high])
    fails = []
    successes = []
    # composer_known=[]
    try:
        for i in range(low, high):
            filename = MSCZ_FILENAMES_LEFT[i]
            ID, file_extension = os.path.splitext(filename)
            converted_file_path = os.path.join(OUTPUT_PATHS["conversion"], ID + ".mscx")
            file_path = os.path.join(DATA_FOLDER, filename)
            try:
                print(f"Converting {file_path} to {converted_file_path}...", end=" ")
                result = subprocess.run(
                    [MUSESCORE_CMD, "-o", converted_file_path, file_path],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0
                result = subprocess.run(
                    [MUSESCORE_CMD, "--score-meta", converted_file_path, file_path],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0
                parsed = ms3.Score(converted_file_path, read_only=True)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                fails.append(ID)
                error_file = os.path.join(OUTPUT_PATHS["errors"], ID)
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(
                        "Error code: " + str(result.returncode) + ", " + result.stderr
                    )
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
                df.to_csv(tsv_path, sep="\t", index=False)

            metadict = {
                k: str(v) for k, v in parsed.mscx.metadata.items() if str(v) != ""
            }  # str cast to handle natypes ?
            metadict["id"] = ID
            mscore_metadict = json.loads(result.stdout)
            for k, v in mscore_metadict.items():
                if str(v) != "":
                    metadict["musescore_data_" + str(k)] = str(v)

            # composer=''
            # if 'composer' in metadict and metadict['composer'] != '':
            #     composer=metadict['composer']
            # if 'Composer' in metadict and metadict['composer'] != '':
            #     composer=metadict['Composer']
            # if composer!='':
            #     compo_file=os.path.join(OUTPUT_PATHS['COMPOSERS'], ID)
            #     with open(compo_file,'w', encoding='utf-8') as f:
            #         f.write(metadict['composer'])
            #     composer_known.append(ID)

            metafile_path = os.path.join(OUTPUT_PATHS["metadata"], ID + ".json")
            with open(metafile_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(metadict, indent=2, skipkeys=True))

            successes.append(ID)
    except KeyboardInterrupt:
        print("Keyboard interrupt was detected!")
        with open(
            os.path.join(OUTPUT_PATHS["temp"], f"successes_{worker_id}.txt"),
            "a",
            encoding="utf-8",
        ) as s:
            s.write("\n".join(successes))
        with open(
            os.path.join(OUTPUT_PATHS["temp"], f"fails_{worker_id}.txt"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write("\n".join(fails))
        print(
            "Wrote fails to : ",
            os.path.join(OUTPUT_PATHS["logs"], f"fails_{worker_id}.txt"),
            " and successes to: ",
            os.path.join(OUTPUT_PATHS["logs"], f"successes_{worker_id}.txt"),
        )
        pass
    except Exception as e:
        print("Something happened: ", str(e))
        pass
    return fails, successes  # ,composer_known


def main():
    ray.init(ignore_reinit_error=True)
    files = set(MSCZ_FILENAMES)
    with open(FAILED_IDS, "r", encoding="utf-8") as failfile:
        fails = set(failfile.read().splitlines())
    with open(SUCCESS_IDS, "r", encoding="utf-8") as successfile:
        successes = set(successfile.read().splitlines())
    # print("Already handled: successes:  ", successes, " fails: ", fails)
    local_nb_success = 0
    local_nb_fail = 0

    global MSCZ_FILENAMES_LEFT
    MSCZ_FILENAMES_LEFT = list((files.difference(fails)).difference(successes))
    n_files = len(MSCZ_FILENAMES_LEFT)
    chunk_size = (n_files // NB_THREADS) + 1
    workers_ids = range(NB_THREADS)
    futures = [
        process_chunk.remote(i * chunk_size, min((i + 1) * chunk_size, n_files), i)
        for i in range(NB_THREADS)
    ]
    returns = []
    try:
        returns = ray.get(futures)
    except KeyboardInterrupt:
        for x in futures:
            ray.cancel(x)  # Sends KeyboardInterrupt to function
        time.sleep(2)
        for worker_id in workers_ids:
            s = os.path.join(OUTPUT_PATHS["temp"], f"successes_{worker_id}.txt")
            f = os.path.join(OUTPUT_PATHS["temp"], f"fails_{worker_id}.txt")
            if os.path.exists(s) and os.path.exists(f):
                print("Found temp files for aborted worker ", worker_id)
                with open(s, "r", encoding="utf-8") as fsucc:
                    succ = fsucc.read().splitlines()
                with open(f, "r", encoding="utf-8") as ffail:
                    fail = ffail.read().splitlines()
                returns.append((fail, succ))
                os.remove(s)
                os.remove(f)
        pass
    failfile = open(FAILED_IDS, "a", encoding="utf-8")
    successfile = open(SUCCESS_IDS, "a", encoding="utf-8")
    for item in returns:
        faillist, successlist = item
        # print(item, len(faillist), len(successlist))
        local_nb_fail += len(faillist)
        local_nb_success += len(successlist)
        for i in faillist:
            failfile.write(i + ".mscz\n")
        for i in successlist:
            successfile.write(i + ".mscz\n")
    failfile.close()
    successfile.close()

    with open(
        os.path.join(OUTPUT_PATHS["logs"], "log.txt"), "a", encoding="utf-8"
    ) as log:
        # log.write(f"% failed: {100*len(failset)/n_files}, % with composer known: {100*len(composerknownset)/n_files}")
        log.write(
            f"Handled {local_nb_fail+local_nb_success} .mscz files, {local_nb_fail} failed and {local_nb_success} succeeded\n"
        )


if __name__ == "__main__":
    main()
