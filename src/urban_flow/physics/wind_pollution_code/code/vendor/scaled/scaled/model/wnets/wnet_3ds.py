import torch
import torch.nn as nn
from ..unets.unet_3ds import UNet3DsModel
from typing import Optional, Tuple, Union
from diffusers.models.modeling_utils import ModelMixin

class WNET3DsModel(ModelMixin):
    def __init__(self, 
                    in_channels, 
                    out_channels,
                    down_block_types: Tuple[str, ...] = ("DownBlock3D", "AttnDownBlock3D", "AttnDownBlock3D", "AttnDownBlock3D"),
                    up_block_types: Tuple[str, ...] = ("AttnUpBlock3D", "AttnUpBlock3D", "AttnUpBlock3D", "UpBlock3D"),
                    block_out_channels=(64, 128, 192, 256),
                    add_attention: bool = True,
                    ):
        super().__init__()
        self.out_channels = out_channels
        self.unet1 = UNet3DsModel(
            in_channels=in_channels,
            out_channels=in_channels*3,
            down_block_types=down_block_types,
            up_block_types=up_block_types,
            block_out_channels=block_out_channels,
            add_attention=add_attention,
        )
        self.unet2 = UNet3DsModel(
            in_channels=in_channels*3,
            out_channels=out_channels,
            down_block_types=down_block_types,
            up_block_types=up_block_types,
            block_out_channels=block_out_channels,
            add_attention=add_attention,
        )
    
    def forward(self,
        sample: torch.Tensor,
        timestep: Union[torch.Tensor, float, int],
        class_labels: Optional[torch.Tensor] = None,
        return_dict: bool = True,
        ) -> torch.Tensor:
        x1 = self.unet1(
            sample=sample,
            timestep=timestep,
            class_labels=class_labels,
            return_dict=True,
        ).sample
        x2 = self.unet2(
            sample=x1,
            timestep=timestep,
            class_labels=class_labels,
            return_dict=return_dict,
        )
        return x2
    