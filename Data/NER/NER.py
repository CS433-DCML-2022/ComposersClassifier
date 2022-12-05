import spacy
import os
import json
from functools import lru_cache
from langdetect import detect

COMPOSERDIR =  "composer_labels.txt"
#Fields to query for composer data - "title"?, 
FIELDS = ["description", "title"]
JSONDIR = "/Users/jamiemickaill/Desktop/ML_PROJECT_2/NERbranch/ComposersClassifier/Data/metadata"
SKIPIFCOMPOSEREXISTS = True
KNOWNCOMPOSERSONLY = True
SAVELANG = True
MULTIPLELANGUAGES = True
#All lang models require install on target system with python -m spacy download language_core_model_name
ALTLANGS = {'de':["de_core_news_sm","de_dep_news_trf"], 'ko':["ko_core_news_sm","ko_core_news_lg"],'en':["en_core_web_sm","en_core_web_trf"],'ja':["ja_core_news_sm","ja_core_news_trf"],'ru':["ru_core_news_sm","ru_core_news_lg"],'it':["it_core_news_sm","it_core_news_lg"], 'es':["es_core_news_sm", "es_dep_new_trf"] }
#if true will retrieve _trf (transformer based) language models instead of _sm
# ~438mb file vs 12mb for en
ACCURACYOVERSPEED = False
DEBUG = True
#To add - if composer has an english name use it to reduce variation
CONVERTALLTOEN = False

'''Draft Named Entity Recognition for retrieving possible composers from associated metadata'''

#make composer list (compser,ID) and dict with ID -> [names]
def loadComposers(file):
    composersDict = dict()
    composersList = list()
    with open(file,'r') as comps:
        for line in comps.readlines():
            splitLine = line.split(',')
            ID = splitLine[0].split('/')[-1]
            composer = splitLine[1].strip('\n')
            if composersDict.get(ID):composersDict[ID] = composersDict[ID].append(composer)
            else: composersDict[ID] = list(composer)
            composersList.append((composer,ID))
    return composersDict,composersList

def initModelDict():
    modelDict = dict()
    #init model/s
    if MULTIPLELANGUAGES:
        for lang in ALTLANGS.keys():
            if ACCURACYOVERSPEED:
                modelDict[lang]=spacy.load(ALTLANGS[lang][1])
            else: modelDict[lang]=spacy.load(ALTLANGS[lang][0])
    else:
        if ACCURACYOVERSPEED: modelDict['en'] = spacy.load("en_core_web_rtf") 
        else: modelDict['en'] = spacy.load("en_core_web_sm")
    return modelDict

#Lev dist calculation
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

def getENcomposerName(name,dict):
    possibleNames = dict[name[1]]
    possibleEnglishNames = [name for name in possibleNames if detect(name) == 'en' ] 
    if len(possibleEnglishNames) == 0: return [name[0]]
    return possibleEnglishNames

def namedEntityRecognition(stringToParse, composersDict,composersList, NLPmodel, lang):
    
    #remove special chars
    stringToParse = ''.join(e for e in stringToParse if e.isalnum() or e==" ")

    #parse string with given model
    doc = NLPmodel(stringToParse)
    properNouns = [ent.text for ent in doc.ents ]

    #composerCheck
    possibleComposers = [[composer for composer in composersList if prop in composer[0]] for prop in properNouns]
    
    #remove empty and flatten
    possibleComposers = [item for sublist in possibleComposers for item in sublist if item]

    #this will include all proper nouns from text 
    if not KNOWNCOMPOSERSONLY:
        possibleComposers += properNouns

    if DEBUG: print(possibleComposers)

    #take best / most similar candidate for each proper noun
    #Note: if not KNOWN composers only, then all proper nouns will be selected (due to similarity/distance measure used)
    candidates = list()
    for prop in properNouns:
        candidates.append(sorted(possibleComposers, key= lambda x: lev_dist(prop,x[0]))[0])
    
    #convert to EN
    if lang != 'en':
        candidates = [ [enName for enName in getENcomposerName(candidate,composersDict)] for candidate in candidates]

    return candidates

if __name__ == "__main__":

    #init all language models
    modelDict = initModelDict()
    composersDict,composersList = loadComposers(COMPOSERDIR)

    #Iterate over all JSON in Dir
    for jsonFile in os.listdir(JSONDIR):
        if DEBUG: print(jsonFile)
        f = os.path.join(JSONDIR,jsonFile)

        #read json
        with open(f,'r',newline='') as currJson:
            data = currJson.read()
            jsonObj = json.loads(data)

            #skip if composer exists
            if SKIPIFCOMPOSEREXISTS:
                composer = jsonObj.get("Composer")
                if composer != [] and composer != "" and composer != None:
                    print(jsonFile + ": Composer currently exists = " + str(composer))
                    continue

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
                    continue

                if DEBUG: print(lang)
                if SAVELANG: jsonObj["Language"] = lang

                #if we have the language - try get the proper nouns
                if modelDict.get(lang):
                    entities = namedEntityRecognition(currQueryText, composersDict,composersList, modelDict.get(lang), lang)
                
                #if we dont have language - we cant recognize the proper nouns
                # save new json including language and quit?
                else: 
                    if SAVELANG: json.dump(jsonObj,jsonFile)
                    if DEBUG: print("language model not available for query" + currQueryText + " in lang " + lang)
                    continue
            else:
                continue

            #Write composer to entities
            #what to do if multiple? select first only
            jsonObj["Composer"] = str(entities[0][0])
            if DEBUG: print(entities[0][0])

        with open (f, 'w', newline='') as jsonFile:
            json.dump(jsonObj,jsonFile)



