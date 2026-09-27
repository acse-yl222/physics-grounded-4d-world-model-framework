import random
import torch
import os
from diffusers.utils.import_utils import is_xformers_available
import os
from .urbanflow_regression_runner import UrbanFlowRegressionRunner
from tqdm import tqdm
import torch.nn.functional as F
import time
import math

class UrbanFlowLatentRegressionRunner(UrbanFlowRegressionRunner):
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

class UrbanFlowLatentRegressionGeometryRunner(UrbanFlowLatentRegressionRunner):
    def __init__(self, config, model,compression_model,geometry_model,dataset_info):
        super().__init__(config, model,compression_model,dataset_info)
        self.geometry_model = geometry_model
        self.geometry_model.to(self.accelerator.device)
        self.setup_optimizer_1()

    def setup_optimizer_1(self):
        self.trainable_params0 = list(filter(lambda p: p.requires_grad, self.model.parameters()))
        self.trainable_params1 = list(filter(lambda p: p.requires_grad, self.geometry_model.parameters()))

        self.logger.info(f"Total trainable params {len(self.trainable_params)}")
        self.optimizer = torch.optim.AdamW(
            self.trainable_params0+self.trainable_params1,
            lr=self.learning_rate,
            betas=(self.cfg.solver.adam_beta1, self.cfg.solver.adam_beta2),
            weight_decay=self.cfg.solver.adam_weight_decay,
            eps=self.cfg.solver.adam_epsilon,
        )
        self.optimizer = self.accelerator.prepare(self.optimizer)

    def log_validation(self, model,geometry_model):
        index = random.randint(0, len(self.val_dataset)-1)
        data_0,data_1,geometry = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        geometry = geometry.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
            latent_geometry = geometry_model(geometry)
        output = model(latent_data_0,control_feature=latent_geometry).sample
        with torch.no_grad():
            prediction = self.compression_model.decode(output*10).sample
            ground_truth = self.compression_model.decode(latent_data_1*10).sample
            previous_value = self.compression_model.decode(latent_data_0*10).sample
        prediction = prediction.detach().cpu().numpy().squeeze(0)
        ground_truth = ground_truth.detach().cpu().numpy().squeeze(0)
        previous_value = previous_value.detach().cpu().numpy().squeeze(0)
        self.visualize_results(prediction, ground_truth, previous_value,self.global_step)

    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_1 = batch[1].to(self.weight_dtype)
        geometry = batch[2].to(self.weight_dtype)
        with torch.no_grad():
            latent_data_0 = self.compression_model.encode(data_0).latent_dist.sample()/10
            latent_data_1 = self.compression_model.encode(data_1).latent_dist.sample()/10
            geometry_latent = self.geometry_model(geometry)
        return latent_data_0,latent_data_1,geometry_latent
    
    def load_checkpoint(self):
        # We need to recalculate our total training steps as the size of the training dataloader may have changed.
        num_update_steps_per_epoch = math.ceil(len(self.train_dataloader) / self.cfg.solver.gradient_accumulation_steps)
        # Afterwards we recalculate our number of training epochs
        num_train_epochs = math.ceil(self.cfg.solver.max_train_steps / num_update_steps_per_epoch)
        # Potentially load in the weights and states from a previous save
        if self.cfg.resume_from_checkpoint:
            if self.cfg.resume_from_checkpoint != "latest":
                resume_dir = self.cfg.resume_from_checkpoint
            else:
                resume_dir = self.save_dir
            # Get the most recent checkpoint
            dirs_ = os.listdir(resume_dir)
            dirs = [d for d in dirs_ if d.startswith("model")]
            dirs = sorted(dirs, key=lambda x: int(x.split("-")[1][:-4]))
            if len(dirs)!=0:
                path = dirs[-1]
                weight = torch.load(os.path.join(resume_dir, path),map_location='cpu')
                self.model.load_state_dict(weight,strict=False)

            dirs = [d for d in dirs_ if d.startswith("gemetry_model")]
            dirs = sorted(dirs, key=lambda x: int(x.split("-")[1][:-4]))
            if len(dirs)!=0:
                path = dirs[-1]
                weight = torch.load(os.path.join(resume_dir, path),map_location='cpu')
                self.geometry_model.load_state_dict(weight,strict=False)

            self.accelerator.print(f"Resuming from checkpoint {path}")
            self.global_step = int(path.split("-")[1][:-4])

            self.first_epoch = self.global_step // num_update_steps_per_epoch
            self.resume_step =self.global_step % num_update_steps_per_epoch
        
    def run(self,):
        progress_bar = tqdm(
            range(self.cfg.solver.max_train_steps),
            disable=not self.accelerator.is_local_main_process,
        )
        progress_bar.set_description("Steps")
        progress_bar.update(self.global_step)
        for epoch in range(self.first_epoch, self.num_train_epochs):
            train_loss = 0.0
            t_data_start = time.time()
            for step, batch in enumerate(self.train_dataloader):
                t_data = time.time() - t_data_start
                with self.accelerator.accumulate(self.model):
                    input_variable, target,geometry = self.prepare_input(batch)
                    model_pred = self.model(input_variable,control_feature=geometry).sample
                    loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")
                    avg_loss = self.accelerator.gather(loss.repeat(self.cfg.train_bs)).mean()
                    train_loss += avg_loss.item() / self.cfg.solver.gradient_accumulation_steps
                    self.accelerator.backward(loss)
                    if self.accelerator.sync_gradients:
                        self.accelerator.clip_grad_norm_(self.trainable_params,self.cfg.solver.max_grad_norm)
                    self.optimizer.step()
                    self.optimizer.zero_grad()

                if self.accelerator.sync_gradients:
                    progress_bar.update(1)
                    self.global_step += 1
                    self.accelerator.log({"train_loss": train_loss}, step=self.global_step)
                    train_loss = 0.0
                    if (self.global_step % self.cfg.val.validation_steps == 0) or (self.global_step in self.cfg.val.validation_steps_tuple):
                        if self.accelerator.is_main_process:
                            unwrap_model = self.accelerator.unwrap_model(self.model)
                            unwrap_geometry_model = self.accelerator.unwrap_model(self.geometry_model)
                            self.save_checkpoint(unwrap_model,self.save_dir,"model",self.global_step,total_limit=4)
                            self.save_checkpoint(unwrap_geometry_model,self.save_dir,"geometry_model",self.global_step,total_limit=4)
                            self.log_validation(unwrap_model,unwrap_geometry_model)
                            
                logs = {"step_loss": loss.detach().item(),"lr": self.learning_rate,"td": f"{t_data:.2f}s",}
                t_data_start = time.time()
                progress_bar.set_postfix(**logs)
                if self.global_step >= self.cfg.solver.max_train_steps:
                    break
            self.accelerator.wait_for_everyone()


