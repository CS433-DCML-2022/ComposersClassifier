import argparse
import os
import numpy as np
import matplotlib.pyplot as plt


def main(args):
    folder = args.checkpoint_folder
    train_acc_history = np.load(os.path.join(folder, 'train_accs.npy'))
    val_acc_history = np.load(os.path.join(folder, 'val_accs.npy'))
    train_loss_history = np.load(os.path.join(folder, 'train_losses.npy'))
    val_loss_history = np.load(os.path.join(folder, 'val_losses.npy'))
    lr_history = np.load(os.path.join(folder, 'lrs.npy'))
    num_epochs = np.load(os.path.join(folder, 'epoch.npy'))

    # ===== Plot training curves =====
    n_train = len(train_acc_history)
    t_train = num_epochs * np.arange(n_train) / n_train
    t_val = np.arange(1, num_epochs + 1)

    plt.figure(figsize=(6.4 * 3, 4.8))
    plt.subplot(1, 3, 1)
    plt.plot(t_val, val_acc_history)
    plt.xlabel("Epoch")
    plt.ylabel("Validation Accuracy")

    plt.subplot(1, 3, 2)
    plt.plot(t_val, val_loss_history)
    plt.xlabel("Epoch")
    plt.ylabel("Validation Loss")

    plt.subplot(1, 3, 3)
    plt.plot(t_train, lr_history)
    plt.xlabel("Epoch")
    plt.ylabel("Learning Rate")

    plt.show()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""Plot training curves of a given checkpoint.""")
    parser.add_argument('-c', '--checkpoint_folder', required=True, help='path to the checkpoint folder')

    args = parser.parse_args()
    main(args)
