# Conversion pipeline - not locally runnable

## Code files
- convert.py: Ray-based conversion script

## Requirements
- MuseScore executable (installed binary or .AppImage)

**run $export QT_QPA_PLATFORM="offscreen" before any other command**

- Python:
  - ms3: pip install git+https://github.com/johentsch/ms3@corpus_structure
  - ray
  - json
  - zipfile

## Input files
- mscz/: folder containing all .mscz files named $ID.mscz
- json/: folder containing pre-extracted metadata files

## Output files
- metadata/: folder containing all .json metadata files
- converted_mscz/: folder containing all converted .mscz files (no corrupted/outdated)
- features/: folder containing all features.zip files


## Summary
This script goes through the whole list of available .mscz files, doing:
- converting to newer version of musescore
- extracting musical features in \$FEATURES/\$ID.zip
- extracting metadata in \$METADATA/\$ID.json (or incrementing the existing file)

Errors are logged, and except if --all argument is specified, does not rerun over already converted files.


## How to run

### Example execution
```
export QT_QPA_PLATFORM="offscreen"
export DATA="../data/preprocessing_toy_example/"
python3  convert.py -a -m "/home/nathan/Downloads/MuseScore-4.0.0-x86_64.AppImage" -s $DATA/mscz/ -j $DATA/json/ -c $DATA/converted_mscz/ -f $DATA/features/ -u $DATA/conversion_errors/ -p $DATA/parsing_errors/ -n 4
```
### Details

`$ python3 convert.py $ARGS`
``` 
Args:
    -s, --scores_folder: location of original scores .mscz files (default='./mscz')
    -j, --json_folder: location of original/future .json metadata files (default='./metadata')
    -c, --conversion_folder: location of future converted .mscz files (default='./converted_mscz')
    -f, --features_folder: location of future extracted features .zip file (default='./features')
    -u, --unconvertible: location of conversion error files (default='./conversion_errors')
    -p, --unparseable: location of parsing error files (default='./parsing_errors')
    -n, --num_cpus: number of cores to use (default=12)
    -m, --musescore: MuseScore executable (default="./MuseScore-3.6.2.548021370-x86_64.AppImage")
    -a, --all: Do not skip JSON files that include the key __terminated__ (default: False)
    --skip: Skip the second call to MuseScore that extracts more 'metadata from the score after the conversion (default: False)

Output file(s):
    For every $ID that could be converted, :
        $FEATURES_FOLDER/$ID.zip
        $CONVERSION_FOLDER/$ID.mscz
        $JSON_FOLDER/$ID.json
```
