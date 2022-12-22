import os
import pandas as pd
import torch
import zipfile
from torch.utils.data import Dataset
from torch.utils.data.dataloader import default_collate

from utils import load_score


global_delta = 1/32

class NotesDataset(Dataset):
        def __init__(self, tsv_id_composers, tsv_composers, num_classes, delta, chunk_stride, notes_dir, ids, zipped, logger):
          self.logger = logger
          self.zipped = zipped
          self.num_classes = num_classes
          self.delta = delta
          self.chunk_stride = chunk_stride
          global_delta = delta
          comp_occurences = pd.read_csv(tsv_composers, sep='\t')
          self.composers = dict()
          for i in comp_occurences.index:
            self.composers[comp_occurences['composer'][i]] = i
          self.id_composers = pd.read_csv(tsv_id_composers, sep='\t')
          self.notes_dir = notes_dir
          self.files = [str(id)+'.tsv' for id in ids]

        def __len__(self):
          return len(self.files)

        def __getitem__(self, index):
          chunks = load_score(self.files[index], self.delta, zipped=self.zipped, logger=self.logger, NOTES_ZIP_OR_DIR=self.notes_dir, stride=self.chunk_stride)
          label = torch.zeros(self.num_classes)
          id = int(self.files[index].split(".")[0])
          label[self.composers[self.id_composers.loc[self.id_composers['ID']==id]['composer'].values[0]]] = 1
          return chunks, label


def custom_collate_fn(batch):
  try:
    empty_chunk = torch.zeros_like(batch[0][0][0])
  except:
    empty_chunk = torch.zeros((int(4/global_delta), 11, 12))
  empty_chunk = empty_chunk[None,:]
  max_size = max([score[0].shape[0] for score in batch])
  for i, score in enumerate(batch):
    batch[i] = (torch.cat([score[0]] + [empty_chunk]*(max_size - score[0].shape[0])), score[1])
  return default_collate(batch)