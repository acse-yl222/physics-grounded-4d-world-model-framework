import os
from torch.utils.data import Dataset
import numpy as np
import torch
import random
import h5py

class UrbanFlowDataset(Dataset):
    def __init__(
            self,
            data_dir='',
            width=1024,
            height=1024,
            depth=64,
            subdomain_size=128,
            skip_timestep=50,
            time_steps_list=[i for i in range(2000)]):
        self.data_dir = data_dir
        self.height = height
        self.width = width
        self.depth = depth
        self.stride = 1
        self.subdomain_size = subdomain_size
        self.data_list = time_steps_list
        self.skip_timestep = skip_timestep
        self.boundary_tensor = np.load(os.path.join(self.data_dir, f"sigma.npy"),mmap_mode='r')[0]/1e8

    def __len__(self):
        return len(self.data_list)-self.skip_timestep-1

    def get_data(self,time_step,height_idx,width_idx):
        filename = os.path.join(self.data_dir,f'{time_step:06}.h5')
        with h5py.File(filename, 'r') as f:
            data = f['uvw']
            sub_domain = data[:,:,height_idx*self.stride:height_idx*self.stride+self.subdomain_size,width_idx*self.stride:width_idx*self.stride + self.subdomain_size]
        sub_domain = sub_domain/3
        subdomain_geometry = self.boundary_tensor[:,:,height_idx*self.stride:height_idx*self.stride+self.subdomain_size,width_idx*self.stride:width_idx*self.stride + self.subdomain_size]
        return sub_domain,subdomain_geometry

    def _random_rotation_90(self,array,k1):
        rotated_array = np.rot90(array, k=k1, axes=(1, 2))  # 沿 X 轴旋转
        return rotated_array

    def rotation(self,data,k1):
        data = np.stack([self._random_rotation_90(data[i],k1) for i in range(len(data))])
        return data

    def __getitem__(self,idx):
        time_step = self.data_list[idx]
        height_idx = random.randint(0, (self.height-self.subdomain_size)/self.stride)
        width_idx = random.randint(0, (self.width-self.subdomain_size)/self.stride)
        ori_data,sub_domain_geometry = self.get_data(time_step,height_idx,width_idx)
        future_data,_ = self.get_data(time_step+self.skip_timestep,height_idx,width_idx)
        return torch.from_numpy(ori_data).float(),torch.from_numpy(future_data).float(),torch.from_numpy(sub_domain_geometry)
    

class UrbanFlowDatasetV1(UrbanFlowDataset):
    def __init__(
            self,
            data_dir='',
            width=1024,
            height=1024,
            depth=64,
            subdomain_size=128,
            skip_timestep=50,
            time_steps_list=[i for i in range(2000)]):
        super().__init__(data_dir,width,height,depth,subdomain_size,skip_timestep,time_steps_list)

    def __getitem__(self,idx):
        time_step = self.data_list[idx]
        height_idx = random.randint(0, (self.height-self.subdomain_size)/self.stride)
        width_idx = random.randint(0, (self.width-self.subdomain_size)/self.stride)
        ori_data, sub_domain_geometry = self.get_data(time_step,height_idx,width_idx)
        future_data,_ = self.get_data(time_step+self.skip_timestep,height_idx,width_idx)
        mask_bools = sub_domain_geometry[0].astype(bool)
        bg_data = np.ones_like(ori_data)
        bg_data[:,mask_bools] = 0
        return torch.from_numpy(ori_data).float(),torch.from_numpy(bg_data),torch.from_numpy(future_data).float(),torch.from_numpy(sub_domain_geometry)
