import os
from torch.utils.data import Dataset
import numpy as np
import torch
import random
import json

class UrbanFlowSplitDataset(Dataset):
    def __init__(
            self,
            data_dir='',
            width=128,
            height=128,
            depth=64,
            subdomain_size=32,
            stride=4,
            rotato_ratio=0.5,
            skip_timestep=50,
            time_steps_list=[i for i in range(2000)]):
        self.data_dir = data_dir
        self.height = height
        self.width = width
        self.depth = depth
        self.subdomain_size = subdomain_size
        self.data_list = time_steps_list
        self.random_rotate = rotato_ratio
        self.stride = stride
        self.skip_timestep = skip_timestep

    def __len__(self):
        return len(self.data_list)-self.skip_timestep

    def get_data(self,time_step,height_idx,width_idx,random_x,random_y):
        file_name = f'{random_x}_{random_y}.npy'
        u_data = np.load(os.path.join(self.data_dir, f"u{time_step}",file_name),mmap_mode='r')
        v_data = np.load(os.path.join(self.data_dir, f"v{time_step}",file_name),mmap_mode='r')
        w_data = np.load(os.path.join(self.data_dir, f"w{time_step}",file_name),mmap_mode='r')
        boundary_tensor = np.load(os.path.join(self.data_dir, f"sigma",file_name),mmap_mode='r')/1e8
        
        u_data = u_data/3
        v_data = v_data/3
        w_data = w_data/3
        result = np.stack([u_data, v_data, w_data,boundary_tensor], axis=0)[:,:,height_idx*self.stride:height_idx*self.stride+self.subdomain_size,width_idx*self.stride:width_idx*self.stride + self.subdomain_size]
        return result

    def _random_rotation_90(self,array,k1):
        # 随机选择旋转次数 0, 1, 2, 3 分别对应 0°, 90°, 180°, 270°
        rotated_array = np.rot90(array, k=k1, axes=(1, 2))  # 沿 X 轴旋转
        return rotated_array

    def rotation(self,data,k1):
        data = np.stack([self._random_rotation_90(data[i],k1) for i in range(len(data))])
        return data

    def __getitem__(self,idx):
        time_step = self.data_list[idx]
        randon_x = random.randint(0, 7)
        random_y = random.randint(0, 7)
        height_idx = random.randint(0, (self.height-self.subdomain_size)/self.stride)
        width_idx = random.randint(0, (self.width-self.subdomain_size)/self.stride)
        ori_data = self.get_data(time_step,height_idx,width_idx,randon_x,random_y)
        future_data = self.get_data(time_step+self.skip_timestep,height_idx,width_idx,randon_x,random_y)

        # rotation
        if random.random() < self.random_rotate:
            k1 = np.random.randint(0, 4)
            ori_data = self.rotation(ori_data,k1)
            future_data = self.rotation(future_data,k1)
        return torch.from_numpy(ori_data).float(),torch.from_numpy(future_data).float()

class UrbanFlowDataset(Dataset):
    def __init__(
            self,
            data_dir='',
            width=512,
            height=512,
            depth=62,
            subdomain_size=64,
            rotato_ratio=0.5,
            time_steps_list=[i for i in range(2000)],
            skip_timestep=50):
        self.data_dir = data_dir
        self.height = height
        self.width = width
        self.depth = depth
        self.subdomain_size = subdomain_size
        self.skip_timestep = skip_timestep
        self.data_list = time_steps_list
        self.random_rotate = rotato_ratio

    def __len__(self):
        return len(self.data_list)-self.skip_timestep

    def get_data(self,time_step):
        u_data = np.load(os.path.join(self.data_dir, f"u{time_step}.npy"),mmap_mode='r')
        # u_data = np.zeros((u_data_temple.shape[0]+2,u_data_temple.shape[1],u_data_temple.shape[2]))
        # u_data[1:-1] = u_data_temple
        # u_data[-1:] = u_data[-5:-4]
        
        v_data = np.load(os.path.join(self.data_dir, f"v{time_step}.npy"),mmap_mode='r')
        # v_data = np.zeros((v_data_temple.shape[0]+2,v_data_temple.shape[1],v_data_temple.shape[2]))
        # v_data[1:-1] = v_data_temple
        # v_data[-1:] = v_data[-5:-4]
        
        w_data = np.load(os.path.join(self.data_dir, f"w{time_step}.npy"),mmap_mode='r')
        # w_data = np.zeros((w_data_temple.shape[0]+2,w_data_temple.shape[1],w_data_temple.shape[2]))
        # w_data[1:-1] = w_data_temple
        
        # boundary_tensor_temple = np.load(os.path.join(self.data_dir, f"sigma.npy"))[0,0][:62]/1e8
        # boundary_tensor = np.zeros((boundary_tensor_temple.shape[0] + 2, boundary_tensor_temple.shape[1], boundary_tensor_temple.shape[2]))
        # boundary_tensor[1:-1] = boundary_tensor_temple
        boundary_tensor = np.load(os.path.join(self.data_dir, f"sigma.npy"))[0,0]/1e8
        
        u_data = (u_data)/3
        v_data = (v_data)/3
        w_data = (w_data)/3
        result = np.stack([u_data, v_data, w_data,boundary_tensor], axis=0)
        return result


    def __getitem__(self,idx):
        time_step = self.data_list[idx]
        ori_data = self.get_data(time_step)
        future_data = self.get_data(time_step+self.skip_timestep)
        return torch.from_numpy(ori_data).float(),torch.from_numpy(future_data).float()