import spacy
import os
import json
from functools import lru_cache
from langdetect import detect
import csv
import argparse


#Language Settings
#All lang models require install on target system with python -m spacy download language_core_model_name
#SMALLMODEL uses a smaller spacy model, if false uses transformer or large model if available
MULTIPLELANGUAGES = True
ALTLANGS = {'de':["de_core_news_sm","de_dep_news_trf"], 'ko':["ko_core_news_sm","ko_core_news_lg"],'en':["en_core_web_sm","en_core_web_trf"],'ja':["ja_core_news_sm","ja_core_news_trf"],'ru':["ru_core_news_sm","ru_core_news_lg"],'it':["it_core_news_sm","it_core_news_lg"], 'es':["es_core_news_sm", "es_dep_new_trf"] }
SMALLMODEL = False

#Scrape and parse fields settings
CONVERT_COMPOSER_TO_STEM = False
AGRADELABELSONLY = True
KNOWNCOMPOSERSONLY = False
NORMALIZE_NAMES = False
FIELDS = ["description", "title"] #fix this to specify which metadata dictionary e.g. ms3 or musescore
# SAVELANG = True

DEBUG = True


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


#Lev dist calculation
#only used for picking most similar of all composers that contain the extracted pronoun (not comparison with all)
def lev_dist(a, b):

    @lru_cache(None) 
    def min_dist(s1, s2):
        if s1 == len(a) or s2 == len(b):
            return len(a) - s1 + len(b) - s2
        # no change required
        if a[s1] == b[s2]:
            return min_dist(s1 + 1, s2 + 1)
        return 1 + min(
            min_dist(s1, s2 + 1),      # insert character
            min_dist(s1 + 1, s2),      # delete character
            min_dist(s1 + 1, s2 + 1),  # replace character
        )
    return min_dist(0, 0)


#Attempts to get the 'stem' version of the composer name 
#Stem version is the default name for a given ID (first loaded from composer file)
#used to reduce variation in labels e.g. ideally both of the below will have the same composer string
#http://www.wikidata.org/entity/Q30449,Аўрыл Лавін
#http://www.wikidata.org/entity/Q30449,Avril Lavigne
# def getStemOfComposerName(name,dict):
#     possibleNames = dict[name[1]]
#     #to implement - stem flag for first instance of ID added to composer dictionary
#     possibleEnglishNames = [name for name in possibleNames if name[1] == 1 ] 
#     if len(possibleEnglishNames) == 0: return [name[0]]
#     return possibleEnglishNames

#used primarily for parsing B grade metadata fields
def namedEntityRecognition(stringToParse, composersDict,composersList, NLPmodel, lang):
    
    #remove special chars
    stringToParse = ''.join(e for e in stringToParse if e.isalnum() or e==" ")

    #parse string with given model
    doc = NLPmodel(stringToParse)
    properNouns = [ent.text for ent in doc.ents ]

    #composerCheck
    if KNOWNCOMPOSERSONLY:
        possibleComposers = knownComposerCheck(composersList,properNouns)
    
    if DEBUG: print(possibleComposers)
    #take best / most similar candidate for each proper noun
    #Note: if not KNOWN composers only, then all proper nouns will be selected (due to similarity/distance measure used)
    candidates = list()
    for prop in properNouns:
        candidates.append(sorted(possibleComposers, key= lambda x: lev_dist(prop,x[0]))[0])
    
    #convert to stem version of composer to reduce variation if possible
    # if CONVERT_COMPOSER_TO_STEM:
    #     if lang != 'en':
    #         candidates = [ [enName for enName in getStemOfComposerName(candidate,composersDict)] for candidate in candidates]
    # else:
    #     candidates = [name[0] for name in candidates]
    
    return [name[0] for name in candidates]

#normalize composer name
def normalizeName(name):
    name= ''.join(e for e in name if e.isalnum() or e==" ")
    name = str.capitalize(str.lower(name))
    if ',' in name:
        l,f = name.split(',')
        return f+l

