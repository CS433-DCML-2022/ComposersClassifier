import argparse
import os, subprocess
from typing import Optional

import ms3
import ray
import json
from zipfile import ZipFile


def basic_clean(composer: str) -> str:
        #normalize
        composer = composer.strip(" ").strip("\n")

        #remove multiple composers?
        composer = composer.split("\n")[0].split(",")[0]

        composer= ''.join(e for e in composer if e.isalnum() or e==" " or e=="," or e=="-" or e=="." or e=="\\" or e=="//")
        composer = str.title(str.lower(composer))

        #remove any entries with arranger at index 0
        composerToList = composer.split(" ")
        if disqualifyingWords(composerToList): return "unknown"

        #remove known bad words
        composerStringList = filter(lambda x: not badWord(x),composerToList)

        composer = " ".join(composerStringList)
        for i, word in composerStringList:
            if word[0].isnumeric():
                composer = " ".join(composerStringList[:i])
                break
        #remove longer than 3 words?
        if len(composer.split(" "))>=4: return "unknown"

        #length check
        if len(composer) < 4 :return "unknown"
        # print(composer)
        return composer.strip(" ").strip("-")
    
    
#determine if composer is actually arranger
def disqualifyingWords(wordList):
    for index,word in enumerate(wordList):
        word=str.lower(word)
        word = ''.join(e for e in word if e.isalnum()) 
        
        if 'arr' in word and index == 0: return True
        if 'trans' in word and index == 0: return True

    return False

#if any bad words then remove them
def badWord(word):
    #normalize
    if word.isnumeric(): return True
    word=str.lower(word)
    word = ''.join(e for e in word if e.isalnum())

    if len(word) > 40: return True

    #remove numbers
    if word.isnumeric(): return True

    #remove any common words
    bad_words = set(["ft","composer", "composed", "by", "comp", "words", "word", "and", "music", "piece", "pieces", "arr", "ar" "arranger", "arranged", "arrangement", "ar", "arrg", "transcription", "trans", "choral", "wrote", "version", "in", "music", "melody", "harmony", "created", "mel", "musical", "soundtrack", "game", "score", "version", "unknown", "musique", "original", "edit", "edited", "instrumental", "musik", "bei", "write", "wrote"])
    if word in bad_words: return True

    return False

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
    
    def get_name() -> str:
        ms3dict = jsondict.get("ms3_metadata")
        if ms3dict:
            field1 = ms3dict.get("composer")
            if field1:
                return basic_clean(field1)
            field2 = ms3dict.get("composer")
            if field2:
                return basic_clean(field2)
        mscoredict = jsondict.get("musescore_metadata")    
        if mscoredict:
            mscoredict = mscoredict.get("metadata")
            if not mscoredict:
                return "unknown"
            field1 = mscoredict.get("composer")
            if field1:
                print("Second dict, first field")
                return basic_clean(field1)
            textDataField = mscoredict.get("textFramesData")
            if textDataField:
                textDataComposersList = textDataField.get("composers")
                if textDataComposersList:
                    print("First dict, second field")
                    return basic_clean(textDataComposersList[0])
        return "unknown"
    
    first_composer = get_name()    
    jsondict["__first_composer__"]=first_composer
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
