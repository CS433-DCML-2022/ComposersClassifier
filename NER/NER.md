NER.py: Label processing pipeline

Current label processing pipeline involves:

1) A grade labels: initial collection of a valid 'reliable' composer field from each json object if one exists. 

The specific JSON fields are:
- From the ms3_metadata dictionary:
    - "composer" 
    - "composer_text" 
- from the "musescore_metadata" dictionary:
    - from the inner "metadata" dictionary:
        - "composer"
        - from the inner "textFramesData dictionary:
            - first entry from the list "composers"

If a string is found in any of the fields the search terminates. (Note: Possibly some composer fields are more reliable than others, in this case the order of checking them is important.)

Initial data analysis contained in labelInspect.ipynb was used to determine the best methods to clean composer strings.

The found string is cleaned in the following process

a) Whitespace and newlines are stripped from the outside of the string

b) String is split first by any newline character, and the first substring is taken (this accounts for the case of multiple composers listed with newlines). Secondly by commas (this accounts for the case of multiple composers listed with commas) also taking the first substring of the split. 
This step is primarily responsible for removing any additional composers, so if we wish to keep this information, this should be modified.

c) Any non alphanumeric characters are removed except (" ",",","-",".","\","/") (space,comma,dash,dot,fwdslash,backslash)

d) String format is modified to follow 'title' convention. i.e. each separate word is capitalized

e) String is split with space delimiter and resulting list is passed to a function to check the presence of disqualifying words. Currently this involves  checking for 'arr' or 'transcription' substrings in the word located at the first index of the split string. This is deemed a disqualifying condition and the composer will be set to unknown. If these disqualifying substrings are located at an alternative index we assume it is most likely after a composer.

d) Bad words are removed from the string list through filtering the space delimited substrings in the following process:

    i) String is set to lowercase and all non-alpha numeric components are removed for the following checks:

    ii) Length of individual word is checked, if greater than 40 characters we have currently determined it is likely a junk entry. 

    iii) If the substring consists of only numbers, it is deemed bad and removed (this is to account for the case of dates). 

    iv) Comparison of string with a list of bad words. Bad words were sought from manual inspection of the 1000 json subsample in addition to some relevant related words likely to exist in a larger sample. If the string is in the list, we remove it.

    Bad word list currently includes ["ft","composer", "composed", "by", "comp", "words", "word", "and", "music", "piece", "pieces", "arr", "ar" "arranger", "arranged", "arrangement", "ar", "arrg", "transcription", "trans", "choral", "wrote", "version", "in", "music", "melody", "harmony", "created", "mel", "musical", "soundtrack", "game", "score", "version", "unknown", "musique", "original", "edit", "edited", "instrumental"]  

f) String list is joined again with space delimiters

h) If the length of the joined composer string is strictly less than 4 characters it is removed. 

i) Final strip of whitespace and "-" characters from outside of final composer string

****
Notes for cleaning impovements:
- substrings containing date terms are still currently included, a proposed solution is to trim the string at the first instance of a number. All months could be added to badwords list also, however ordinal numbers (e.g. 1st) may still be present.
****

The cleaned string is written to the relevant json object under the field "first_composer" in the root of the json object. If no valid string is found in the search, "unknown" is set for this field. The ID and it's associated Agrade label are written to a csv file specified by the user via command arguments.

At present, A-grade label processing conlcudes at this step. 

Further data exploration should be conducted to determine whether it is worthwhile attempting to retrieve possible composers from alternative fields and the best method to do so. E.g. Check the number of currently "unknown" composers that have titles containing a composer, descriptions containing a composer, etc. Alternative fields could then be hierarchically scanned based on quality.

Some draft functions for parsing alternative user-specified fields of the jsonObject and extracting composers have been written. This consists of scraping all test from fields, identifying the language, and then the entities present with the corresponding Spacy language model if the language model is present. 

An additional verification step may be performed on the found entities to cross validate them with a list of known composers such as wiki data in composer_text.txt to ensure quality. 

Issues remain such as 
- instances of the same composer written in multiple different languages: this may be resolved during the verification step where a 'default' composer can be selected from the multiple language variants of an identified known composer.
- misspelled composers: a similarity check over all known composers may be too computationally expensive.


