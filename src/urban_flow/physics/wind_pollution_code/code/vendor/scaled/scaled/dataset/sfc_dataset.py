import os
from torch.utils.data import Dataset
import numpy as np
import torch
import random
import json

class SFCDataset(Dataset):
    def __init__(
            self,
            data_dir='',
            data_list=range(1000),
            skip_timestep=1):
        self.data_dir = data_dir
        self.data_list = [f"data_{i}.csv" for i in data_list]

    def __len__(self):
        return len(self.data_list)

    def get_data(self,timestep):
        data = np.load(os.path.join(self.data_dir, self.data_list[timestep]))
        return data

    def __getitem__(self,idx):
        time_step = idx
        ori_data = self.get_data(time_step)
        future_data = self.get_data(time_step+self.skip_timestep)
        return torch.from_numpy(ori_data).float(),torch.from_numpy(future_data).float()