import argparse
import os, subprocess
from typing import Optional

import ms3
import ray
import json
from zipfile import ZipFile


def basic_clean(composer: str, debug: bool = False) -> str:
        #normalize
        composer = composer.strip(" ").strip("\n")

        #remove multiple composers?
        composer = composer.split("\n")[0].split(",")[0]

        #we dont want to remove other languages
        composer= ''.join(e for e in composer if e.isalnum() or e==" " or e=="," or e=="-" or e=="." or e=="\\" or e=="//" or not e.isascii())
        composer = str.title(str.lower(composer))

        #remove any entries with arranger at index 0
        composerToList = composer.split(" ")
        if disqualifyingWords(composerToList):
            if debug: return 'DQ'; 
            else : return None

        #trim composer names up until date
        for i, word in enumerate(composerToList):
            word = ''.join(l for l in word if l.isalnum())
            if len(word) == 0 : continue
            #fixes bug where '三' is numeric
            if word[0].isnumeric() and word[0].isascii():
                composerToList = composerToList[:i]
                break

        #remove known bad words
        composerStringList = [x for x in filter(lambda x: not badWord(x),composerToList)]

        composer = " ".join(composerStringList)

        #remove longer than 5 words (allows for titles like, 'the x of the y')
        if len(composer.split(" "))>5:             
            if debug: return '>5'; 
            else : return None

        #length check
        if len(composer) < 4 :
            if debug: return '<4'; 
            else : return None

        # print(composer)
        return composer.strip(" ").strip("-")


#determine if composer is actually arranger
def disqualifyingWords(wordList):
    for index,word in enumerate(wordList):
        word=str.lower(word)
        word = ''.join(e for e in word if e.isalnum()) 
        if len(word) > 2:
            #keep larry, barry and harry
            if 'arr' in word[:3] and index == 0: return True
            if 'transcription' in word and index == 0: return True
            if 'transcripción' in word and index == 0: return True
            if 'trans'in word and index == 0: return True
            if 'trad'in word and index == 0: return True
    return False

#if any bad words then remove them
def badWord(word):
    #normalize
    word=str.lower(word)
    word= ''.join(e for e in word if e.isalnum())

    if len(word) > 40: return True

    #remove numbers
    if word.isnumeric(): return True

    #remove any common words
    bad_words = ['and', 'anon', 'anonymous', 'ar', 'ararranger', 'aritst', 'arr', 'arranged', 'arrangement', 'arrg', 'bei', 'by', 'choral', 'comp', 'composed', 'composer', 'compositor', 'created', 'designed', 'edit', 'edited', 'ft', 'game', 'harmony', 'in', 'instrumental', 'known', 'me', 'mel', 'melody', 'music', 'music', 'musical', 'musik', 'musique', 'original', 'pianist', 'piece', 'pieces', 'played', 'score', 'soundtrack', 'trad', 'traditional', 'traditionell', 'tradicionel', 'trans', 'transcription', 'unknown', 'version', 'version', 'word', 'words', 'write', 'wrote', 'wrote']
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
        #retrieve all possible composer fields
        possibleComposers = list()
        ms3dict = jsondict.get("ms3_metadata")
        if ms3dict:
            field1 = ms3dict.get("composer")
            if field1:
                c1 = basic_clean(field1)
                if c1: possibleComposers.append(c1)
            field2 = ms3dict.get("composer_text")
            if field2:
                c2 = basic_clean(field2)
                if c2: possibleComposers.append(c2)
        mscoredict = jsondict.get("musescore_metadata")
        if mscoredict:
            mscoredict = mscoredict.get("metadata")
            field3 = mscoredict.get("composer")
            if field3:
                c3 = basic_clean(field3)
                if c3: possibleComposers.append(c3)
            textDataField = mscoredict.get("textFramesData")
            if textDataField:
                textDataComposersList = textDataField.get("composers")
                if textDataComposersList:
                    for textDataComposer in textDataComposersList:
                        tdc = basic_clean(textDataComposer)
                        if tdc: possibleComposers.append(tdc)
        if len(possibleComposers) > 0: return possibleComposers[0]
        else: 
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
    parser.add_argument('-c', '--composer_folder', default='./metadata_with_composer')
    parser.add_argument('-n', '--num_cpus', default=12, help='Number of CPUs to be used in parallel.')
    parser.add_argument('-a', '--all', action='store_true', help='Do not skip JSON files that include the key __first_composer__')

    args = parser.parse_args()
    main(args)
