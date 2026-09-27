import os
import torch
from tqdm import tqdm
import numpy as np
from ..common.pipeline.pipline_ddim_scaled_urbanflow import SCALEDUrbanFlowPipeline
import matplotlib.pyplot as plt
import torch
import torch.distributed as dist
from accelerate.utils import gather_object
import torch
from tqdm import tqdm
from accelerate import PartialState
from accelerate.utils import gather_object

def visualize(gt, prediction,building,height_level, filename):
    gt = gt.cpu().numpy()
    prediction = prediction.cpu().numpy()
    if building is not None:
        building = building.to(torch.bool)
        building = building.cpu().numpy()
        # import pdb; pdb.set_trace()
        gt[:,building[0]] = -1
        prediction[:,building[0]] = -1
    fig, axs = plt.subplots(3, 3, figsize=(9, 6))
    axs[0, 0].set_title('Prediction', fontsize=8)
    axs[1, 0].set_title('Ground Truth', fontsize=8)
    axs[2, 0].set_title('diff', fontsize=8)
    for i in range(3):
        pred_img = axs[0, i].imshow(prediction[i][height_level, :, :], vmin=-1, vmax=1)
        gt_img = axs[1, i].imshow(gt[i][height_level, :, :], vmin=-1, vmax=1)
        diff = np.abs(prediction[i][height_level, :, :] - gt[i][height_level, :, :])
        diff_img = axs[2, i].imshow(diff, vmin=0, vmax=0.2)
        axs[0, i].tick_params(axis='both', which='major', labelsize=4)
        axs[1, i].tick_params(axis='both', which='major', labelsize=4)
        axs[2, i].tick_params(axis='both', which='major', labelsize=4)
        fig.colorbar(pred_img, ax=axs[0, i], fraction=0.046, pad=0.04)
        fig.colorbar(gt_img, ax=axs[1, i], fraction=0.046, pad=0.04)
        fig.colorbar(diff_img, ax=axs[2, i], fraction=0.046, pad=0.04)
    plt.savefig(filename, dpi=300)
    plt.close()
    
def visualize_single(value,filename):
    plt.imshow(value)
    plt.savefig(filename,dpi=300)
    plt.close()


class predict_model:
    def __init__(self,
                 model,
                 noise_scheduler,
                 subdomain_size,
                 num_inference_steps,):
        self.subdomain_size = subdomain_size
        self.pipe = SCALEDUrbanFlowPipeline(
                model,
                scheduler=noise_scheduler)
        self.num_inference_steps = num_inference_steps
            
    def predict(self,input):
        pre = self.pipe(
                input[0],
                input[1],
                num_inference_steps=self.num_inference_steps,
                guidance_scale=0,
                depth=self.subdomain_size[0],
                height=self.subdomain_size[1],
                width=self.subdomain_size[2],
                generator=torch.manual_seed(12580),
                return_dict=False,)
        return pre

    def to(self,device):
        self.pipe.to(device)
        return self


class predict_model_unet:
    def __init__(self,
                 model,
                 subdomain_size):
        self.subdomain_size = subdomain_size
        self.model = model
    
    @torch.no_grad()
    def predict(self,input):
        original_data = input[0].clone().to(self.model.device)
        bg_data = input[1].clone().to(self.model.device)
        in_data = torch.cat([original_data,bg_data],dim=1)
        pre = self.model(in_data).sample
        return original_data+pre

    def to(self,device):
        self.model.to(device)
        return self


