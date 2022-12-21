import argparse
import os, subprocess
from typing import Optional

import ms3
import ray
import json
from zipfile import ZipFile
import spacy
from langdetect import detect
import csv

#Language Settings
#All lang models require install on target system with python -m spacy download language_core_model_name
#SMALLMODEL uses a smaller spacy model, if false uses transformer or large model if available
MULTIPLELANGUAGES = True
ALTLANGS = {'de':["de_core_news_sm","de_dep_news_trf"], 'ko':["ko_core_news_sm","ko_core_news_lg"],'en':["en_core_web_sm","en_core_web_trf"],'ja':["ja_core_news_sm","ja_core_news_trf"],'ru':["ru_core_news_sm","ru_core_news_lg"],'it':["it_core_news_sm","it_core_news_lg"], 'es':["es_core_news_sm", "es_dep_new_trf"] }
SMALLMODEL = True

'''Draft Named Entity Recognition for retrieving possible composers from associated metadata'''

#make composer list (composer,ID) and dict with ID -> [names]
def loadComposers(file):
    composersDict = dict()
    composersList = list()
    with open(file,'r') as comps:
        for line in comps.readlines():
            splitLine = line.split(',')
            ID = splitLine[0].split('/')[-1]
            composer = splitLine[1].strip('\n')
            #TO DO - add stem flag to first instance of composer added to dict, all found composer instances of different languages for the same ID will be converted to the string of the canonical instance to reduce variation
            if composersDict.get(ID):composersDict[ID] = composersDict[ID].append(composer)
            else: composersDict[ID] = list(composer)
            composersList.append((composer,ID))
    return composersDict,composersList

#initialize spacy models
def initModelDict():
    modelDict = dict()
    #init model/s
    if MULTIPLELANGUAGES:
        for lang in ALTLANGS.keys():
            if not SMALLMODEL:
                modelDict[lang]=spacy.load(ALTLANGS[lang][1])
            else: modelDict[lang]=spacy.load(ALTLANGS[lang][0])
    else:
        if not SMALLMODEL: modelDict['en'] = spacy.load("en_core_web_rtf") 
        else: modelDict['en'] = spacy.load("en_core_web_sm")
    return modelDict


#used primarily for parsing B grade metadata fields
def namedEntityRecognition(ID,stringToParse, modelDict , checkKnown=False, composersDict=None,composersList=None, error_csv_writer = None):
    
    #Detect language - used to select correct model
    try: lang = detect(stringToParse) 
    except: 
        # print("failed to detect language of query " + stringToParse + " continuing with en")
        #parse as english?
        lang = 'en'

    #if we have the language - try get the people entities
    if modelDict.get(lang):

        #remove special chars
        stringToParse = ''.join(e for e in stringToParse if e.isalnum() or e==" " or e=="-")

        #parse string with given model
        doc = modelDict.get(lang)(stringToParse)
        properNouns = [ent.text for ent in doc.ents if ent.label_ == 'PERSON' ]

    #if we dont have language - we cant recognize the proper nouns
    else: 
        # print("language model not available for query " + stringToParse.replace('\n', " ") + " in lang " + lang)
        error_csv_writer.writerow([ID,lang, stringToParse.replace('\n', " ") ])

        return None

    if properNouns: return [x for x in properNouns if x]
    else: return None


def basic_clean(composer: str, debug: bool = False, initials: bool = True, strict: bool = False) -> str:
        #normalize
        composer = composer.strip(" ").strip("\n")

        #remove multiple composers?
        composer = composer.split("\n")[0].split(",")[0]

        #we dont want to remove other languages
        composer= ''.join(e for e in composer if e.isalnum() or e==" " or e=="," or e=="-" or e=="." or e=="\\" or e=="//" or not e.isascii())
        composer = str.title(str.lower(composer))

        #Insert space after all .
        composer = ". ".join(composer.split('.'))

        #remove any entries with arranger at index 0
        composerToList = composer.split(" ")
        if disqualifyingWords(composerToList):
            if debug: return 'DQ'; 
            else : return None
        
        #Check for common composers
        commonCheck = commonComposers([x.lower() for x in composerToList])
        if not (commonCheck == None): return commonCheck 

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

        composer = charStrip(" ',.- ", composer)
    
        #remove double spaces and symbol only substrings "-."
        composer = " ".join([x for x in composer.split(' ') if x and symbolCheck(x)])

        #remove longer than 5 words (allows for titles like, 'the x of the y') and replace with first 2 words
        if len(composer.split(" "))>5:   
            composer= " ".join(composer.split(" ")[:2])         
            if debug: return '>5'; 

        if len(composer) >1 and initials:
            composer = composer.split(' ')
            composer = " ".join([x[0].upper()+"." if i < (len(composer)-1) else x for i,x in enumerate(composer) ])

        #length check
        if len(composer) < 4 :
            if debug: return '<4'; 
            else : return None
        
        #composer must have some non-symbols
        if not symbolCheck(composer): return None

        #strict = no single name composers 
        # (will remove any uncommon single named composers (e.g. John) (i.e. those that arent adressed in commonComposers))
        if strict: 
            if len(composer.split(' ')) == 1: return None

        if not composer == '': return composer; 
        else: return None


