from __future__ import annotations

import torch
from torch import nn


class Smooth3D(nn.Module):
    """Two convolutions used after a scale change."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        groups = _groups(out_channels)
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.GroupNorm(groups, out_channels),
            nn.LeakyReLU(0.1, inplace=True),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.net(value)


class Down3D(nn.Module):
    """Downsample and smooth one encoder level."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.scale = nn.Conv3d(in_channels, out_channels, kernel_size=3, stride=2, padding=1)
        self.smooth = Smooth3D(out_channels, out_channels)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.smooth(self.scale(value))


class Up3D(nn.Module):
    """Upsample and merge one decoder level."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.scale = nn.ConvTranspose3d(in_channels, out_channels, kernel_size=2, stride=2)
        self.smooth = Smooth3D(2 * out_channels, out_channels)

    def forward(self, value: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        return self.smooth(torch.cat((self.scale(value), skip), dim=1))


class DigitUNet3D(nn.Module):
    """Four-level 3D U-Net with quarter-resolution wind conditioning."""

    def __init__(self, channels: tuple[int, ...], out_channels: int = 1) -> None:
        super().__init__()
        if len(channels) < 4 or any(value < 1 for value in channels):
            raise ValueError("channels must define at least four positive levels")
        if out_channels not in (1, 2):
            raise ValueError("out_channels must be one or two")
        self.channels = channels
        self.first = Smooth3D(3, channels[0])
        self.down = nn.ModuleList(
            Down3D(channels[index - 1], channels[index])
            for index in range(1, len(channels))
        )
        self.wind_proj = nn.Conv3d(4, 16, kernel_size=1)
        self.wind_smooth = Smooth3D(channels[2] + 16, channels[2])
        self.up = nn.ModuleList(
            Up3D(channels[index], channels[index - 1])
            for index in range(len(channels) - 1, 0, -1)
        )
        self.head = nn.Conv3d(channels[0], out_channels, kernel_size=1)

    def forward(
        self,
        pollution: torch.Tensor,
        boundary: torch.Tensor,
        wind: torch.Tensor,
    ) -> torch.Tensor:
        if pollution.ndim != 5 or pollution.shape[1] != 1:
            raise ValueError("pollution must have one channel")
        if boundary.ndim != 5 or boundary.shape[1] != 2:
            raise ValueError("boundary must contain geometry and source")
        if pollution.shape[0] != boundary.shape[0] or pollution.shape[-3:] != boundary.shape[-3:]:
            raise ValueError("pollution and boundary shapes must match")

        value = self.first(torch.cat((pollution, boundary), dim=1))
        skips = [value]
        for index, layer in enumerate(self.down, start=1):
            value = layer(value)
            if index == 2:
                if wind.ndim != 5 or wind.shape[0] != value.shape[0] or wind.shape[-3:] != value.shape[-3:]:
                    raise ValueError("wind latent must match the quarter-resolution encoder field")
                if wind.shape[1] != 4:
                    raise ValueError("wind latent must have four channels")
                value = self.wind_smooth(torch.cat((value, self.wind_proj(wind)), dim=1))
            skips.append(value)

        for layer, skip in zip(self.up, reversed(skips[:-1])):
            value = layer(value, skip)
        return self.head(value)


def _groups(channels: int) -> int:
    for groups in (8, 4, 2):
        if channels % groups == 0:
            return groups
    return 1
