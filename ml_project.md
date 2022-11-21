# Musicology Lab
Johannes ??? & Zeng Ren

Big project: 1.6 bn scores (what score ?)

Musescore: Opensource score editor  
score=partition

https://github.com/Xmader/musescore-dataset

.mscx: score format  = +- XML
.mscz: zipped  

- Parsing XML: Done already
- Parsing other files: TODO => What format to use afterwards ?

Data: notes, piano/..., crescendo, secondary information (dots/...)  
Metadata: Instruments names 

Advanced parser implemented already, extracting notes/rests/events/...

Main features: notes, position, duration,...

MSID: Unique ID, used to get additional data on website ?

OpenScore project: rely on themfor metadata ?

Metadata: very messy

Name: useful info, but uncontrolled  
Composer name: only last name


Extract info from a text: NLP ?
- Find named entities
- Multilingual

Find composer: using wiki or sth

Recognize composer ?

higher level data: labels


Project idea:
- Use pre-made lib to extract names from libs
- Classify composers from scores: 
  - transform scores ?
  - extract some features ?
  - ...




Score transformation:
- "piano roll": 1-hot encoding
- ...

Use ms3 (python lib)

Huge dataset:
- create subfolders
- chunks ?
- parallel parsing (how many cores,... ?)

List corrupt files

Parallel framework: RAY (learn ~ one-day ?), else multi-processing lib from python

GitHub repo to share with them  
Discussion feature ?

Meetings on monday
Next monday: Extract composers from all 
- Setup everything:
  - Create GitHub
  - Send moodle link to google forms
  - Ask teacher to get access to a machine ?
  - Download dataset
  - Start parsing

https://github.com/Xmader/musescore-dataset