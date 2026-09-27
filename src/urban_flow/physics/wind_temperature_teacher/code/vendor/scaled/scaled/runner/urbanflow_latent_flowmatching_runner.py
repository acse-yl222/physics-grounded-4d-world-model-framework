import random
import torch
import os
from diffusers.utils.import_utils import is_xformers_available
import os
from .urbanflow_flowmatching_runner import UrbanFlowFlowMatchingRunner
from tqdm import tqdm
import torch.nn.functional as F
import time
import math

class UrbanFlowLatentFlowMatchingRunner(UrbanFlowFlowMatchingRunner):
    def __init__(self, config, model,compression_model, dataset_info):
        super().__init__(config, model,dataset_info)
        self.compression_model = compression_model
        self.compression_model.to(self.accelerator.device)
    
    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_1 = batch[1].to(self.weight_dtype)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
        return latent_data_0,latent_data_1
        
    def visualize_results(self, prediction, ground_truth, previous_value, global_step):
        os.makedirs(os.path.join(self.sample_dir, str(global_step)), exist_ok=True)
        shape = prediction.shape
        height = 128
        width = len(prediction) // height
        prediction = [prediction[i][4] for i in range(shape[0])]
        ground_truth = [ground_truth[i][4] for i in range(shape[0])]
        previous_value = [previous_value[i][4] for i in range(shape[0])]
        for i in range(shape[0]):
            save_path = os.path.join(self.sample_dir, str(global_step), f"visualize_{i}.png")
            self.visualize(prediction[i], ground_truth[i], previous_value[i], save_path)
    
    def log_validation(self, model):
        index = random.randint(0, len(self.val_dataset)-1)
        data_0,data_1,geometry = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
        output = model(latent_data_0).sample
        with torch.no_grad():
            prediction = self.compression_model.decode(output*10).sample
            ground_truth = self.compression_model.decode(latent_data_1*10).sample
            previous_value = self.compression_model.decode(latent_data_0*10).sample
        prediction = prediction.detach().cpu().numpy().squeeze(0)
        ground_truth = ground_truth.detach().cpu().numpy().squeeze(0)
        previous_value = previous_value.detach().cpu().numpy().squeeze(0)
        self.visualize_results(prediction, ground_truth, previous_value,self.global_step)
    
    def setup_model(self):
        self.model.requires_grad_(True)
        if self.cfg.solver.enable_xformers_memory_efficient_attention:
            if is_xformers_available():
                self.model.enable_xformers_memory_efficient_attention()
            else:
                raise ValueError("xformers is not available. Make sure it is installed correctly")
        if self.cfg.solver.gradient_checkpointing:
            self.model.enable_gradient_checkpointing()
        
    def setup_optimizer(self):
        self.trainable_params = list(filter(lambda p: p.requires_grad, self.model.parameters()))
        self.logger.info(f"Total trainable params {len(self.trainable_params)}")
        self.optimizer = torch.optim.AdamW(
            self.trainable_params,
            lr=self.learning_rate,
            betas=(self.cfg.solver.adam_beta1, self.cfg.solver.adam_beta2),
            weight_decay=self.cfg.solver.adam_weight_decay,
            eps=self.cfg.solver.adam_epsilon,
        )
        self.optimizer = self.accelerator.prepare(self.optimizer)


class UrbanFlowLatentFlowMatchingV1Runner(UrbanFlowFlowMatchingRunner):
    def __init__(self, config, model,compression_model,dataset_info):
        super().__init__(config, model,compression_model,dataset_info)

    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0)/10
            latent_data_1 = self.compression_model.encode(data_1)/10
            latent_data_bg = self.compression_model.encode(data_bg)/10
        latent_data_0 = torch.cat([latent_data_0,latent_data_bg],dim=1)
        return latent_data_0,latent_data_1

    def log_validation(self, model):
        index = random.randint(0, len(self.val_dataset)-1)
        data_0,data_bg,data_1,_ = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_bg = data_bg.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0)/10
            latent_data_bg = self.compression_model.encode(data_bg)/10
            latent_data_1 = self.compression_model.encode(data_1)/10
        input_latent = torch.cat([latent_data_0,latent_data_bg],dim=1)
        output = model(input_latent).sample
        with torch.no_grad():
            prediction = self.compression_model.decode(output*10)
            ground_truth = self.compression_model.decode(latent_data_1*10)
            previous_value = self.compression_model.decode(latent_data_0*10)
        prediction = prediction.detach().cpu().numpy().squeeze(0)
        ground_truth = ground_truth.detach().cpu().numpy().squeeze(0)
        previous_value = previous_value.detach().cpu().numpy().squeeze(0)
        self.visualize_results(prediction, ground_truth, previous_value,self.global_step)

class UrbanFlowLatentFlowMatchingV2Runner(UrbanFlowFlowMatchingRunner):
    def __init__(self, config, model,compression_model,dataset_info):
        super().__init__(config, model,compression_model,dataset_info)

    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
            latent_data_bg = self.compression_model.encode(data_bg).latent_dist.sample()/10
        latent_data_0 = torch.cat([latent_data_0,latent_data_bg],dim=1)
        return latent_data_0,latent_data_1

    def log_validation(self, model):
        index = random.randint(0, len(self.val_dataset)-1)
        data_0,data_bg,data_1,_ = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_bg = data_bg.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_bg = self.compression_model.encode(data_bg).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
        input_latent = torch.cat([latent_data_0,latent_data_bg],dim=1)
        output = model(input_latent).sample
        with torch.no_grad():
            prediction = self.compression_model.decode(output*10).sample
            ground_truth = self.compression_model.decode(latent_data_1*10).sample
            previous_value = self.compression_model.decode(latent_data_0*10).sample
        prediction = prediction.detach().cpu().numpy().squeeze(0)
        ground_truth = ground_truth.detach().cpu().numpy().squeeze(0)
        previous_value = previous_value.detach().cpu().numpy().squeeze(0)
        self.visualize_results(prediction, ground_truth, previous_value,self.global_step)