# #check if composer name is of correct format, if so assume correct unless knowncomposersonly=True
# #  write to csv and json
# def checkName(composer,ID,jsonObj,f,csv_file_dir='composer_id.csv'):
#     #strip any newlines or spaces
#     composer = composer.strip("\n").strip(" ")
#     #see if we can get a clean split into two
#     #alternatively if we get 3 substrings maybe we can handle this somehow (with proper noun parse to remove extra terms?)
#     if len(composer.split(" "))==2 or len(composer.split(","))==2:
#         composer = normalizeName(composer)
#         # check for stem version of composer if exists? 
#         # if KNOWNCOMPOSERSONLY:
#         with open (f, 'w', newline='') as jsonFile:
#             jsonObj["parsed_composer"] = composer
#             json.dump(jsonObj,jsonFile)
#         # with open(csv_file_dir,'a') as csvFile:
#         #     writer = csv.writer(csvFile)
#         #     writer.writerow(str(ID) + "," + composer)
#         return True
#     else: return False

#determine if composer is actually arranger
def disqualifyingWords(wordList):
    for index,word in enumerate(wordList):
        word=str.lower(word)
        word = ''.join(e for e in word if e.isalnum()) 
        
        if 'arr' in word and index == 0: return True
        if 'transcription' in word and index == 0: return True

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
    bad_words = ["ft","composer", "composed", "by", "comp", "words", "word", "and", "music", "piece", "pieces", "arr", "ar" "arranger", "arranged", "arrangement", "ar", "arrg", "transcription", "trans", "choral", "wrote", "version", "in", "music", "melody", "harmony", "created", "mel", "musical", "soundtrack", "game", "score", "version", "unknown", "musique", "original", "edit", "edited", "instrumental"]
    if word in bad_words: return True

    return False


def basicClean(composer):
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

    #remove longer than 3 words?
    composer = " ".join(composerStringList)

    if len(composer.split(" "))>4: return "unknown"

    #length check
    if len(composer) < 4 :return "unknown"
    # print(composer)
    return composer.strip(" ").strip("-")

