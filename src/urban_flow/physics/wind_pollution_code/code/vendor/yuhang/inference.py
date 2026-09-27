from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import nn

from model import DigitUNet3D


CHANNELS = {
    "digit4wide": (16, 32, 64, 128, 256),
    "unet3d_reduced": (16, 32, 64, 128, 256),
    "digit4full": (32, 64, 128, 256, 512),
    "unet3d_full": (32, 64, 128, 256, 512),
}


class Predictor(nn.Module):
    """Restore a physical concentration field from a trained U-Net."""

    def __init__(self, model: DigitUNet3D, mean: float, std: float, cap: float | None) -> None:
        super().__init__()
        self.model = model
        self.mean = mean
        self.std = std
        self.cap = cap

    def forward(
        self,
        pollution: torch.Tensor,
        boundary: torch.Tensor,
        wind: torch.Tensor,
    ) -> torch.Tensor:
        device = next(self.model.parameters()).device
        pollution = pollution.to(device=device, dtype=torch.float32)
        boundary = boundary.to(device=device, dtype=torch.float32)
        wind = wind.to(device=device, dtype=torch.float32)
        if self.cap is not None:
            pollution = pollution.clamp(0, self.cap)
        prediction = self.model(pollution, boundary, wind).float() * self.std + self.mean
        return prediction.clamp(0, self.cap) if self.cap is not None else prediction.clamp_min(0)


def load_predictor(checkpoint_path: str | Path, device: str = "cpu") -> Predictor:
    """Load the architecture and preprocessing values stored in a checkpoint."""

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    config = checkpoint["config"]
    architecture = config["architecture"]
    if architecture not in CHANNELS:
        raise ValueError(f"unsupported architecture: {architecture}")
    stats = config["stats"]
    meta = config.get("stats_meta", {})
    cap = float(meta["clip_value"]) if meta.get("clip_target") is True else None
    model = DigitUNet3D(CHANNELS[architecture])
    model.load_state_dict(checkpoint["model"])
    predictor = Predictor(model, float(stats["mean"]), float(stats["std"]), cap)
    return predictor.to(device).eval().requires_grad_(False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one C(t) to C(t+50) U-Net step.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True, help="Torch file with pollution, boundary, and wind tensors")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    inputs = torch.load(args.input, map_location="cpu", weights_only=True)
    predictor = load_predictor(args.checkpoint, args.device)
    with torch.inference_mode():
        prediction = predictor(inputs["pollution"], inputs["boundary"], inputs["wind"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(prediction.cpu(), args.output)


if __name__ == "__main__":
    main()
