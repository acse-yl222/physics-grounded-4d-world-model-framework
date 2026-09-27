from __future__ import annotations
import torch
from torch import nn

class ConvBlock3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        groups = min(8, out_channels)
        while out_channels % groups != 0 and groups > 1:
            groups -= 1
        self.block = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.SiLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)

class UNet3D(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int = 1,
        base_channels: int = 24,
        depth: int = 3,
        upsample_mode: str = "trilinear",
    ):
        super().__init__()
        if depth < 1:
            raise ValueError("depth must be at least 1.")

        channels = [base_channels * (2**idx) for idx in range(depth + 1)]
        self.encoders = nn.ModuleList()
        prev_channels = in_channels
        for channels_out in channels:
            self.encoders.append(ConvBlock3D(prev_channels, channels_out))
            prev_channels = channels_out

        self.pool = nn.MaxPool3d(kernel_size=2)
        self.upsample_mode = upsample_mode
        self.upconvs = nn.ModuleList()
        self.decoders = nn.ModuleList()
        for idx in range(depth - 1, -1, -1):
            if upsample_mode == "transpose":
                self.upconvs.append(nn.ConvTranspose3d(channels[idx + 1], channels[idx], kernel_size=2, stride=2))
            elif upsample_mode == "trilinear":
                self.upconvs.append(
                    nn.Sequential(
                        nn.Upsample(scale_factor=2, mode="trilinear", align_corners=False),
                        nn.Conv3d(channels[idx + 1], channels[idx], kernel_size=1),
                    )
                )
            else:
                raise ValueError("upsample_mode must be 'trilinear' or 'transpose'.")
            self.decoders.append(ConvBlock3D(channels[idx] * 2, channels[idx]))

        self.out = nn.Conv3d(base_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for encoder in self.encoders[:-1]:
            x = encoder(x)
            skips.append(x)
            x = self.pool(x)
        x = self.encoders[-1](x)

        for upconv, decoder, skip in zip(self.upconvs, self.decoders, reversed(skips)):
            x = upconv(x)
            x = self._match_shape(x, skip)
            x = torch.cat([skip, x], dim=1)
            x = decoder(x)
        return self.out(x)

    @staticmethod
    def _match_shape(x: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        dz = reference.shape[-3] - x.shape[-3]
        dy = reference.shape[-2] - x.shape[-2]
        dx = reference.shape[-1] - x.shape[-1]
        if dz == dy == dx == 0:
            return x
        if dz < 0 or dy < 0 or dx < 0:
            x = x[..., : reference.shape[-3], : reference.shape[-2], : reference.shape[-1]]
            dz = reference.shape[-3] - x.shape[-3]
            dy = reference.shape[-2] - x.shape[-2]
            dx = reference.shape[-1] - x.shape[-1]
        return nn.functional.pad(x, [0, dx, 0, dy, 0, dz])
