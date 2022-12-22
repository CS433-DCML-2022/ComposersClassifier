## Folder Structure
```
.
├── README.md
├── requirements.txt
├── configs
    ├── config_test_chance.yaml
    ├── config_test_full_unbalanced.yaml
    ├── config_test_max_balanced.yaml
    ├── config_test_small_balanced.yaml
    ├── config_test_small_unbalanced.yaml
    ├── config_train_full_unbalanced.yaml
    ├── config_train_max_balanced.yaml
    ├── config_train_small_balanced.yaml
    ├── config_train_small_unbalanced.yaml

├── trained_models
    ├── full_unbalanced.pt
    ├── max_balanced.pt
    ├── small_balanced.pt
    ├── small_unbalanced.pt

├── checkpoints
    ├── full_unbalanced
        ├── ...
    ├── max_balanced
        ├── ...
    ├── small_balanced
        ├── ...
    ├── small_unbalanced
        ├── ...

├── src
    ├── dataset.py
    ├── generate_dataset.py
    ├── model.py
    ├── plot_training_curves.py
    ├── select_data.py
    ├── test_chance.py
    ├── test.py
    ├── train.py
    ├── utils.py
    
```
## Installation
In order to have the good environnement to run this code you need to :
- Create a virtual environnement (optional)
```
python3 -m venv venv
source venv/bin/activate
```

- Install all the needed dependencies
```
pip install -r requirements.txt
```

## Input data
### Downloading from Drive
To experiment on our datasets, please download them from:
https://drive.google.com/drive/folders/1Fdby1B12gKPfIL31OetuSnTjYF_uLe1_?usp=sharing

Then move and rename the zip files to the locations and names that are described in Project Structure section (data/CONFIG/notes.zip).

### From the previous steps
From the previous steps we have a features.zip folder. One may get a notes folder from this zip folder and a selection of id_composers.tsv using:
```
python3 src/select_data.py -f features.zip -o ../data/myDataset/ -i ../data/myDataset/id_composers.tsv
```
We recommend to zip the notes file for next steps.

## Usage
### Training
```
python3 src/train.py --config configs/config_train_small_unbalanced.yaml
```
Train configs are provided as:
```
configs/config_train_*.yaml
```

### Testing
```
python3 src/test.py --config configs/config_test_small_unbalanced.yaml
```
Test configs are provided as
```
configs/config_test_*.yaml
```

### Testing chance
```
python3 src/test_chance.py --config configs/config_test_chance.yaml
```

### Plotting training curves
```
python3 src/plot_training_curves.py -c checkpoints/small_unbalanced
```

### Generating a proportional dataset
For generating an unbalanced dataset that respects full dataset's proportions, one may use:
```
python3 src/generate_dataset.py -c data/small_unbalanced/composers.tsv -i data/small_unbalanced/id_composers.tsv
```
For more details type:
```
python3 src/generate_dataset.py -h
```