def symbolCheck(composer):
    composer = ''.join(x for x in composer if x!='.' and x!=',' and x!='-' and x!=' ')
    if len(composer) > 0: return True 
    else: return False

def charStrip(chars,word):
    while not word==None:
        for char in chars:
            word = word.strip(char)
        break
    return word

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
            if 'unbekannt' in word: return True
            if 'reelkey' in word: return True
            if 'santa' in word and index ==0: return True
            if 'hornpipekey' in word: return True
            if 'strathspeykey' in word: return True
            if 'polkakey' in word: return True
    return False

#if any bad words then remove them
def badWord(word):
    #normalize
    word=str.lower(word)
    word= ''.join(e for e in word if e.isalnum())

    if len(word) > 20: return True

    #remove numbers
    if word.isnumeric(): return True

    #remove any common words
    bad_words = ['-', '-.', 'ago', 'allegro', 'alto', 'american', 'and', 'anon', 'anonymous', 'anthem', 'april', 'ar', 'ararranger', 'archived', 'aritst', 'arr', 'arranged', 'arrangement', 'arrg', 'august', 'australia', 'author', 'baritone', 'bass', 'battle', 'beat', 'bei', 'belgium', 'berlin', 'blues', 'by', 'capella', 'carol', 'castle', 'cdiscography', 'cello', 'chambers', 'choral', 'christmas', 'city', 'ckey', 'clarinet', 'cnote', 'comp', 'composed', 'composer', 'composition', 'compositor', 'created', 'crhythm', 'csource', 'ctranscription', 'current', 'dance', 'day', 'designed', 'deutschland', 'ding', 'dkey', 'dong', 'dream', 'drhythm', 'duet', 'dutch', 'early', 'edit', 'edited', 'eight', 'eighth', 'england', 'europa', 'february', 'fifth', 'first', 'five', 'fkey', 'folk', 'four', 'fourth', 'french', 'fribourg', 'friday', 'ft', 'game', 'genre', 'germany', 'gkey', 'gsource', 'harmony', 'hornpipe', 'httpwwwmusicavivacom', 'httpwwwmusicavivacommeter', 'hymn', 'in', 'instrumental', 'into', 'intro', 'irish', 'january', 'jesus', 'jig', 'jingle', 'joyful', 'july', 'june', 'jungle', 'key', 'known', 'language', 'late', 'length', 'length-14', 'length-18', 'live', 'london', 'lyrics', 'main', 'march', 'may', 'me', 'medley', 'mel', 'melody', 'merrily', 'merry', 'meter', 'midi', 'minor', 'monday', 'moon', 'morning', 'musescore', 'music', 'musical', 'musicxml', 'musik', 'musique', 'música', 'new', 'night', 'nine', 'ninth', 'no', 'november', 'october', 'one', 'original', 'perform', 'performed', 'pianist', 'piano', 'piece', 'pieces', 'played', 'present', 'quartet', 'races', 'rhythm', 'sacredhymn', 'saturday', 'sax', 'saxophone', 'scales', 'score', 'second', 'september', 'seven', 'seventh', 'sharp', 'silent', 'six', 'sixth', 'solo', 'song', 'soundtrack', 'string', 'sunday', 'ten', 'tenor', 'tenth', 'text', 'theme', 'third', 'three', 'thursday', 'time', 'tinwhistle', 'title', 'trad', 'tradicionel', 'traditional', 'traditionell', 'trans', 'transcribed', 'transcription', 'trio', 'trombone', 'tuba', 'tuesday', 'two', 'undertale', 'unknown', 'version', 'waltz', 'warmup', 'wednesday', 'winter', 'wip', 'word', 'words', 'write', 'written', 'wrote', 'year', 'years']
    if word in bad_words: return True
    
    return False

#check for common composers
def commonComposers(names):
    if 'mozart' in names: return 'W. A. Mozart'
    if 'beethoven'in names: return 'L. V. Beethoven'
    if 'yohei' in names: return 'Y. Kato  加藤 洋平'
    if  'bach' in names: return 'J. S. Bach'
    if 'debussy' in names: return 'C. Debussy'
    return None

def setNameInitials(words):
    return [x[0].upper()+"." if i < len(words)-1 else x for i,x in enumerate(words) ]



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
