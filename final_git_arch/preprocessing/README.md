# Preprocessing pipeline - not locally runnable

## Code files
- tally.py

## Requirements
- Python:
  - ray
  - json
  - pandas

## Input files
All described folders were produced as part of the "Initial Conversion" step
- mscz/: folder containing all .mscz files, named $ID.mscx
- metadata/: folder containing all .json metadata files
- converted_mscz/: folder containing all converted .mscz files (no corrupted/outdated)
- features/: folder containing all features.zip files

## Output
- metadata.csv: summary of all score IDs, with status or further needed metadata fields
- 
## Summary
This script goes through all $ID.json files available in metadata/ folder, then does the following:
- (if composer mode): store all possibly useful text fields  
Format: ID,[composerTextList],[titleTextList], [DescriptionTextList]
- (if not): check a .mscz file exists for this ID in mscz/ folder (meaning it is an original), then stores the size of the converted .mscz if exists (meaning it terminated without error), and size of extracted features.zip file  
Format: ID,[original],[terminated], [converted], [features], [last_error]

## How to run

### Example execution
```
export DATA="../data/preprocessing_toy_example/"
python3  tally.py -s $DATA/mscz/ -j $DATA/json/  -c $DATA/converted_mscz/ -f $DATA/features/ -n 4 --file_name $DATA/tallied.csv
python3  tally.py -s $DATA/mscz/ -j $DATA/json/  -c $DATA/converted_mscz/ -f $DATA/features/ -n 4 --composer_mode --file_name $DATA/composers_tallied.csv
```
### Details

`$ python3 tally.py $ARGS`
``` 
Args:
    --composer_mode: Setting this flag means going only through successfully parsed files and tallying composer, title and description fields. Otherwise (by default), the script will go through all JSON files and tally information on which scores have been converted and parsed.
    --file_name: filename of output (+'.csv')
    -s, --scores_folder: location of original .mscz files (default='./mscz')
    -j, --json_folder: location of metadata .json files (default='./metadata')
    -c, --conversion_folder: location of converted .mscz files (default='./converted_mscz')
    -f, --features_folder: location of musical features .zip files (default='./features')
    -n, --num_cpus: number of cores to use (default=12)

Output file(s):
    default: tallied.csv
    if specified under --file_name $NAME, $NAME.csv
```

## Processing explanation

The relevant text fields within the JSON that are kept are:

- From the ms3_metadata dictionary:
    - "composer" 
    - "composer_text" 
- from the "musescore_metadata" dictionary:
    - from the inner "metadata" dictionary:
        - "composer"
        - from the inner "textFramesData dictionary:
            - all entries from the list "composers"

Alternative text fields include:

- "title"
- "description" 
- From the ms3_metadata dictionary:
    - "title_text"
- from the "musescore_metadata" dictionary:
 - from the inner "metadata" dictionary:
    "title"
    - from the inner "textData" dictionary:
        - from the inner "textFramesData dictionary:
            - all entries from the list "subtitles"
            - all entries from the list "titles"