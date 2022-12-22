import os
import torch
import pandas as pd
import numpy as np
import zipfile


def compute_random_indices(partial_dataset, prop_train, prop_test, zipped, NOTES_ZIP_OR_DIR):
  assert(partial_dataset > 0)
  if zipped:
      with zipfile.ZipFile(NOTES_ZIP_OR_DIR) as zfile:
          nb_files = len(zfile.namelist())
  else:
      nb_files = len(os.listdir(NOTES_ZIP_OR_DIR))
  if partial_dataset > nb_files:
      partial_dataset = nb_files
  indices = np.arange(nb_files)
  np.random.shuffle(indices)
  p = int(prop_train*partial_dataset)
  q = int((1-prop_test)*partial_dataset)
  train_indices = indices[:p]
  val_indices = indices[p:q]
  test_indices = indices[q:partial_dataset]
  return train_indices, val_indices, test_indices


def compute_balanced_indices(num_classes, nb_train, nb_val, nb_test, zipped, NOTES_ZIP_OR_DIR, composers_ID_filepath, composers_filepath):
  nb_total = nb_train + nb_val + nb_test
  if zipped:
      with zipfile.ZipFile(NOTES_ZIP_OR_DIR) as zfile:
        nb_files = len(zfile.namelist())
  else:
      nb_files = len(os.listdir(NOTES_ZIP_OR_DIR))
  id_composers = pd.read_csv(composers_ID_filepath, sep='\t')
  composers = pd.read_csv(composers_filepath, sep='\t')
  indices = np.arange(nb_files)
  train_indices, val_indices, test_indices = [], [], []
  train_count = dict()
  val_count = dict()
  test_count = dict()
  for i in composers.index:
    train_count[composers['composer'][i]] = 0
    val_count[composers['composer'][i]] = 0
    test_count[composers['composer'][i]] = 0
  count = 0
  np.random.shuffle(indices)
  i = 0
  if zipped:
      with zipfile.ZipFile(NOTES_ZIP_OR_DIR) as zfile:
          namelist = zfile.namelist()
  else:
      namelist = os.listdir(NOTES_ZIP_OR_DIR)
  while count < num_classes*nb_total and i < len(indices):
    idx = indices[i]
    i += 1
    if zipped:
        ID = int(namelist[idx].split('.')[0])
    else:
        ID = int(os.listdir(NOTES_ZIP_OR_DIR)[idx].split('/')[0])
    composer = id_composers[id_composers['ID']==ID]['composer'].values[0]
    if train_count[composer] >= nb_train:
        if val_count[composer] >= nb_val:
            if test_count[composer] >= nb_test:
                continue
            else:
                test_count[composer] += 1
                test_indices.append(idx)
                count += 1
                continue
        else:
            val_count[composer] += 1
            val_indices.append(idx)
            count += 1
            continue
    else:
        train_count[composer] += 1
        train_indices.append(idx)
        count += 1
        continue
  
  return np.array(train_indices), np.array(val_indices), np.array(test_indices)


def get_ids_from_indices(indices, zipped, NOTES_ZIP_OR_DIR):
  if zipped:
    with zipfile.ZipFile(NOTES_ZIP_OR_DIR) as zfile:
      files = len(zfile.namelist())
  else:
    files = len(os.listdir(NOTES_ZIP_OR_DIR))
  return np.array([files[idx].split('.')[0] for idx in indices])


def frac2float(frac_series):
  vals = frac_series.str.split('/')
  res = torch.zeros(vals.shape, dtype=torch.float32)
  for i, val in enumerate(vals):
    if len(val) == 2:
      res[i] = int(val[0]) / int(val[1])
    else:
      res[i] = float(val[0])
  return res

def frac2float_scalar(frac):
  val = str(frac).split('/')
  if len(val) == 2:
    return int(val[0]) / int(val[1])
  return float(val[0])

def get_global_index(mc_series, frac_series, delta):
  if frac_series.dtype != str:
    return -1
  factor = int(1/delta)
  vals = frac_series.str.split('/')
  res = torch.zeros(vals.shape, dtype=torch.int)
  for i, val in enumerate(vals):
    if len(val) == 2:
      res[i] = factor * int(mc_series[i]-1) + (int(val[0]) / int(val[1])) * factor
    else:
      res[i] = int((int(mc_series[i]-1) + float(val[0])) * factor)
  return res

def midi2idx(midi):
  return midi//12, midi%12

def load_score(filename, delta, zipped, logger, NOTES_ZIP_OR_DIR="", stride=-1):
  if zipped:
    with zipfile.ZipFile(NOTES_ZIP_OR_DIR) as z:
      with z.open(filename) as f:
        notes = pd.read_csv(f, sep='\t')
  else:
    filepath = os.path.join(NOTES_ZIP_OR_DIR, filename)
    notes = pd.read_csv(filepath, sep='\t')
  notes['global_index'] = get_global_index(notes['mn'], notes['mn_onset'], delta)
  notes['duration_frames'] = (notes['duration'].apply(frac2float_scalar) / delta).astype(int)
  try:
    mn_max = torch.max(torch.tensor(notes['mn'].values)).item()
  except:
    mn_max = 0
  t_max = int(mn_max/delta)
  if t_max <= 0:
    if logger:
      logger.info("Score with length 0: " + filename)
    t_max = 1
  score = torch.zeros((t_max, 11, 12))
  for i in notes.index:
    starting_time = notes['global_index'][i]
    duration = notes['duration_frames'][i]
    row, col = midi2idx(notes['midi'][i])
    score[starting_time:starting_time+duration, row, col] = 1
  chunk_size = int(4/delta)
  if stride < 0:
    stride = chunk_size
  assert(stride > 0)
  nb_chunks = max(0, (t_max-chunk_size)//stride+1)
  chunks = torch.zeros(nb_chunks, chunk_size, score.shape[1], score.shape[2])
  for i in range(nb_chunks):
    chunks[i,:,:,:] = score[i*stride:i*stride+chunk_size,:,:]
  return chunks
