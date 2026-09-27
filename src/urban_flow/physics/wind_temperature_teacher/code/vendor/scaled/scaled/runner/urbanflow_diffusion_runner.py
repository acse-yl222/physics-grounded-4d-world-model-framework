import random
import torch
from tqdm import tqdm
import time
import os
import torch.nn.functional as F
import numpy as np
from diffusers.utils.import_utils import is_xformers_available
from .runner import Runner
import matplotlib.pyplot as plt
import sys
import os
from diffusers.schedulers.scheduling_ddim import DDIMScheduler
from scaled.common.pipeline.pipline_ddim_scaled_urbanflow import SCALEDUrbanFlowPipeline

def compute_snr(noise_scheduler, timesteps):
    """
    Computes SNR as per
    https://github.com/TiankaiHang/Min-SNR-Diffusion-Training/blob/521b624bd70c67cee4bdf49225915f5945a872e3/guided_diffusion/gaussian_diffusion.py#L847-L849
    """
    alphas_cumprod = noise_scheduler.alphas_cumprod
    sqrt_alphas_cumprod = alphas_cumprod ** 0.5
    sqrt_one_minus_alphas_cumprod = (1.0 - alphas_cumprod) ** 0.5
    sqrt_alphas_cumprod = sqrt_alphas_cumprod.to(device=timesteps.device)[
        timesteps
    ].float()
    while len(sqrt_alphas_cumprod.shape) < len(timesteps.shape):
        sqrt_alphas_cumprod = sqrt_alphas_cumprod[..., None]
    alpha = sqrt_alphas_cumprod.expand(timesteps.shape)
    sqrt_one_minus_alphas_cumprod = sqrt_one_minus_alphas_cumprod.to(
        device=timesteps.device
    )[timesteps].float()
    while len(sqrt_one_minus_alphas_cumprod.shape) < len(timesteps.shape):
        sqrt_one_minus_alphas_cumprod = sqrt_one_minus_alphas_cumprod[..., None]
    sigma = sqrt_one_minus_alphas_cumprod.expand(timesteps.shape)
    snr = (alpha / sigma) ** 2
    return snr

