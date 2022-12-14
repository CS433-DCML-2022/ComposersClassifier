# ComposersClassifier - Guessing the composer of a MuseScore file

Work conducted Jamie MICKAILL, Erwan UMLIL, Nathan PELUSO, in collaboration with the Digital & Cognitive Musicology Lab, EPFL.

## Project Structure
```
├── conversion
│   ├── convert.py
│   └── README.md
├── data
│   ├── full_unbalanced
│   │   └── ...
│   ├── max_balanced
│   │   └── ...
│   ├── preprocessing_toy_example
│   │   └── ...
│   ├── small_balanced
│   │   └── ...
│   └── small_unbalanced
│       └── ...
├── label_processing
│   ├── labelExtract.py
│   ├── labelInspect.ipynb
│   ├── parseMetadata.py
│   ├── README.md
├── learning
│   ├── checkpoints
│   │   ├── full_unbalanced
│   │   ├── max_balanced
│   │   ├── small_balanced
│   │   └── small_unbalanced
│   ├── configs
│   │   └── ...
│   ├── README.md
│   ├── requirements.txt
│   ├── src
│   │   └── ...
│   └── trained_models
│       └── ...
├── preprocessing
│   ├── README.md
│   └── tally.py
├── project2_description.pdf
├── README.md
└── results_analysis
    ├── README.md
    ├── results_analysis.ipynb
    ├── final_heatmap_balanced.png
    └── final_heatmap_unbalanced.png
```


  ## How to run
  Every step has a corresponding subfolder, in which you can run the scripts according to the related README.md explanatory file.
  - Conversion (non-runnable)
  - Preprocessing (non-runnable)
  - Label Processing
  - Training
  - Results analysis

Considered the size of the data set we used, the conversion and preprocessing steps were only achieved on HPC. Code and README are provided but due to version-specific issues of binaries (mscore especially), they are not guaranteed to run locally.
A metadata.csv file is provided on https://drive.google.com/drive/folders/1Fdby1B12gKPfIL31OetuSnTjYF_uLe1_?usp=sharing for label processing analysis.
Data sets are also available to download, to continue at 'Training' step.