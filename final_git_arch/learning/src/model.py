import torch
import torch.nn as nn


class ComposersClassifier(nn.Module):
  def __init__(self, num_classes, delta, device, lstm_hidden_size=128, lstm_num_layers=2, fc_hidden_size=64):
    super().__init__()
    self.device = device
    self.lstm_hidden_size = lstm_hidden_size
    self.lstm_num_layers = lstm_num_layers
    # input size: chunk_size x 11 x 12
    # in + 2p - (k-1)
    self.conv1 = nn.Conv3d(1, 8, 3, padding=(0,1,1))
    # size: chunk_size-2 x 11 x 12
    # (in + 2p - (k-1) - 1) / stride + 1
    self.pool1 = nn.MaxPool3d((4,2,2))
    # size: (chunk_size-6)/4+1 x 5 x 6
    self.conv2 = nn.Conv3d(8, 16, 3, padding=(0,1,1))
    # size: ... x 5 x 6
    self.pool2 = nn.MaxPool3d((4,2,2)) # 2 if d 16
    # size: ... x 2 x 3
    self.conv3 = nn.Conv3d(16, 32, 2)
    # size: ... x 1 x 2
    self.pool3 = nn.MaxPool3d((4,1,1))
    # output size: [(96/384)*chunk_size - 16] x 1 x 2
    self.flat1  = nn.Flatten(start_dim=1)
    self.lstm  = nn.LSTM(input_size=4*(int(1/delta)-16), hidden_size=lstm_hidden_size, num_layers=lstm_num_layers) # compute lstm input_size
    # self.lstm  = nn.LSTM(input_size=384, hidden_size=lstm_hidden_size, num_layers=lstm_num_layers) # compute lstm input_size
    self.flat2 = nn.Flatten(start_dim=1)
    self.fc1   = nn.Linear(lstm_num_layers*lstm_hidden_size, fc_hidden_size)
    self.fc2   = nn.Linear(fc_hidden_size, num_classes)
    self.relu = nn.ReLU()
  
  def forward(self, chunks):
    h = torch.autograd.Variable(torch.zeros(self.lstm_num_layers, chunks.shape[0], self.lstm_hidden_size)).to(self.device) #hidden state
    c = torch.autograd.Variable(torch.zeros(self.lstm_num_layers, chunks.shape[0], self.lstm_hidden_size)).to(self.device) #internal state
    for i in range(chunks.shape[1]):
      x = chunks[:,i,None,:,:,:]
      z = self.conv1(x)
      z = self.pool1(z)
      z = self.conv2(z)
      z = self.pool2(z)
      z = self.conv3(z)
      z = self.pool3(z)
      z = self.flat1(z)
      z = z[None,:,:]
      _, (h, c) = self.lstm(z, (h, c))
    h = torch.permute(h, (1, 0, 2))
    h = self.flat2(h) # reshape data for Dense layer next
    out = self.relu(h)
    out = self.fc1(out)
    out = self.relu(out)
    out = self.fc2(out)
    return out