class UrbanflowDiffusionRunner(Runner):
    def __init__(self, config, model,dataset_info=None):
        super().__init__(config, model,dataset_info)
        self.scheduler = DDIMScheduler(
                num_train_timesteps=1000,
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                steps_offset=1,
                clip_sample=False,
                rescale_betas_zero_snr=True,
                timestep_spacing="trailing",
                prediction_type="v_prediction",
        )
    
    def visualize(self, prediction, ground_truth, previous_value,save_path):
        prediction = prediction[4]
        ground_truth = ground_truth[4]
        previous_value = previous_value[4]
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
            im = ax.imshow(images[i],vmin=-0.8, vmax=3)
            ax.set_title(titles[i])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        for i in range(3):
            ax = axes[1, i]
            im = ax.imshow(images[i+3],vmin=0, vmax=0.2)
            ax.set_title(titles[i+3])
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        plt.tight_layout()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close(fig)
    
    def visualize_results(self, prediction, ground_truth, previous_value, global_step):
        os.makedirs(os.path.join(self.sample_dir,str(global_step)), exist_ok=True)
        for i in range(3):
            save_path = os.path.join(self.sample_dir,str(global_step),f"visualize_{i}.png")
            self.visualize(prediction[i], ground_truth[i], previous_value[i],save_path)
    
    def log_validation(self,model):
        self.logger.info("Running validation... ")
        if self.generator is None:
            self.generator = torch.manual_seed(42)
        dataset_len = len(self.val_dataset)
        sample_idx = [random.randint(0, dataset_len) for _ in range(1)]
        pipe = SCALEDUrbanFlowPipeline(
            model,
            scheduler=self.scheduler,
        )
        pipe = pipe.to(self.accelerator.device)
        ori_data,bg_data,gt_result,_ = self.val_dataset[sample_idx[0]] # condition （9x32x32x32） gt_result (9x32x32x32)

        previous_value = ori_data.unsqueeze(0).to('cuda')
        next_value = gt_result.unsqueeze(0).to('cuda')
        bg_data = bg_data.unsqueeze(0).to('cuda')

        input_latent = torch.cat([previous_value, bg_data], dim=1)

        pre = pipe(
            input_latent,
            num_inference_steps=25,
            guidance_scale=0,
            generator=self.generator,
            return_dict=False,
        )
        pre_velocity = pre.detach().cpu().numpy()[0]
        previous_velocity = previous_value.detach().cpu().numpy()[0]
        gt_velocity = next_value.detach().cpu().numpy()[0]
        del pipe
        self.visualize_results(pre_velocity,gt_velocity,previous_velocity,self.global_step)
        
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

    def prepare_input(self, batch):
        data_0 = batch[0].to(self.weight_dtype)
        data_bg = batch[1].to(self.weight_dtype)
        data_1 = batch[2].to(self.weight_dtype)
        return data_0,data_bg,data_1
        
    def run(self,):
        self.generator = torch.Generator(device=self.accelerator.device)
        self.generator.manual_seed(self.cfg.seed)
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
                    data_0,data_bg,data_1 = self.prepare_input(batch)
                    noise = torch.randn_like(data_1)

                    if self.cfg.noise_offset > 0:
                        noise += self.cfg.noise_offset * torch.randn(
                            (data_0.shape[0], data_0.shape[1], 1, 1, 1),
                            device=data_0.device,
                        )
                    bsz = data_0.shape[0]
                    timesteps = torch.randint(
                        0,
                        self.scheduler.num_train_timesteps,
                        (bsz,),
                        device=data_0.device,
                    )
                    timesteps = timesteps.long()
                    noisy_latents = self.scheduler.add_noise(data_1, noise, timesteps)
                    input_latent = torch.cat([data_0,data_bg,noisy_latents], dim=1)  # [B, 2+2, D//8,  H//8, W//8]
                    if self.scheduler.prediction_type == "epsilon":
                        target = noise
                    elif self.scheduler.prediction_type == "v_prediction":
                        target = self.scheduler.get_velocity(
                            data_1, noise, timesteps
                        )
                    elif self.scheduler.prediction_type == "sample":
                        target = data_1
                    else:
                        raise ValueError(
                            f"Unknown prediction type {self.scheduler.prediction_type}"
                        )

                    # ---- Forward!!! -----
                    # import pdb;pdb.set_trace()
                    model_pred = self.model(
                        input_latent,
                        timesteps
                    ).sample

                    if self.cfg.snr_gamma == 0:
                        loss = F.mse_loss(
                            model_pred.float(), target.float(), reduction="mean"
                        )
                    else:
                        snr = compute_snr(self.scheduler, timesteps)
                        if self.scheduler.config.prediction_type == "v_prediction":
                            # Velocity objective requires that we add one to SNR values before we divide by them.
                            snr = snr + 1
                        mse_loss_weights = (
                                torch.stack(
                                    [snr, self.cfg.snr_gamma * torch.ones_like(timesteps)], dim=1
                                ).min(dim=1)[0]
                                / snr
                        )
                        loss = F.mse_loss(
                            model_pred.float(), target.float(), reduction="none"
                        )
                        loss = (
                                loss.mean(dim=list(range(1, len(loss.shape))))
                                * mse_loss_weights
                        )
                        loss = loss.mean()

                    # Gather the losses across all processes for logging (if we use distributed training).
                    avg_loss = self.accelerator.gather(loss.repeat(self.cfg.train_bs)).mean()
                    train_loss += avg_loss.item() / self.cfg.solver.gradient_accumulation_steps

                    # Backpropagate
                    self.accelerator.backward(loss)
                    if self.accelerator.sync_gradients:
                        self.accelerator.clip_grad_norm_(
                            self.trainable_params,
                            self.cfg.solver.max_grad_norm,
                        )
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
                            self.save_checkpoint(
                                unwrap_net,
                                self.save_dir,
                                "model",
                                self.global_step,
                                total_limit=4,
                            )
                            self.log_validation(unwrap_net)
                            

                logs = {
                    "step_loss": loss.detach().item(),
                    "lr": self.learning_rate,
                    "td": f"{t_data:.2f}s",
                }
                t_data_start = time.time()
                progress_bar.set_postfix(**logs)
                if self.global_step >= self.cfg.solver.max_train_steps:
                    break
            # save model after each epoch
            # Create the pipeline using the trained modules and save it.
            self.accelerator.wait_for_everyone()