class DomainDecomposition:
    def __init__(self,
                 model,
                 domain_size=(64,488,488),
                 dataset = None,
                 result_dir = None,
                 ):
        self.domain_size = domain_size
        
        self.dataset = dataset
        self.result_dir = result_dir
        self.model=model
        self.makedirs()
        
    def makedirs(self,):
        self.npz_file = self.result_dir + '/result'
        self.image_dir = self.result_dir + '/image'
        os.makedirs(self.npz_file, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        
    def split_dataset(self,):
        pass
    
    def patch_4Nx_flow_past_building(self,data,subdomain_size,halo_size):
        _,d,h,w = data.shape
        data_result = []
        index_list = []
        skip_d = subdomain_size[0]-2
        skip_h = subdomain_size[1]-2*halo_size
        skip_w = subdomain_size[2]-2*halo_size
        for d_index in range(1):
            for h_index in range(0, (h-2*halo_size)//skip_h):
                for w_index in range(0, (w-2*halo_size)//skip_w):
                    data_result.append(data[:,d_index*skip_d:d_index*skip_d+subdomain_size[0],
                                            h_index*skip_h:h_index*skip_h+subdomain_size[1],
                                            w_index*skip_w:w_index*skip_w+subdomain_size[2]])
                    index_list.append([(d_index*skip_d,d_index*skip_d+subdomain_size[0]),
                                       (h_index*skip_h,h_index*skip_h+subdomain_size[1]),
                                       (w_index*skip_w,w_index*skip_w+subdomain_size[2])])
        return torch.stack(data_result),index_list
    
    def subdomain_interations(self,data_0,data_1,boundary_condition,subdomain_size,halo_size=4,divide_number=25,num_gpus=1):
        # data_1[:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = \
        #     data_0[:,1:-1,halo_size:-halo_size,halo_size:-halo_size]
        self.model.to('cuda')
        sub_data_0,index_list = self.patch_4Nx_flow_past_building(data_0, subdomain_size,halo_size)
        sub_data_1,_ = self.patch_4Nx_flow_past_building(data_1, subdomain_size,halo_size)
        building,_ = self.patch_4Nx_flow_past_building(boundary_condition, subdomain_size,halo_size)
        building = building.to(torch.bool)
        # initialize the inpainting space
        sub_data_1[:,:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = 1
        sub_data_1[:,0:1][building] = 0
        sub_data_1[:,1:2][building] = 0
        sub_data_1[:,2:3][building] = 0
        
        n = len(sub_data_0)//divide_number
        pre_result = []
        for i in tqdm(range(n)):
            sub_data_0_input = sub_data_0[i*divide_number:(i+1)*divide_number]
            sub_data_1_input = sub_data_1[i*divide_number:(i+1)*divide_number]
            input = (sub_data_0_input,sub_data_1_input)
            # import pdb; pdb.set_trace()
            pre = self.model.predict(input)
            pre_result.append(pre)
        pre = torch.cat(pre_result)
        return pre,index_list
    
    def fill_value(self,data_1_boundary,prediction,index_list,halo_size=4):
        for i in range(len(index_list)):
            d_index_begin = index_list[i][0][0]+1
            d_index_end = index_list[i][0][1]-1
            h_index_begin = index_list[i][1][0]+halo_size
            h_index_end = index_list[i][1][1]-halo_size
            w_index_begin = index_list[i][2][0]+halo_size
            w_index_end = index_list[i][2][1]-halo_size
            data_1_boundary[:,d_index_begin:d_index_end,h_index_begin:h_index_end,w_index_begin:w_index_end] = \
            prediction[i][:,1:-1,halo_size:-halo_size,halo_size:-halo_size]
        return data_1_boundary

    
    def predict(self,
                AI4PDEs_timesteps,
                subdomain_iteration,
                subdomain_size,
                halo_size,
                divide_number=25,
                num_gpus=1,
                ):
        ## initialize the first data
        data_0,_ = self.dataset[0]
        data_0 = data_0[:,:,0:self.domain_size[1],0:self.domain_size[2]]
        building = data_0[3:].clone()
        data_0 = data_0[:3].clone()
        building_information = building.clone().to(torch.bool)
        for timestep in [AI4PDEs_timesteps*i for i in range(1,101)]:
            gt,_ = self.dataset[timestep]
            gt = gt[:3].clone()
            gt = gt[:,:,0:self.domain_size[1],0:self.domain_size[2]]
            # initialize the prediction tem
            prediction_tem = gt.clone()
            prediction_tem[:,-1:1,halo_size:-halo_size,halo_size:-halo_size] = 0
            # initalize the inpainting space
            inpainting_space = gt.clone()
            inpainting_space[:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = data_0[:,1:-1,halo_size:-halo_size,halo_size:-halo_size]
            
            # begin inpainting
            for k in range(subdomain_iteration):
                os.makedirs(f'{self.npz_file}/{k}',exist_ok=True)
                os.makedirs(f'{self.image_dir}/{k}',exist_ok=True)
                # visualize_single(data_0[0,4],f'analysis/data_0_{timestep}_{k}.png')
                # visualize_single(inpainting_space[0,4],f'analysis/inpainting_space_{timestep}_{k}.png')
                pre,index_list = self.subdomain_interations(data_0.clone(),inpainting_space.clone(),building,subdomain_size,halo_size,divide_number,num_gpus)
                prediction = self.fill_value(prediction_tem,pre,index_list,halo_size)
                # visualize_single(prediction[0,4],f'analysis/prediction_{timestep}_{k}.png')
                # force the boundary to the prediction
                prediction[0:1][building_information] = 0
                prediction[1:2][building_information] = 0
                prediction[2:3][building_information] = 0
                tem =gt.clone()
                tem[:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = prediction[:,1:-1,halo_size:-halo_size,halo_size:-halo_size].clone()
                prediction_tem = tem.clone()
                # save the result
                # visualize_single(prediction[0,4],f'analysis/prediction_v2_{timestep}_{k}.png')
                visualize(gt.clone(),prediction.clone(),building.clone(),4,f'{self.image_dir}/{k}/{timestep:05d}.png')
                if k == subdomain_iteration-1:
                    np.save(f'{self.npz_file}/{k}/{timestep:05d}.npy',prediction.clone().cpu().numpy())
                inpainting_space[:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = prediction[:,1:-1,halo_size:-halo_size,halo_size:-halo_size]
                # visualize_single(prediction[0,4],f'analysis/prediction_v1_{timestep}_{k}.png')
            data_0 = inpainting_space.clone()



class DomainDecompositionMultipleGPUs(DomainDecomposition):
    def subdomain_interations(self,data_0,data_1,boundary_condition,subdomain_size,halo_size=4,divide_number=25,num_gpus=1):
        sub_data_0,index_list = self.patch_4Nx_flow_past_building(data_0, subdomain_size,halo_size)
        sub_data_1,_ = self.patch_4Nx_flow_past_building(data_1, subdomain_size,halo_size)
        building,_ = self.patch_4Nx_flow_past_building(boundary_condition, subdomain_size,halo_size)
        building = building.to(torch.bool)
        # initialize the inpainting space
        sub_data_1[:,:,1:-1,halo_size:-halo_size,halo_size:-halo_size] = 1
        sub_data_1[:,0:1][building] = 0
        sub_data_1[:,1:2][building] = 0
        sub_data_1[:,2:3][building] = 0
        n = len(sub_data_0)//divide_number
        print(f'n: {n}')
        pre_result = []
        input_list = []
        for i in range(n):
            sub_data_0_input = sub_data_0[i*divide_number:(i+1)*divide_number]
            sub_data_1_input = sub_data_1[i*divide_number:(i+1)*divide_number]
            input_list.append((sub_data_0_input,sub_data_1_input))
        
        iteration = len(input_list)//num_gpus
        print(f'iteration: {iteration}')
        for i in tqdm(range(iteration)):
            sub_input_list = input_list[i*num_gpus:(i+1)*num_gpus]
            distributed_state = PartialState()
            self.model.to(distributed_state.device)
            with distributed_state.split_between_processes(sub_input_list) as input:
                pre = self.model.predict(input[0])
            pre = gather_object(pre)
            for i in range(len(pre)):
                pre[i] = pre[i].to('cpu')
            pre = torch.stack(pre)
            # pre.to('cuda')
            pre_result.append(pre)
        pre = torch.cat(pre_result)
        return pre,index_list