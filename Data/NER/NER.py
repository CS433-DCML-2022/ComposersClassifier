import spacy

COMPOSERDIR =  "composer_labels.txt"

'''Draft Named Entity Recognition for retrieving possible composers from associated metadata'''

def loadComposers(file):
    composers = list()
    with open(file,'r') as comps:
        for line in comps.readlines():
            composers.append(line.split(',')[1].rstrip("\n"))
    return composers

def namedEntityRecognition(stringToParse, composerFile, NLPmodel, knownComposersOnly = True,):
    #parse string with given model
    doc = NLPmodel(stringToParse)
    properNouns = [ent.text for ent in doc.ents ]
    #composerCheck
    if knownComposersOnly:
        composers = loadComposers(composerFile)
        # print(composers)
        # print(properNouns)
        properNouns = [[composer for composer in composers if prop in composer] for prop in properNouns]
    return properNouns


if __name__ == "__main__":
    #test string
    dummyString = "A classical piece from Chopin that I have modified, inspired by my friend Jose. Still a work in progress but its pretty cool"
    #english only first
    nlpEnglish = spacy.load("en_core_web_sm")
    entities = namedEntityRecognition(dummyString, COMPOSERDIR, nlpEnglish, True)
    #sort by word distance or artist popularity?
    print(entities)

