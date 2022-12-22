import os
import logging
import torch
import numpy as np
import tqdm
import argparse
from torch.utils.data import DataLoader
import pandas as pd
import yaml

from model import ComposersClassifier
from dataset import NotesDataset, custom_collate_fn


@torch.no_grad()
def generate_prediction(model, device, test_loader, criterion, logger, SAVE_PATH, composers_tsv, test_ids):
    model.eval()  # Important: eval mode (affects dropout, batch norm etc)
    test_loss = 0
    correct = 0
    composers = pd.read_csv(composers_tsv, sep='\t')
    preds = pd.DataFrame(columns=['ID', 'predicted_composer'])
    for i, (data, target) in enumerate(tqdm.tqdm(test_loader)):
        data, target = data.to(device), target.to(device)
        output = model(data)
        test_loss += criterion(output, target).item() * len(data)
        pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
        pred = pred.cpu()
        preds = preds.append({'ID':test_ids[i], 'predicted_composer':composers['composer'][pred.item()]}, ignore_index=True)
        correct += pred.eq(target.cpu().argmax(dim=1, keepdim=True).view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)

    logger.info(
        f"Test set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{len(test_loader.dataset)} ({100.0 * correct / len(test_loader.dataset):.1f}%)"
    )
    print(
        "Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.1f}%)".format(
            test_loss,
            correct,
            len(test_loader.dataset),
            100.0 * correct / len(test_loader.dataset),
        )
    )

    preds.to_csv(os.path.join(SAVE_PATH, 'predictions.tsv'), sep='\t')
    return test_loss, correct / len(test_loader.dataset)
 

def test(
    num_classes,
    delta,
    num_workers,
    device,
    SAVE_PATH,
    LOAD_FILE,
    ids_folder,
    CSV_DIR,
    zipped,
    NOTES_ZIP_OR_DIR="",
    ):

    logging.basicConfig(filename=os.path.join(SAVE_PATH, "std_test.log"), format='%(asctime)s %(message)s', filemode='w') 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging.info("starting training...")

    # ===== Dataset and DataLoader =====
    test_ids = np.load(os.path.join(ids_folder, 'test_ids.npy'))

    composers_ID_filepath = os.path.join(CSV_DIR, "id_composers.tsv")
    composers_filepath = os.path.join(CSV_DIR, "composers.tsv")

    test_set = NotesDataset(composers_ID_filepath, composers_filepath, num_classes, delta, -1, NOTES_ZIP_OR_DIR, test_ids, zipped=zipped, logger=logger)
    test_loader = DataLoader(test_set, 1, shuffle=False, num_workers=num_workers, collate_fn=custom_collate_fn)

    # ===== Model, Optimizer and Criterion =====
    model = ComposersClassifier(num_classes, delta, device)
    model.load_state_dict(torch.load(LOAD_FILE))
    model = model.to(device=device)
    criterion = torch.nn.functional.cross_entropy

    # ===== Test Model =====
    return generate_prediction(model, device, test_loader, criterion, logger, SAVE_PATH, composers_filepath, test_ids)


def main(args):
    with open(args.config, 'r') as stream:
        config = yaml.safe_load(stream)
    try:
        test(
            config['num_classes'],
            1/config['delta'],
            config['num_workers'],
            torch.device("cuda" if config['cuda'] and torch.cuda.is_available() else "cpu"),
            config['save_path'],
            config['load_checkpoint'],
            config['ids_folder'],
            config['csv_dir'],
            config['zipped'],
            config['notes_zip_or_dir'],
            )
    except Exception as e:
        logging.exception(str(e))


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="""Test ComposersClassifier.""")
    parser.add_argument('--config', required=True, help='path to yaml config')

    args = parser.parse_args()
    main(args)
