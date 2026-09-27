from omegaconf import OmegaConf
import random
import torch
from tqdm import tqdm
import time
import os
import torch.nn.functional as F
import torch.nn as nn
import numpy as np
from diffusers.utils.import_utils import is_xformers_available
from .runner import Runner
import matplotlib.pyplot as plt
from ..toolkit.flowpastcylinder_dataprocess import interpolate_2D
import sys
import os

class FPCRegressionRunner(Runner):
    def __init__(self, config, model, dataset_info):
        super().__init__(config, model,dataset_info)
    
    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        input_variable = torch.cat([data_0, data_bg], dim=1)
        target = data_1[:, 2:, :].float()
        return input_variable, target
    
    def visualize(self, prediction, ground_truth, previous_value, points, save_path):
        prediction = interpolate_2D(points, prediction, x_number=2200, y_number=410)
        ground_truth = interpolate_2D(points, ground_truth, x_number=2200, y_number=410)
        previous_value = interpolate_2D(points, previous_value, x_number=2200, y_number=410)
        diff_pre_gt = np.abs(prediction - ground_truth)
        diff_pre_previous = np.abs(prediction - previous_value)
        diff_gt_previous = np.abs(ground_truth - previous_value)
        fig, axes = plt.subplots(2, 3, figsize=(12, 8))
        titles = [
            'Prediction',
            'Ground Truth',
            'Previous Value',
            'Diff Prediction - GT',
            'Diff Prediction - Previous Value',
            'Diff GT - Previous Value'
        ]
        images = [
            prediction, ground_truth, previous_value,
            diff_pre_gt, diff_pre_previous, diff_gt_previous
        ]
        for i in range(3):
            ax = axes[0, i]
            im = ax.imshow(images[i], vmin=-0.8, vmax=3)
            ax.set_title(titles[i])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        for i in range(3):
            ax = axes[1, i]
            im = ax.imshow(images[i + 3], vmin=0, vmax=0.2)
            ax.set_title(titles[i + 3])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        plt.close(fig)
        
    
    def visualize_results(self, prediction, ground_truth, previous_value, points, global_step):
        os.makedirs(os.path.join(self.sample_dir, str(global_step)), exist_ok=True)
        shape = prediction.shape
        height = 128
        width = len(prediction) // height
        prediction = [prediction[:, i] for i in range(shape[1])]
        ground_truth = [ground_truth[:, i] for i in range(shape[1])]
        previous_value = [previous_value[:, i] for i in range(shape[1])]
        for i in range(shape[1]):
            save_path = os.path.join(self.sample_dir, str(global_step), f"visualize_{i}.png")
            self.visualize(prediction[i], ground_truth[i], previous_value[i], points, save_path)
    
    def log_validation(self, model):
        # Implement your validation logic here
        index = random.randint(0, len(self.val_dataset)-1)
        data_0,data_bg,data_1 = self.val_dataset[index]
        
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        back_data = data_bg.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        input_variable = torch.cat([data_0, back_data], dim=1)
        output = model(input_variable)
        
        ## data post process
        prediction = output.detach().cpu().numpy().squeeze(0).transpose(1,0)
        ground_truth = data_1.detach().cpu().numpy().squeeze(0).transpose(1,0)[:, 2:]
        previous_value = data_0.detach().cpu().numpy().squeeze(0).transpose(1,0)[:, 2:]
        points = data_0.detach().cpu().numpy().squeeze(0).transpose(1,0)[:, 0:2]
        result = {
            "prediction": prediction,
            "ground_truth": ground_truth,
            "previous_value": previous_value,
            "points" : points
        }
        self.visualize_results(prediction, ground_truth, previous_value,points,self.global_step)
    
    def setup_model(self):
        self.model.backbone.requires_grad_(True)
        self.model.processor1.requires_grad_(False)
        self.model.processor2.requires_grad_(False)
        if self.cfg.solver.enable_xformers_memory_efficient_attention:
            if is_xformers_available():
                self.model.enable_xformers_memory_efficient_attention()
            else:
                raise ValueError("xformers is not available. Make sure it is installed correctly")
        if self.cfg.solver.gradient_checkpointing:
            self.model.enable_gradient_checkpointing()
        
    def setup_optimizer(self):
        self.trainable_params = list(filter(lambda p: p.requires_grad, self.model.backbone.parameters()))
        self.logger.info(f"Total trainable params {len(self.trainable_params)}")
        self.optimizer = torch.optim.AdamW(
            self.trainable_params,
            lr=self.learning_rate,
            betas=(self.cfg.solver.adam_beta1, self.cfg.solver.adam_beta2),
            weight_decay=self.cfg.solver.adam_weight_decay,
            eps=self.cfg.solver.adam_epsilon,
        )
        self.optimizer = self.accelerator.prepare(self.optimizer)
        
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
                    input_variable, target = self.prepare_input(batch)
                    model_pred = self.model(input_variable)
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
                            unwrap_net = self.accelerator.unwrap_model(self.model)
                            self.save_checkpoint(unwrap_net,self.save_dir,"model",self.global_step,total_limit=4)
                            model = self.accelerator.unwrap_model(self.model)
                            self.log_validation(model)
                            
                logs = {"step_loss": loss.detach().item(),"lr": self.learning_rate,"td": f"{t_data:.2f}s",}
                t_data_start = time.time()
                progress_bar.set_postfix(**logs)
                if self.global_step >= self.cfg.solver.max_train_steps:
                    break
            self.accelerator.wait_for_everyone()
            
