import argparse
import torch
import os
import pandas as pd
import tqdm
import numpy as np
import yaml
from torch.utils.data import DataLoader

from dataset import NotesDataset


def get_random_perf(num_classes, csv_dir, test_ids_tsv, zipped, NOTES_ZIP_OR_DIR, num_workers):
    test_ids = np.load(test_ids_tsv)
    composers_ID_filepath = os.path.join(csv_dir, 'id_composers.tsv')
    composers_filepath = os.path.join(csv_dir, 'composers.tsv')
    test_set = NotesDataset(composers_ID_filepath, composers_filepath, num_classes, 1/32, -1, NOTES_ZIP_OR_DIR, test_ids, zipped=zipped, logger=None)
    test_loader = DataLoader(test_set, 1, num_workers=num_workers, shuffle=True)
    composers = pd.read_csv(composers_filepath, sep='\t')
    id_composers = pd.read_csv(composers_ID_filepath, sep='\t')
    props = id_composers['composer'].value_counts() / id_composers['composer'].count()

    correct = 0
    for i, (_, target) in enumerate(tqdm.tqdm(test_loader)):
        j = np.random.choice(num_classes, p=props)
        composer = props[props==props.iloc[j]].index.values[0]
        pred = composers.loc[composers['composer']==composer].index.values[0]        
        correct += pred == target.argmax(dim=1, keepdim=True).item()

        if i>0 and i%100 == 0:
            print(
                "RANDOM - Test set: Accuracy: {}/{} ({:.3f}%)".format(
                    correct,
                    i,
                    100.0 * correct / i,
                )
            )

    print(
        "RANDOM - Test set: Accuracy: {}/{} ({:.3f}%)".format(
            correct,
            len(test_loader.dataset),
            100.0 * correct / len(test_loader.dataset),
        )
    )

    return correct / len(test_loader.dataset)


def main(args):
    with open(args.config, 'r') as stream:
        config = yaml.safe_load(stream)
    np.random.seed(config['random_seed'])
    torch.manual_seed(config['random_seed'])
    get_random_perf(config['num_classes'], config['csv_dir'], os.path.join(config['ids_folder'], 'test_ids.npy'), config['zipped'], config['notes_zip_or_dir'], config['num_workers'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Test Random Predictor.""")
    parser.add_argument('--config', required=True, help='path to yaml config')
    
    args = parser.parse_args()
    main(args)
