# Tasks
- Join mattermost
- Mail for cluster
- 
## Nathan
- Handle pull request
## Erwan
- Look into how to extract composer
- Start looking into how to use scores
## Jamie
- Web scraper + NLP parsing of metadata

# To think about
- How to evaluate ?
- How to explore extracted data & throw out 'empty'/'unusable'

# Data transformation
- Discretisation: what smallest times interval ?
PPCM of all ? Standard one (better to compare pieces) ? Split when note change ?
- 1-hot encoding ?
- pitch-space => convolution (to get translation invariance)
- 2 dim: octave(TPC)-name (existing already) (+time), collapse all instruments ?
- how to 'sum' instruments: sum/normalize/log sum/...

Octaves: can be clipped
Note: + or - 12
Or drop

Duration: fraction (string) or fraction_qb (4*fraction, as float)

# Exploration notebook
- lowest, highest pitch ?
- how many composers/arrangers ?
- how long pieces are ? Number of notes & length in measures
- Number of empty measures ?


