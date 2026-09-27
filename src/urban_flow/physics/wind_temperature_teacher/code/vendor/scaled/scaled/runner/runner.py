from accelerate import Accelerator
from accelerate.utils import DistributedDataParallelKwargs
from accelerate.logging import get_logger
import logging
import transformers
import diffusers
from ..utils.util import seed_everything
import os
import torch
from diffusers.utils.import_utils import is_xformers_available
import math
from datetime import datetime
import os.path as osp
from collections import OrderedDict

class Runner:
    def __init__(self,config,model,dataset_info):
        self.cfg = config
        self.model = model
        self.accelerator = self.initial_accelerator()
        self.logger = self.set_logger()
        self.set_seed()
        self.setup_directory()
        self.setup_model()
        self.setup_dataset(**dataset_info)
        self.setup_learning_rate()
        self.setup_optimizer()
        (
        self.model,
        self.optimizer,
        self.train_dataloader,
        ) = self.accelerator.prepare(
            self.model,
            self.optimizer,
            self.train_dataloader,
        )
        self.setup_initial_training()
        self.load_checkpoint()

    def set_seed(self):
        if self.cfg.seed is not None:
            seed_everything(self.cfg.seed)

    def set_logger(self):
        logger = get_logger(__name__, log_level="INFO")
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%m/%d/%Y %H:%M:%S",
            level=logging.INFO,
        )
        logger.info("Logger initialized")
        return logger

    def initial_accelerator(self):
        kwargs = DistributedDataParallelKwargs(find_unused_parameters=False)
        accelerator = Accelerator(
            gradient_accumulation_steps=self.cfg.solver.gradient_accumulation_steps,
            mixed_precision=self.cfg.solver.mixed_precision,
            kwargs_handlers=[kwargs],
        )
        if accelerator.is_local_main_process:
            transformers.utils.logging.set_verbosity_warning()
            diffusers.utils.logging.set_verbosity_info()
        else:
            transformers.utils.logging.set_verbosity_error()
            diffusers.utils.logging.set_verbosity_error()
        return accelerator
    
    def setup_directory(self):
        exp_name = self.cfg.exp_name
        self.save_dir = f"{self.cfg.output_dir}/{exp_name}"
        if self.accelerator.is_main_process:
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir)
        self.sample_dir = os.path.join(self.save_dir, 'samples')
        if self.accelerator.is_main_process and not os.path.exists(self.sample_dir):
            os.makedirs(self.sample_dir)
        if self.cfg.weight_dtype == "fp16":
            self.weight_dtype = torch.float16
        elif self.cfg.weight_dtype == "fp32":
            self.weight_dtype = torch.float32
        else:
            raise ValueError(
                f"Do not support weight dtype: {self.cfg.weight_dtype} during training"
            )
            
    
    def setup_learning_rate(self):
        # Initialize the learning rate
        if self.cfg.solver.scale_lr:
            self.learning_rate = (
                    self.cfg.solver.learning_rate
                    * self.cfg.solver.gradient_accumulation_steps
                    * self.cfg.train_bs
                    * self.accelerator.num_processes
            )
        else:
            self.learning_rate = self.cfg.solver.learning_rate

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
        
    def setup_dataset(self,train_dataset,val_dataset,collate_fn=None):
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        if collate_fn is None:
            self.train_dataloader = torch.utils.data.DataLoader(
                self.train_dataset,
                shuffle=True,
                batch_size=self.cfg.train_bs,
                num_workers=self.cfg.num_workers,
            )
        else:
            self.train_dataloader = torch.utils.data.DataLoader(
                self.train_dataset,
                shuffle=True,
                batch_size=self.cfg.train_bs,
                num_workers=self.cfg.num_workers,
                collate_fn=collate_fn,
            )
        
    def setup_model(self):
        self.model.requires_grad_(True)
        if self.cfg.solver.enable_xformers_memory_efficient_attention:
            if is_xformers_available():
                self.model.enable_xformers_memory_efficient_attention()
            else:
                raise ValueError(
                    "xformers is not available. Make sure it is installed correctly"
                )
        if self.cfg.solver.gradient_checkpointing:
            self.model.enable_gradient_checkpointing()
            
    def setup_initial_training(self):
        # We need to recalculate our total training steps as the size of the training dataloader may have changed.
        num_update_steps_per_epoch = math.ceil(
            len(self.train_dataloader) / self.cfg.solver.gradient_accumulation_steps
        )
        # Afterwards we recalculate our number of training epochs
        self.num_train_epochs = math.ceil(
            self.cfg.solver.max_train_steps / num_update_steps_per_epoch
        )
        # We need to initialize the trackers we use, and also store our configuration.
        # The trackers initializes automatically on the main process.
        if self.accelerator.is_main_process:
            run_time = datetime.now().strftime("%Y%m%d-%H%M")
            self.accelerator.init_trackers(self.cfg.exp_name,)

        # Train!
        total_batch_size = (
                self.cfg.train_bs
                * self.accelerator.num_processes
                * self.cfg.solver.gradient_accumulation_steps
        )
        self.logger.info("***** Running training *****")
        self.logger.info(f"  Num examples = {len(self.train_dataset)}")
        self.logger.info(f"  Num Epochs = {self.num_train_epochs}")
        self.logger.info(f"  Instantaneous batch size per device = {self.cfg.train_bs}")
        self.logger.info(f"  Total train batch size (w. parallel, distributed & accumulation) = {total_batch_size}")
        self.logger.info(f"  Gradient Accumulation steps = {self.cfg.solver.gradient_accumulation_steps}")
        self.logger.info(f"  Total optimization steps = {self.cfg.solver.max_train_steps}")
        self.global_step = 0
        self.first_epoch = 0
        
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
            path = dirs[-1]
            weight = torch.load(os.path.join(resume_dir, path),map_location='cpu')
            self.model.load_state_dict(weight,strict=False)
            self.accelerator.print(f"Resuming from checkpoint {path}")
            self.global_step = int(path.split("-")[1][:-4])

            self.first_epoch = self.global_step // num_update_steps_per_epoch
            self.resume_step =self.global_step % num_update_steps_per_epoch
            
    def save_checkpoint(self,model, save_dir, prefix, ckpt_num, total_limit=None):
        save_path = osp.join(save_dir, f"{prefix}-{ckpt_num}.pth")

        if total_limit is not None:
            checkpoints = os.listdir(save_dir)
            checkpoints = [d for d in checkpoints if d.startswith(prefix)]
            checkpoints = sorted(
                checkpoints, key=lambda x: int(x.split("-")[1].split(".")[0])
            )

            if len(checkpoints) >= total_limit:
                num_to_remove = len(checkpoints) - total_limit + 1
                removing_checkpoints = checkpoints[0:num_to_remove]
                self.logger.info(
                    f"{len(checkpoints)} checkpoints already exist, removing {len(removing_checkpoints)} checkpoints"
                )
                self.logger.info(f"removing checkpoints: {', '.join(removing_checkpoints)}")
                for removing_checkpoint in removing_checkpoints:
                    removing_checkpoint = os.path.join(save_dir, removing_checkpoint)
                    os.remove(removing_checkpoint)

        mm_state_dict = OrderedDict()
        state_dict = model.state_dict()
        for key in state_dict:
            mm_state_dict[key] = state_dict[key]
        torch.save(mm_state_dict, save_path)

    def run(self):
        pass