def writeFirstComposer(composer,jsonObj,f, csv_file_dir,ID):
    #very basic cleaning of name
    # if DEBUG: print(composer)
    composer = basicClean(composer)
    jsonObj['first_composer'] = composer

    with open (f, 'w', newline='') as jsonFile:
        json.dump(jsonObj,jsonFile)
    with open(csv_file_dir,'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([str(ID), composer])

#prioritized check of metadata composer fields
#if cleanName, returns true if correctly formatted name is found in composer fields, optional check with wiki
#Otherwise saves any existing 'reliable' composer field in first_composer 
def getComposerFromMetadata(jsonObj,ID,f,csv_file_dir):
    
    #first check ms3_metadata? 2 possible fields
    ms3Dict = jsonObj.get( "ms3_metadata")
    if ms3Dict:
        composerField1 = ms3Dict.get("composer")
        if composerField1: 
            # if NORMALIZE_NAMES:
            #     if checkName(composerField1,ID,jsonObj,f): return True
            # else:
                writeFirstComposer(composerField1,jsonObj,f,csv_file_dir,ID)
                return True
                
        composerField2 = ms3Dict.get("composer_text")
        if composerField2: 
            # if NORMALIZE_NAMES:
            #     if checkName(composerField2,ID,jsonObj,f): return True
            # else:
                writeFirstComposer(composerField2,jsonObj,f,csv_file_dir,ID)
                return True

    #then check museScoreDict
    museScoreDict = jsonObj.get( "musescore_metadata")
    if museScoreDict:
        museScoreMDDict = museScoreDict.get( "metadata")
        composerField3 = museScoreMDDict.get("composer")
        if composerField3:
            # if NORMALIZE_NAMES:
            #     if checkName(composerField3,ID,jsonObj,f): return True
            # else:
                writeFirstComposer(composerField3,jsonObj,f,csv_file_dir,ID) 
                return True

        museScoreTextDataDict = museScoreMDDict.get("textFramesData")
        if museScoreTextDataDict:
            textDataComposerList = museScoreTextDataDict.get("composers")
            if textDataComposerList:
                for textDataComposer in textDataComposerList:
                    # if NORMALIZE_NAMES:
                    #     if checkName(textDataComposer,ID,jsonObj,f): return True
                    # else:
                        writeFirstComposer(textDataComposer,jsonObj,f,csv_file_dir,ID)
                        return True  

        return False


def knownComposerCheck(properNouns,composersList):
    #only takes composers if the proper noun taken from metadata is 'in' the composer name -> this will not work for small spelling errors
    #does not account for spelling errors***
    possibleComposers = [[composer for composer in composersList if prop in composer[0]] for prop in properNouns]
    #remove empty and flatten
    possibleComposers = [item for sublist in possibleComposers for item in sublist if item]
    return possibleComposers


def BgradeParse(jsonObj, modelDict, composersList,composersDict,f,csv_file_dir):
    #Query each specified field of the json for text
    currQueryText = []
    for field in FIELDS:
        #check if field contains .Arr? - to add
        if (jsonObj.get(field)): currQueryText.append(jsonObj.get(field))

    if DEBUG: print(currQueryText)
    currQueryText = str(" ".join(currQueryText))

    #any text to query with?
    if len(currQueryText) > 0 :

        #Detect language - maybe useful feature / can be used to select correct model
        try: lang = detect(currQueryText) 
        except: 
            if DEBUG: print("failed to detect language of query " + currQueryText)
            #parse as english?
            lang = 'en'

        if DEBUG: print(lang)
        # if SAVELANG: jsonObj["Language"] = lang

        #if we have the language - try get the proper nouns
        if modelDict.get(lang):
            entities = namedEntityRecognition(currQueryText, composersDict,composersList, modelDict.get(lang), lang)
        
        #if we dont have language - we cant recognize the proper nouns
        else: 
            # if SAVELANG: json.dump(jsonObj,jsonFile)
            if DEBUG: print("language model not available for query " + currQueryText + " in lang " + lang)
            
            return False
                    #Write composer to entities
        #what to do if multiple? select first only
        jsonObj["b_grade_composer"] = str(entities[0][0])
        if DEBUG: print(entities[0][0])
        with open (f, 'w', newline='') as jsonFile:
            json.dump(jsonObj,jsonFile)
        return True

def main(args):

    composer_dir = os.path.abspath(args.composer_file)
    csv_file_dir = os.path.abspath(args.csv_file)
    json_dir = os.path.abspath(args.json_folder)

    #init all language models if using NER (parsing B grade or checking composers with wiki data)
    if KNOWNCOMPOSERSONLY or not AGRADELABELSONLY:
        modelDict = initModelDict()
        composersDict,composersList = loadComposers(composer_dir)

    for jsonFileName in os.listdir(json_dir):
        ID = jsonFileName.split(".")[0]
        # if DEBUG: print(jsonFileName)
        f = os.path.join(json_dir,jsonFileName)

        with open(f,'r',newline='') as currJson:
            data = currJson.read()
            jsonObj = json.loads(data)

            #try get composer from reliable fields
            if getComposerFromMetadata(jsonObj,ID,f,csv_file_dir): continue

            #if not checking B grade fields then write to file
            if AGRADELABELSONLY: 
                jsonObj["first_composer"] = "unknown"
                with open (f, 'w', newline='') as jsonFile:
                    json.dump(jsonObj,jsonFile)
                with open(csv_file_dir,'a') as csvFile:
                        writer = csv.writer(csvFile)
                        writer.writerow([str(ID),  "unknown"])
                continue
                
            #Parse other fields - to be implemented
            if BgradeParse(jsonObj, modelDict, composersList,composersDict,f,csv_file_dir): continue
            else:
                #no possible label found in primary or secondary sources
                jsonObj["first_composer"] = "unknown"
                jsonObj["b_grade_composer"] = "unknown"
                with open (f, 'w', newline='') as jsonFile:
                    json.dump(jsonObj,jsonFile)
                


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Get composers from metadata.""")
    parser.add_argument('-j', '--json_folder', default="../data/metadata")
    parser.add_argument('-csv', '--csv_file', default="../data/csv/labels_v2.csv")
    parser.add_argument('-c', '--composer_file', default="composer_labels.txt")

    args = parser.parse_args()
    main(args)


