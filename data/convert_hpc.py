import os, shutil, subprocess
import ms3
import ray

DATA_FOLDER = os.path.abspath('./mscz') 
# DATA_FOLDER = os.path.abspath('/scratch/data/musescore.com/') # on the HPC: /scratch/data/musescore.com/
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


musescore_cmd = ms3.get_musescore('auto')
threads=32
filenames=os.listdir(DATA_FOLDER)

@ray.remote
def process_chunk(low, high):
    fails=[]
    composer_known=[]
    for i in range(low,high):
        filename=filenames[i]
        ID, file_extension = os.path.splitext(filename)
        converted_file_path = os.path.join(CONVERSION_FOLDER, ID + '.mscx')
        file_path = os.path.join(DATA_FOLDER, filename)
        print(f"Converting {file_path} to {converted_file_path}...", end=' ')
        result = subprocess.run([musescore_cmd, "-o", converted_file_path, file_path], capture_output=False, text=True)
        print(f"Exit code: {result.returncode}")
        if result.returncode!=0:
            fails.append(ID)
            continue
            
        parsed = ms3.Score(converted_file_path, read_only=True)
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
        metadata = parsed.mscx.metadata # please add this nested dictionary to the JSON stored in the previous step
        metadata['id'] = ID
        if metadata['composer'] != '':
            compo_file=os.path.join(COMPOSERS_PATH, ID)
            f=open(compo_file,'a')
            f.write(metadata['composer'])
            f.close()
            composer_known.append(ID)
        metafile_path = os.path.join(OUTPUT_PATHS['metadata'], ID+'.txt')
        f=open(metafile_path, 'a')
        f.write(str(metadata))
        f.close()            
    return fails, composer_known
        
     
def main():
    ray.init(ignore_reinit_error=True)
    files=os.listdir(DATA_FOLDER)
    n=len(files)
    futures = [process_chunk.remote(i*(n//threads),min((i+1)*(n//threads),n)) for i in range (threads)]
    faillist, composerknownlist =ray.get(futures)
    failset = set()
    composerknownset = set()
    for l in faillist:
        for i in l:
            failset.add(i)
    f = open("failed_IDs", 'a')
    f.write("\n".join(failset))
    
    for l in composerknownlist:
        for i in l:
            composer_known.add(i)
    f = open("known_composers_IDs", 'a')
    f.write("\n".join(composer_known))
    print(f"% failed: {100*len(faillist)/n}, % with composer known: {100*len(composer_known)/n}")
    
        
if __name__ == "__main__":
    main()