import argparse
import pandas as pd
import numpy as np
import os


def generate_dataset(args):
    composers = pd.read_csv(args.composers_tsv, sep='\t')
    id_composers = pd.read_csv(args.id_composers_tsv, sep='\t')
    counts = id_composers['composer'].value_counts()
    all_ids_train = []
    all_ids_val = []
    all_ids_test = []
    np.random.seed(args.random_seed)
    for composer in composers['composer'].values:
        print(composer)
        ids = id_composers[id_composers['composer']==composer]['ID'].values
        np.random.shuffle(ids)
        nb_train = int(args.prop_train * counts[composer])
        nb_val = int(args.prop_val * counts[composer])
        all_ids_train += ids[:nb_train].tolist()
        all_ids_val += ids[nb_train:nb_train+nb_val].tolist()
        all_ids_test += ids[nb_train+nb_val:].tolist()
    train_ids = np.array(all_ids_train)
    val_ids = np.array(all_ids_val)
    test_ids = np.array(all_ids_test)
    np.save(os.path.join(args.save_path, 'train_ids.npy'), train_ids)
    np.save(os.path.join(args.save_path, 'val_ids.npy'), val_ids)
    np.save(os.path.join(args.save_path, 'test_ids.npy'), test_ids)
    return train_ids, val_ids, test_ids



if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="""Generate proportional Train/Val/Test indices.""")
    parser.add_argument('-c', '--composers_tsv', type=str, default='./data/composers.tsv', help='composers tsv file')
    parser.add_argument('-i', '--id_composers_tsv', type=str, default='./data/id_composers.tsv', help='ID/composers tsv file')
    parser.add_argument('-t', '--prop_train', type=float, default=0.6, help='proportion of dataset that will be in the train set')
    parser.add_argument('-v', '--prop_val', type=float, default=0.2, help='proportion of dataset that will be in the validation set')
    parser.add_argument('-s', '--save_path', type=str, default='./checkpoints/', help='save path')
    parser.add_argument('-r', '--random_seed', type=int, default=1, help='random seed')

    args = parser.parse_args()
    tr, va, te = generate_dataset(args)
    print(tr.shape)
    print(va.shape)
    print(te.shape)