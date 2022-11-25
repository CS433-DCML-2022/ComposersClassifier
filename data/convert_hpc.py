import os, shutil, subprocess
import ms3
import ray

### Arch-Dependant parameters to check

DATA_FOLDER = os.path.abspath('./mscz') 
# DATA_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/
MUSESCORE_CMD = ms3.get_musescore('auto')
# MUSESCORE_CMD = "/usr/local/bin/AppImg???"
# MUSESCORE_CMD = "/home/erwan/.local/bin/MuseScore-3.6.2.548021370-x86_64.AppImage"

NB_THREADS=32
MSCZ_FILENAMES=os.listdir(DATA_FOLDER)

CONVERSION_FOLDER = os.path.abspath('./mscx')
OUTPUT_PATHS = dict(
    events = os.path.abspath('./events'),
    notes = os.path.abspath('./notes'),
    measures = os.path.abspath('./measures'),
    labels = os.path.abspath('./labels'),
    metadata = os.path.abspath('./metadata'),
)
COMPOSERS_PATH = os.path.abspath('./composers')

for dir in [CONVERSION_FOLDER,OUTPUT_PATHS['events'],OUTPUT_PATHS['notes'],OUTPUT_PATHS['measures'],OUTPUT_PATHS['labels'],OUTPUT_PATHS['metadata'],COMPOSERS_PATH]:
    if not os.path.exists(dir):
        os.makedirs(dir)

@ray.remote
def process_chunk(low, high):
    fails=[]
    composer_known=[]
    for i in range(low,high):
        filename=MSCZ_FILENAMES[i]
        ID, file_extension = os.path.splitext(filename)
        converted_file_path = os.path.join(CONVERSION_FOLDER, ID + '.mscx')
        file_path = os.path.join(DATA_FOLDER, filename)
        print(f"Converting {file_path} to {converted_file_path}...", end=' ')
        result = subprocess.run([MUSESCORE_CMD, "-o", converted_file_path, file_path], capture_output=False, text=True)
        print(f"Exit code: {result.returncode}")
        if result.returncode!=0:
            fails.append(ID)
            continue
        try:
            parsed = ms3.Score(converted_file_path, read_only=True)
        except:
            fails.append(ID)
            continue
        tsv_name = f"{ID}.tsv"
        dataframes = dict(
        events = parsed.mscx.events,
        notes = parsed.mscx.notes,
        measures = parsed.mscx.measures,
        labels = parsed.mscx.labels,
        )
        for facet, df in dataframes.items():
            if df is None:
                continue
            tsv_path = os.path.join(OUTPUT_PATHS[facet], tsv_name)
            df.to_csv(tsv_path, sep='\t', index=False)
        metadata = parsed.mscx.metadata
        metadata['id'] = ID
        if metadata['composer'] != '':
            compo_file=os.path.join(COMPOSERS_PATH, ID)
            f=open(compo_file,'a')
            f.write(metadata['composer'])
            f.close()
            composer_known.append(ID)
        metafile_path = os.path.join(OUTPUT_PATHS['metadata'], ID+'.txt')
        f=open(metafile_path, 'a')
        f.write(str(metadata)) # Could be cleaner
        f.close()            
    return fails, composer_known
        
     
def main():
    ray.init(ignore_reinit_error=True)
    files=os.listdir(DATA_FOLDER)
    n=len(files)
    futures = [process_chunk.remote(i*(n//NB_THREADS),min((i+1)*(n//NB_THREADS),n)) for i in range (NB_THREADS)]
    returns = ray.get(futures)
    failset = set()
    composerknownset = set()
    for item in returns:
        faillist, composerknownlist = item
        for i in faillist:
            failset.add(i)
        for i in composerknownlist:
            composerknownset.add(i)
    f = open("failed_IDs", 'a')
    f.write("\n".join(failset))
    f.close()
    f = open("known_composers_IDs", 'a')
    f.write("\n".join(composerknownset))
    f.close()
    log = open("log.txt", 'a')
    log.write("% failed: {100*len(failset)/n}, % with composer known: {100*len(composerknownset)/n}")
    log.close()
    
if __name__ == "__main__":
    main()