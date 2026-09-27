import torch
from tqdm import tqdm
import h5py
import numpy as np
import os
import matplotlib.pyplot as plt

class Inference:
    def __init__(self,compression_model,inference_model,initial_information,device):
        self.compression_model = compression_model
        self.compression_model.to(device)
        self.inference_model = inference_model
        self.inference_model.to(device)
        self.initial_information = initial_information
        self.device = device
        
    def initial_file(self,file_name,geometry_name,begin_index_w,begin_index_h,subdomain_size):
        geometry = np.load(geometry_name)[0,0]
        geometry = geometry[:,begin_index_h:begin_index_h+subdomain_size,begin_index_w:begin_index_w+subdomain_size]
        with h5py.File(file_name, 'r') as f:
            data = f['data']
            sub_domain = data[:,:,begin_index_h:begin_index_h+subdomain_size,begin_index_w:begin_index_w+subdomain_size]
        geometry = torch.from_numpy(geometry/1e8).to(self.device).bool()
        sub_domain = torch.from_numpy(sub_domain/3).to(self.device).float().unsqueeze(0)
        return geometry,sub_domain
    
    def visualize(self,subdomain,timestep):
        os.makedirs('result',exist_ok=True)
        result = subdomain[0,4]
        plt.imshow(result,vmin=-0.5,vmax=0.2)
        plt.colorbar()
        plt.savefig(f'result/{timestep:05d}.png')
        plt.close()

    def visualize_geo(self,geometry):
        result = geometry[4]
        plt.imshow(result,vmin=-0.8,vmax=0.8)
        plt.colorbar()
        plt.savefig(f'geometry.png')
        plt.close()
    
    def inference(self,inference_timesteps):
        geometry,subdomain = self.initial_file(**self.initial_information)
        with torch.no_grad():
            input = self.compression_model.encode(subdomain).latent_dist.sample()/10
            input
            for timestep in tqdm(range(inference_timesteps)):
                result  = self.inference_model(input).sample
                subdomain = self.compression_model.decode(result*10).sample
                subdomain[:,:,geometry] = -3
                self.visualize(subdomain.detach().cpu().numpy()[0],timestep)
                input = result

class InferenceGeometry(Inference):
    def __init__(self,compression_model,inference_model,geometry_model,initial_information,device):
        super().__init__(compression_model,inference_model,initial_information,device)
        self.geometry_model = geometry_model
        self.geometry_model.to(self.device)

    
    def inference(self,inference_timesteps):
        geometry,subdomain = self.initial_file(**self.initial_information)
        input_geometry = geometry.float().unsqueeze(0)
        with torch.no_grad():
            input = self.compression_model.encode(subdomain).latent_dist.sample()/10
            input_geometry = self.geometry_model(input_geometry)
            for timestep in tqdm(range(inference_timesteps)):
                result  = self.inference_model(input,control_feature=input_geometry).sample
                subdomain = self.compression_model.decode(result*10).sample
                subdomain[:,:,geometry] = -3
                self.visualize(subdomain.detach().cpu().numpy()[0],timestep)
                # self.visualize_geo(geometry.detach().cpu().numpy())
                input = result

class LatentInference(Inference):
    def __init__(self,compression_model,inference_model,initial_information,device):
        super().__init__(compression_model,inference_model,initial_information,device)

    def initial_file(self, file_name, geometry_name, begin_index_w, begin_index_h, subdomain_size):
        geometry,sub_domain =  super().initial_file(file_name, geometry_name, begin_index_w, begin_index_h, subdomain_size)
        boundary_condition = torch.ones(sub_domain.shape).to(self.device)
        boundary_condition[:,:,:,:,0:9] = -1
        boundary_condition[:,:,:,:,]
        boundary_condition[:,:,geometry] = 0
        return boundary_condition,sub_domain

    def visualize_gt(self,subdomain_gt,timestep):
        os.makedirs('result_gt',exist_ok=True)
        result = subdomain_gt[0,4]
        plt.imshow(result,vmin=-0.5,vmax=0.2)
        plt.colorbar()
        plt.savefig(f'result_gt/{timestep:05d}.png')
        plt.close()

    def inference(self,inference_timesteps):
        boundary_condition,subdomain = self.initial_file(**self.initial_information)
        with torch.no_grad():
            data_0 = self.compression_model.encode(subdomain)/10
            data_bg = self.compression_model.encode(boundary_condition)/10
            input = torch.cat([data_0,data_bg],dim=1)
            for timestep in tqdm(range(inference_timesteps)):
                prediction  = self.inference_model(input).sample
                subdomain = self.compression_model.decode(prediction*10)
                subdomain_gt = self.compression_model.decode(data_0*10)
                subdomain[boundary_condition==0] = -3
                self.visualize(subdomain.detach().cpu().numpy()[0],timestep)
                self.visualize_gt(subdomain_gt.detach().cpu().numpy()[0],timestep)
                input = torch.cat([prediction,data_bg],dim=1)

class LatentInferenceOnlyGeometry:
    def __init__(self,inference_model,initial_information,device):
        self.inference_model = inference_model.to(device)
        self.initial_information = initial_information
        self.device = device

    def initial_file(self, initial_information):
        initial_latent,latent_geometry = initial_information
        initial_latent = initial_latent.to(self.device)
        latent_geometry = latent_geometry.to(self.device)
        return initial_latent,latent_geometry

    def save_latent(self,latent,timestep):
        os.makedirs('saved_latent',exist_ok=True)
        path_name = f'saved_latent/{timestep:05d}.pth'
        torch.save(latent,path_name)

    def visualize(self,subdomain,timestep):
        os.makedirs('result',exist_ok=True)
        result = subdomain[0,4]
        plt.imshow(result,vmin=-0.5,vmax=0.2)
        plt.colorbar()
        plt.savefig(f'result/{timestep:05d}.png')
        plt.close()

    def inference(self,inference_timesteps):
        data_0,data_bg = self.initial_file(self.initial_information)
        data_0 = data_0.to(self.device)/10
        data_bg = data_bg.to(self.device)/10
        with torch.no_grad():
            input = torch.cat([data_0,data_bg],dim=1)
            for timestep in tqdm(range(inference_timesteps)):
                prediction  = self.inference_model(input).sample
                self.save_latent(prediction*10,timestep)
                input = torch.cat([prediction,data_bg],dim=1)