import wandb

class FPCRegressionRunnerWandb(Runner):
    def __init__(self, config, model, dataset_info):
        super().__init__(config, model, dataset_info)
        if self.accelerator.is_main_process and self.cfg.get("wandb", {}).get("enable", True):
            wandb.init(
                project=self.cfg.wandb.project,
                name=self.cfg.wandb.name,
                config=OmegaConf.to_container(self.cfg, resolve=True),
                mode="online"
            )

    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        input_variable = torch.cat([data_0, data_bg], dim=1)
        target = data_1[:, 2:, :].float()
        return input_variable, target

    def visualize(self, prediction, ground_truth, previous_value, points, save_path):
        prediction = interpolate_2D(points, prediction, x_number=2200, y_number=410)
        ground_truth = interpolate_2D(points, ground_truth, x_number=2200, y_number=410)
        previous_value = interpolate_2D(points, previous_value, x_number=2200, y_number=410)
        diff_pre_gt = np.abs(prediction - ground_truth)
        diff_pre_previous = np.abs(prediction - previous_value)
        diff_gt_previous = np.abs(ground_truth - previous_value)
        fig, axes = plt.subplots(2, 3, figsize=(12, 8))
        titles = [
            'Prediction',
            'Ground Truth',
            'Previous Value',
            'Diff Prediction - GT',
            'Diff Prediction - Previous Value',
            'Diff GT - Previous Value'
        ]
        images = [
            prediction, ground_truth, previous_value,
            diff_pre_gt, diff_pre_previous, diff_gt_previous
        ]
        for i in range(3):
            ax = axes[0, i]
            im = ax.imshow(images[i], vmin=-0.8, vmax=3)
            ax.set_title(titles[i])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        for i in range(3):
            ax = axes[1, i]
            im = ax.imshow(images[i + 3], vmin=0, vmax=0.2)
            ax.set_title(titles[i + 3])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        plt.close(fig)
        return save_path  # ✅ 返回路径用于 wandb.Image

    def visualize_results(self, prediction, ground_truth, previous_value, points, global_step):
        os.makedirs(os.path.join(self.sample_dir, str(global_step)), exist_ok=True)
        shape = prediction.shape
        height = 128
        width = len(prediction) // height
        prediction = [prediction[:, i] for i in range(shape[1])]
        ground_truth = [ground_truth[:, i] for i in range(shape[1])]
        previous_value = [previous_value[:, i] for i in range(shape[1])]
        for i in range(shape[1]):
            save_path = os.path.join(self.sample_dir, str(global_step), f"visualize_{i}.png")
            img_path = self.visualize(prediction[i], ground_truth[i], previous_value[i], points, save_path)
            # if self.accelerator.is_main_process:
            #     wandb.log({f"image/step{global_step}_field{i}": wandb.Image(img_path)}, step=global_step)

    def log_validation(self, model):
        index = random.randint(0, len(self.val_dataset) - 1)
        data_0, data_bg, data_1 = self.val_dataset[index]
        data_0 = data_0.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        data_1 = data_1.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        back_data = data_bg.to(self.weight_dtype).to(self.accelerator.device).unsqueeze(0)
        input_variable = torch.cat([data_0, back_data], dim=1)
        output = model(input_variable)

        prediction = output.detach().cpu().numpy().squeeze(0).transpose(1, 0)
        ground_truth = data_1.detach().cpu().numpy().squeeze(0).transpose(1, 0)[:, 2:]
        previous_value = data_0.detach().cpu().numpy().squeeze(0).transpose(1, 0)[:, 2:]
        points = data_0.detach().cpu().numpy().squeeze(0).transpose(1, 0)[:, 0:2]
        self.visualize_results(prediction, ground_truth, previous_value, points, self.global_step)

    def setup_model(self):
        self.model.backbone.requires_grad_(True)
        self.model.processor1.requires_grad_(False)
        self.model.processor2.requires_grad_(False)
        if self.cfg.solver.enable_xformers_memory_efficient_attention:
            if is_xformers_available():
                self.model.enable_xformers_memory_efficient_attention()
            else:
                raise ValueError("xformers is not available. Make sure it is installed correctly")
        if self.cfg.solver.gradient_checkpointing:
            self.model.enable_gradient_checkpointing()

    def setup_optimizer(self):
        self.trainable_params = list(filter(lambda p: p.requires_grad, self.model.backbone.parameters()))
        self.logger.info(f"Total trainable params {len(self.trainable_params)}")
        self.optimizer = torch.optim.AdamW(
            self.trainable_params,
            lr=self.learning_rate,
            betas=(self.cfg.solver.adam_beta1, self.cfg.solver.adam_beta2),
            weight_decay=self.cfg.solver.adam_weight_decay,
            eps=self.cfg.solver.adam_epsilon,
        )
        self.optimizer = self.accelerator.prepare(self.optimizer)

    def loss_construction(self, model_pred, target,fx):
        loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")
        return loss

    def run(self, ):
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
                    input_variable, target = self.prepare_input(batch)
                    model_pred = self.model(input_variable)
                    points = input_variable[:, :2, :] # Bx2xN
                    loss = self.loss_construction(model_pred, target, points)
                    # loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")
                    avg_loss = self.accelerator.gather(loss.repeat(self.cfg.train_bs)).mean()
                    train_loss += avg_loss.item() / self.cfg.solver.gradient_accumulation_steps
                    self.accelerator.backward(loss)
                    if self.accelerator.sync_gradients:
                        self.accelerator.clip_grad_norm_(self.trainable_params, self.cfg.solver.max_grad_norm)
                    self.optimizer.step()
                    self.optimizer.zero_grad()

                if self.accelerator.sync_gradients:
                    progress_bar.update(1)
                    self.global_step += 1
                    if self.accelerator.is_main_process:
                        wandb.log({"train/loss": train_loss}, step=self.global_step)
                    train_loss = 0.0
                    if (self.global_step % self.cfg.val.validation_steps == 0) or (self.global_step in self.cfg.val.validation_steps_tuple):
                        if self.accelerator.is_main_process:
                            unwrap_net = self.accelerator.unwrap_model(self.model)
                            self.save_checkpoint(unwrap_net, self.save_dir, "model", self.global_step, total_limit=4)
                            self.log_validation(unwrap_net)

                logs = {
                    "step/loss": loss.detach().item(),
                    "step/lr": self.learning_rate,
                    "step/td": t_data
                }
                if self.accelerator.is_main_process:
                    wandb.log(logs, step=self.global_step)
                t_data_start = time.time()
                progress_bar.set_postfix(**logs)
                if self.global_step >= self.cfg.solver.max_train_steps:
                    break
            self.accelerator.wait_for_everyone()
        if self.accelerator.is_main_process:
            wandb.finish()
