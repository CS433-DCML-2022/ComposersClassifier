Label processing pipeline

Relevant files: tally.py (metadata reduction), ray_NER.py (additional functions for label cleaning), parseMetadata.py (script for producing final labels)

Current label processing pipeline involves:
- Producing set of clean labels from metadata 'composer' fields
- Optional secondary label acquisition from alternative text fields

1) Initial collection of all relevant metadata fields from each json File. This is performed as part of tally.py

The specific 'composer' fields within the JSON are:

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

Tally.py writes all fields for each ID to a metadata.csv for processing. (e.g. ID,[composerTextList],[titleTextList], [DescriptionTextList])

2) A-grade labels

ParseMetadata.py will read the list of composers for each ID in metadata.csv. As composer fields are input by users, they required cleaning. For each composer, text processing is used to clean the string in the following process:

    a) Whitespace and newlines are stripped from the outside of the string

    b) String is split first by any newline character, taking the first substring (this accounts for the case of multiple composers listed with newlines). 
    
    Secondly by commas (this accounts for the case of multiple composers listed with commas) also taking the first substring of the split. 

    This removes any additional composers, retaining only the first mentioned composer.

    c) Non alphanumeric characters are removed except (" ",",","-",".","\","/") (space,comma,dash,dot,fwdslash,backslash). Non-ascii characters are retained.

    d) String format is modified to follow 'title' convention. i.e. each separate word is capitalized

    e) If any '.' period characers exist in the string, they will be replaced by '. '. This is to consolidate composers of the format (A.B. Composer, A.B.Composer and A. B. Composer). Any double spaces introduced (e.g. '. ' -> '.  ') are removed.

    f) String is split with space delimiter and resulting list is passed to a function to check the presence of disqualifying words. Presence of disqualifying words at specific indices (e.g. 'Arr' at index 0) was determined to be a disqualifying condition and the composer will be removed. 
    
    For some disqualifying substrings, if they are located at an alternative index we assume it is most likely after a composer (e.g. A. Composer Transcribed by A. Transcriber) and therefore they are retained. Words include [arr, transcription, transcripcion, trans, trad, unbekannt, reelkey, santa.. etc]

    g) A check is performed for distinct known composer substrings. This is used to reduce variance in labels for common, easily identifiable composers. (e.g. Mozart, Beethoven, Bach) If a known substring is found, the cleaning process terminates and the composers name is returned.

    h) Space delimited substring list is trimmed to the first index containing a first character than is a number. (e.g. ['Johann', 'Sebastian', 'Bach', '17th' 'Century'] -> ['Johann', 'Sebastian', 'Bach'])

    i) Bad words are removed from the string list through filtering the space delimited substrings in the following process:

        i) String is set to lowercase and all non-alpha numeric components are removed for the following checks:

        ii) Length of individual word is checked, if greater than 20 characters it is deleted as a junk entry. 

        iii) If the substring consists of only numbers, it is deemed bad and removed (this is to account for the case of dates). 

        iv) Comparison of string with a list of bad words. Bad words list was iteratively constructed from manual inspection of processing results. If the string is in the list of bad words, we remove it.


    j) String list is joined again with space delimiters

    k) Composer string is .stripped of all " ',.- " characters that may remain after removal of bad words and numbers.

    l) Any substrings containing only " ',.- " characters are removed

    m) Composer strings > length of 5 words are trimmed to the first two words. (This allows for titles such as 'The x of the y')

    n) Cleaned composer string is reduced to an initial-ised form. Each non-surname word is initialized (E.g. Johann Sebastian Bach -> J. S. Bach) This reduces variation in labels, better pooling together compositions from the same composer.

    o) If the length of the joined composer string is strictly less than 4 characters it is removed. 

    p) Final check that composer string contains some non-symbol characters

    q) Optional: If strict setting is selected, only composers with a minimum of 2 names are retained. This increases quality of composers derived from alternative text fields.

List of composers is written in semicolon separated form, along with it's relevant ID, to the specified slim_metadata.csv directory. E.g. (5925434,K. Totaka)


3) B-Grade Labels

Additional composers may be discovered by searching alternative user-provided metadata text fields for composer information. The most reliable seems to be the Title field, however description may also contain relevant info. This additional step allows for a larger (though possibly less reliable) set of labeled compositions for training the model.

    a) Alternative non-composer text fields (title, description) are gathered from metadata.csv

    b) String language is identified with langdetect's detect() function. (Note: this is not very accurate, especially on short strings)

    c) Spacy Language model (corresponding to detected language) is loaded if available, otherwise defaults to english language model

    d) String is filtered for 'entities' with Spacy, entities are filtered to those identified as 'People'.

    e) Identified entities are cleaned in the same procedure specified above, though strict filtering for entities with >=2 word names is recommended.

List of composers is written in semicolon separated form, along with it's relevant ID, to the specified slim_metadata.csv directory. E.g. (5925434,K. Totaka)

Unless specified, only A-grade labels will be obtained by parseMetadata.py. Using additional fields hierarchically is optional. This will first attempt to use composer fields, followed by title and then finally description fields to find a valid composer. 