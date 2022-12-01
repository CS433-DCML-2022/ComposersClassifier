import spacy
import os
import json
from functools import lru_cache


COMPOSERDIR =  "composer_labels.txt"
#Fields to query for composer data - "title"?, 
FIELDS = ["description", "title"]
JSONDIR = "/Users/jamiemickaill/Desktop/ML_PROJECT_2/NERbranch/ComposersClassifier/Data/metadata"
SKIPIFCOMPOSEREXISTS = True
KNOWNCOMPOSERSONLY = True
DEBUG = False

'''Draft Named Entity Recognition for retrieving possible composers from associated metadata'''

def loadComposers(file):
    composers = list()
    with open(file,'r') as comps:
        for line in comps.readlines():
            composers.append(line.split(',')[1].rstrip("\n"))
    return composers


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


def namedEntityRecognition(stringToParse, composerFile, NLPmodel):
    
    #remove special chars
    stringToParse = ''.join(e for e in stringToParse if e.isalnum() or e==" ")

    #parse string with given model
    doc = NLPmodel(stringToParse)
    properNouns = [ent.text for ent in doc.ents ]

    #composerCheck
    composers = loadComposers(composerFile)
    possibleComposers = [[composer for composer in composers if prop in composer] for prop in properNouns]
    #this will include all proper nouns from text 
    if not KNOWNCOMPOSERSONLY:
        possibleComposers += properNouns

    if DEBUG: print(possibleComposers)
    #take best / most similar candidate for each proper noun
    #Note: if not KNOWN composers only, then all proper nouns will be selected (due to similarity/distance measure used)
    candidates = []
    for prop in properNouns:
        candidates.append(sorted(possibleComposers, key= lambda x: lev_dist(prop,x))[0])

    return candidates



if __name__ == "__main__":

    #init model/s
    nlpEnglish = spacy.load("en_core_web_sm")

    #Iterate over all JSON in Dir
    for jsonFile in os.listdir(JSONDIR):
        if DEBUG: print(jsonFile)
        f = os.path.join(JSONDIR,jsonFile)
        with open(f,'r',newline='') as currJson:
            data = currJson.read()
            jsonObj = json.loads(data)

            #skip if composer exists
            if SKIPIFCOMPOSEREXISTS:
                composer = jsonObj.get("Composer")
                if composer != [] and composer != "" and composer != None:
                    print(jsonFile + ": Composer currently exists = " + str(composer))
                    continue

            #just description? set fields
            currQueryText = []
            for field in FIELDS:
                if (jsonObj.get(field)):
                    #check if field contains .Arr?
                    currQueryText.append(jsonObj.get(field))
    
            if DEBUG: print(currQueryText)

            #any text to query with?
            if currQueryText != []:
                entities = namedEntityRecognition(str(" ".join(currQueryText)), COMPOSERDIR, nlpEnglish)
            else:
                continue

            #else try another dictionary/language to scrape entities
            if entities == None:
                #for language in languages...
                continue

            #Write composer to entities
            #what to do if multiple? select first only
            jsonObj["Composer"] = str(entities[0])
            if DEBUG: print(entities[0])

        with open (f, 'w', newline='') as jsonFile:
            json.dump(jsonObj,jsonFile)



