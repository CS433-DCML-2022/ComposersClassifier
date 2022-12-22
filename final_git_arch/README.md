# ComposersClassifier
Guessing the composer of a MuseScore file

## Project Structure
```
Project
|  classifying_script: simple script using pre-trained model, classifying a given notes.tsv file (or folder with argument --folder)
|  json_processing_notebook: Python notebook going through all steps of label extraction from a metadata.json file
|  learning_notebook: Python notebook running training on either balanced or unbalanced training set, and testing on test_set
|
└── data/
|   └── full_unbalanced
|        └── ...
|   └── max_balanced
|        └──  ...
|   └──  small_balanced
|        └──  ...
|   └──  small_unbalanced
|        └──  ...
└── conversion/
|   └── ...
└── label_processing/
|   └── ...
└── preprocessing/
|   └── ...
└── learning/
|   └── ...
└── results_analysis/
|   └── ...
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
