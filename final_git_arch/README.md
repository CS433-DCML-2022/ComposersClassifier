//TODO: merge with prev readme
## Contents
//TODO update
```
Project
|  classifying_script: simple script using pre-trained model, classifying a given notes.tsv file (or folder with argument --folder)
|  json_processing_notebook: Python notebook going through all steps of label extraction from a metadata.json file
|  learning_notebook: Python notebook running training on either balanced or unbalanced training set, and testing on test_set
|
└── data/
|   |  composers_occurences.tsv: Observed occurences of top 10 composers in the full dataset (15e6 samples)
|   └── samples/
|       |  sample files for explaining and intermediary tests purposes
|       └─
|   └── test_set/
|       |  notes.zip
|       |  composers_per_ID.tsv: summary of composers (if known) for given notes
|       └─     
|   └── tr_set_balanced/: dataset to train model, exactly 150 random scores per composer, top 10 composers
|       |  notes.zip: notes
|       |  composers_per_ID.tsv: summary of composers for given notes
|       └─         
|   └── tr_set_unbalanced/: dataset to train model, exactly 1 500 random scores, sampled with natural observed distribution
|       |  ...
|       └─    
└── trained_models/
|   |  binary save of trained models
|   └─
└─
  ```

  ## How to run
  Every step has a corresponding subfolder, in which you can run the scripts according to the $STEP.md explanatory file.
  ## Conversion
  ```
  cd conversion/
  python3 convert.py
  ```
  ## Preprocessing
  ```
  cd preprocessing/
  python3 tally.py
  ```
  ## Label Processing
  ```
  cd conversion/
  python3 parseMetadata.py
  ```
  ## ...
  ## Results analysis
