import os
import logging
import torch
import numpy as np
import tqdm
import yaml
import argparse
from torch.utils.data import DataLoader

from model import ComposersClassifier
from dataset import NotesDataset, custom_collate_fn
from utils import get_ids_from_indices, compute_random_indices


def train_epoch(model, optimizer, scheduler, criterion, train_loader, epoch, device, logger):
    model.train()
    loss_history = []
    accuracy_history = []
    lr_history = []
    
    for batch_idx, (data, target) in enumerate(tqdm.tqdm(train_loader)):
        data = data.to(device)
        target = target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        scheduler.step()

        output = torch.argmax(output, axis=1)
        target = torch.argmax(target, axis=1)
        accuracy_float = torch.mean((output==target)*1.).item()
        loss_float = loss.item()
        loss_history.append(loss_float)
        accuracy_history.append(accuracy_float)
        lr_history.append(scheduler.get_last_lr()[0])
        if batch_idx % (len(train_loader.dataset) // len(data) // 10) == 0:
            logger.info(
                f"Train Epoch: {epoch}-{batch_idx:03d} "
                f"batch_loss={loss_float:0.2e} "
                f"batch_acc={accuracy_float:0.3f} "
                f"lr={scheduler.get_last_lr()[0]:0.3e} "
            )
            print(
                f"Train Epoch: {epoch}-{batch_idx:03d} "
                f"batch_loss={loss_float:0.2e} "
                f"batch_acc={accuracy_float:0.3f} "
                f"lr={scheduler.get_last_lr()[0]:0.3e} "
            )

    return loss_history, accuracy_history, lr_history


@torch.no_grad()
def validate(model, device, val_loader, criterion, logger):
    model.eval()  # Important: eval mode (affects dropout, batch norm etc)
    test_loss = 0
    correct = 0
    for data, target in tqdm.tqdm(val_loader):
        data, target = data.to(device), target.to(device)
        output = model(data)
        test_loss += criterion(output, target).item() * len(data)
        pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
        pred = pred.cpu()
        correct += pred.eq(target.cpu().argmax(dim=1, keepdim=True).view_as(pred)).sum().item()

    test_loss /= len(val_loader.dataset)

    logger.info(
        f"Test set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{len(val_loader.dataset)} ({100.0 * correct / len(val_loader.dataset):.0f}%)"
    )
    print(
        "Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)".format(
            test_loss,
            correct,
            len(val_loader.dataset),
            100.0 * correct / len(val_loader.dataset),
        )
    )
    return test_loss, correct / len(val_loader.dataset)


@torch.no_grad()
def get_predictions(model, device, val_loader, criterion, num=None):
    model.eval()
    points = []
    for data, target in val_loader:
        data, target = data.to(device), target.to(device)
        output = model(data)
        loss = criterion(output, target)
        pred = output.argmax(dim=1, keepdim=True)
        data = np.split(data.cpu().numpy(), len(data))
        loss = np.split(loss.cpu().numpy(), len(loss))
        pred = np.split(pred.cpu().numpy(), len(data))
        target = np.split(target.cpu().numpy(), len(data))
        points.extend(zip(data, loss, pred, target))

        if num is not None and len(points) > num:
            break

    return points


def train(
    num_classes,
    delta,
    num_epochs,
    starting_epoch,
    batch_size,
    num_workers,
    initial_learning_rate,
    device,
    SAVE_PATH,
    LOAD_FILE,
    ids_folder,
    CSV_DIR,
    zipped,
    NOTES_ZIP_OR_DIR="",
    nb_train=100,
    nb_val=50,
    nb_test=50,
    partial_dataset=-1
    ):

    logging.basicConfig(filename=os.path.join(SAVE_PATH, "std_train_"+str(starting_epoch)+"-"+str(starting_epoch+num_epochs-1)+".log"), format='%(asctime)s %(message)s', filemode='w') 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.info(
        f"num_classes: {num_classes} "
        f"delta={int(1/delta)} "
        f"num_epochs={num_epochs} "
        f"starting_epoch={starting_epoch} "
        f"batch_size={batch_size} "
        f"num_workers={num_workers} "
        f"initial_lr={initial_learning_rate} "
        f"device={device} "
        f"save_path={SAVE_PATH} "
        f"load_file={LOAD_FILE} "
        f"csv_dir={CSV_DIR} "
        f"zipped={zipped} "
        f"notes_zip_or_dir={NOTES_ZIP_OR_DIR} "
        f"nb_train={nb_train} "
        f"nb_val={nb_val} "
        f"nb_test={nb_test} "
        f"partial_dataset={partial_dataset} "
    )
    logger.info("starting training...")

    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)


    # ===== Dataset and DataLoader =====
    composers_ID_filepath = os.path.join(CSV_DIR, "id_composers.tsv")
    composers_filepath = os.path.join(CSV_DIR, "composers.tsv")
    assert(LOAD_FILE != "" or starting_epoch <= 1)
    # Split into train and test indices
    if LOAD_FILE == "" and partial_dataset > 0:
            nb_total = nb_train + nb_val + nb_test
            train_indices, val_indices, test_indices = compute_random_indices(partial_dataset, nb_train/nb_total, nb_test/nb_total, zipped, NOTES_ZIP_OR_DIR)
            train_ids = get_ids_from_indices(train_indices, zipped, NOTES_ZIP_OR_DIR)
            val_ids = get_ids_from_indices(val_indices, zipped, NOTES_ZIP_OR_DIR)
            test_ids = get_ids_from_indices(test_indices, zipped, NOTES_ZIP_OR_DIR)
            np.save(os.path.join(SAVE_PATH, 'train_ids'), train_ids)
            np.save(os.path.join(SAVE_PATH, 'val_ids'), val_ids)
            np.save(os.path.join(SAVE_PATH, 'test_ids'), test_ids)
    else:
        train_ids = np.load(os.path.join(ids_folder, 'train_ids.npy'))
        val_ids = np.load(os.path.join(ids_folder, 'val_ids.npy'))

    train_set = NotesDataset(composers_ID_filepath, composers_filepath, num_classes, delta, -1, NOTES_ZIP_OR_DIR, train_ids, zipped=zipped, logger=logger)
    train_loader = DataLoader(train_set, batch_size, shuffle=True, num_workers=num_workers, collate_fn=custom_collate_fn)

    val_set = NotesDataset(composers_ID_filepath, composers_filepath, num_classes, delta, -1, NOTES_ZIP_OR_DIR, val_ids, zipped=zipped, logger=logger)
    val_loader = DataLoader(val_set, batch_size, shuffle=False, num_workers=num_workers, collate_fn=custom_collate_fn)

    learning_rate = initial_learning_rate

    # ===== Model, Optimizer and Criterion =====
    model = ComposersClassifier(num_classes, delta, device)
    if LOAD_FILE != "":
        model.load_state_dict(torch.load(LOAD_FILE))
    model = model.to(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = torch.nn.functional.cross_entropy
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lr_lambda=lambda epoch: 1,
    )

    # ===== Train Model =====
    if LOAD_FILE == "" or not os.path.exists(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_lrs.npy')):
        # WARNING: if starting_epoch < max_epoch_already_done, history will be overwritted at some point
        lr_history = []
        train_loss_history = []
        train_acc_history = []
        val_loss_history = []
        val_acc_history = []
    else:
        lr_history = np.load(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_lrs.npy')).tolist()
        train_loss_history = np.load(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_train_losses.npy')).tolist()
        train_acc_history = np.load(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_train_accs.npy')).tolist()
        val_loss_history = np.load(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_val_losses.npy')).tolist()
        val_acc_history = np.load(os.path.join(SAVE_PATH, 'epoch_'+str(starting_epoch-1)+'_val_accs.npy')).tolist()

    for epoch in range(starting_epoch, starting_epoch+num_epochs):
        train_loss, train_acc, lrs = train_epoch(
            model, optimizer, scheduler, criterion, train_loader, epoch, device, logger
        )
        train_loss_history.extend(train_loss)
        train_acc_history.extend(train_acc)
        lr_history.extend(lrs)

        val_loss, val_acc = validate(model, device, val_loader, criterion, logger)
        val_loss_history.append(val_loss)
        val_acc_history.append(val_acc)

        torch.save(model.state_dict(), os.path.join(SAVE_PATH, 'epoch_'+str(epoch)+'.pt'))
        np.save(os.path.join(SAVE_PATH, 'train_losses'), train_loss_history)
        np.save(os.path.join(SAVE_PATH, 'val_losses'), val_loss_history)
        np.save(os.path.join(SAVE_PATH, 'train_accs'), train_acc_history)
        np.save(os.path.join(SAVE_PATH, 'val_accs'), val_acc_history)
        np.save(os.path.join(SAVE_PATH, 'lrs'), lr_history)
        np.save(os.path.join(SAVE_PATH, 'epoch'), np.array([epoch]))


def main(args):
    with open(args.config, 'r') as stream:
        config = yaml.safe_load(stream)
    torch.manual_seed(config['random_seed'])
    try:
        train(
            config['num_classes'],
            1/config['delta'],
            config['num_epochs'],
            config['starting_epoch'],
            config['batch_size'],
            config['num_workers'],
            config['learning_rate'],
            torch.device("cuda" if config['cuda'] != 0 and torch.cuda.is_available() else "cpu"),
            config['save_path'],
            config['load_checkpoint'],
            config['ids_folder'],
            config['csv_dir'],
            config['zipped'],
            config['notes_zip_or_dir'],
            100,
            50,
            50,
            config['partial_dataset'],
            )
    except Exception as e:
        logging.exception(str(e))


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="""Train ComposersClassifier.""")
    parser.add_argument('--config', required=True, help='path to yaml config')

    args = parser.parse_args()
    main(args)
