import spacy
from langdetect import detect

#Language Settings
#All lang models require install on target system with python -m spacy download language_core_model_name
#SMALLMODEL uses a smaller spacy model, if false uses transformer or large model if available
MULTIPLELANGUAGES = True
ALTLANGS = {'de':["de_core_news_sm","de_dep_news_trf"], 'ko':["ko_core_news_sm","ko_core_news_lg"],'en':["en_core_web_sm","en_core_web_trf"],'ja':["ja_core_news_sm","ja_core_news_trf"],'ru':["ru_core_news_sm","ru_core_news_lg"],'it':["it_core_news_sm","it_core_news_lg"], 'es':["es_core_news_sm", "es_dep_new_trf"] }
SMALLMODEL = True

'''Composer label cleaning and Named Entity Recognition functions for retrieving composers from associated metadata'''

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


#Used for parsing B grade metadata fields
def namedEntityRecognition(ID,stringToParse, modelDict , checkKnown=False, composersDict=None,composersList=None, error_csv_writer = None):
    
    #Detect language - used to select correct model
    try: lang = detect(stringToParse) 
    except: 
        # print("failed to detect language of query " + stringToParse + " continuing with en")
        #parse as english
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

        #we dont want to remove other languages (Ascii)
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