class UrbanFlowLatentRegressionV1Runner(UrbanFlowLatentRegressionRunner):
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

class UrbanFlowLatentRegressionV2Runner(UrbanFlowLatentRegressionRunner):
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

class UrbanFlowLatentRegressionV1RunnerStage2(UrbanFlowLatentRegressionV1Runner):
    def __init__(self, config, model,compression_model,dataset_info):
        super().__init__(config, model,compression_model,dataset_info)
    
    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        b,c,d,h,w = data_1.shape
        ratio = 0.5
        halo_ratio = random.random()*0.08
        randon_number = random.random()
        halo_type_choice = random.random()
        if randon_number>ratio:
            if halo_type_choice>0.5:
                data_bg_c = data_1.clone()
                halo_size = int(halo_ratio*h)
                if halo_size==0:
                    halo_size=1
                data_bg_c[:,:,:,halo_size:-halo_size,halo_size:-halo_size] = data_bg[:,:,:,halo_size:-halo_size,halo_size:-halo_size]
                data_bg = data_bg_c
                with torch.no_grad():
                    latent_data_0 = self.compression_model.encode(data_0)/10
                    latent_data_1 = self.compression_model.encode(data_1)/10
                    latent_data_bg = self.compression_model.encode(data_bg)/10
            else:
                latent_h = h//4
                halo_size = int(halo_ratio*latent_h)
                if halo_size==0:
                    halo_size=1
                with torch.no_grad():
                    latent_data_0 = self.compression_model.encode(data_0)/10
                    latent_data_1 = self.compression_model.encode(data_1)/10
                    latent_data_bg = self.compression_model.encode(data_bg)/10
                latent_data_bg_c = latent_data_1.clone()
                latent_data_bg_c[:,:,:,halo_size:-halo_size,halo_size:-halo_size] = latent_data_bg[:,:,:,halo_size:-halo_size,halo_size:-halo_size]
                latent_data_bg = latent_data_bg_c
        else:
            with torch.no_grad():
                    latent_data_0 = self.compression_model.encode(data_0)/10
                    latent_data_1 = self.compression_model.encode(data_1)/10
                    latent_data_bg = self.compression_model.encode(data_bg)/10
        latent_data_0 = torch.cat([latent_data_0,latent_data_bg],dim=1)
        return latent_data_0,latent_data_1

    def log_validation(self, model):
        index = random.randint(0, len(self.val_dataset) - 1)
        data_0, data_bg, data_1, _ = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_bg = data_bg.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        b, c, d, h, w = data_1.shape

        # 使用一致的随机策略进行 halo 替换
        halo_ratio = random.random() * 0.08
        randon_number = random.random()
        halo_type_choice = random.random()

        if randon_number > 0.1:
            if halo_type_choice > 0.9:
                # Physical space halo replacement
                halo_size = max(int(halo_ratio * h), 1)
                data_bg_c = data_1.clone()
                data_bg_c[:, :, :, halo_size:-halo_size, halo_size:-halo_size] = data_bg[:, :, :, halo_size:-halo_size, halo_size:-halo_size]
                data_bg = data_bg_c
                with torch.no_grad():
                    latent_data_0 = self.compression_model.encode(data_0) / 10
                    latent_data_1 = self.compression_model.encode(data_1) / 10
                    latent_data_bg = self.compression_model.encode(data_bg) / 10
            else:
                # Latent space halo replacement
                latent_h = h // 4
                halo_size = max(int(halo_ratio * latent_h), 1)
                with torch.no_grad():
                    latent_data_0 = self.compression_model.encode(data_0) / 10
                    latent_data_1 = self.compression_model.encode(data_1) / 10
                    latent_data_bg = self.compression_model.encode(data_bg) / 10
                latent_data_bg_c = latent_data_1.clone()
                latent_data_bg_c[:, :, :, halo_size:-halo_size, halo_size:-halo_size] = latent_data_bg[:, :, :, halo_size:-halo_size, halo_size:-halo_size]
                latent_data_bg = latent_data_bg_c
        else:
            # No halo augmentation
            with torch.no_grad():
                latent_data_0 = self.compression_model.encode(data_0) / 10
                latent_data_1 = self.compression_model.encode(data_1) / 10
                latent_data_bg = self.compression_model.encode(data_bg) / 10

        input_latent = torch.cat([latent_data_0, latent_data_bg], dim=1)
        output = model(input_latent).sample

        with torch.no_grad():
            prediction = self.compression_model.decode(output * 10)
            ground_truth = self.compression_model.decode(latent_data_1 * 10)
            previous_value = self.compression_model.decode(latent_data_0 * 10)

        prediction = prediction.detach().cpu().numpy().squeeze(0)
        ground_truth = ground_truth.detach().cpu().numpy().squeeze(0)
        previous_value = previous_value.detach().cpu().numpy().squeeze(0)

        self.visualize_results(prediction, ground_truth, previous_value, self.global_step)