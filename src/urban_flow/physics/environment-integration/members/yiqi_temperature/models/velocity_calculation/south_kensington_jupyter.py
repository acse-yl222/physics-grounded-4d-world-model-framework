from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np
import torch
import torch.nn as nn

try:
    import matplotlib.animation as mpl_animation
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as MplPath
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    MATPLOTLIB_AVAILABLE = True
except ModuleNotFoundError:
    mpl_animation = None
    plt = None
    MplPath = None
    MATPLOTLIB_AVAILABLE = False

try:
    from IPython.display import HTML
except ModuleNotFoundError:
    HTML = None


BUNDLE_ROOT = Path(__file__).resolve().parent
ASSET_ROOT = BUNDLE_ROOT / "assets"


@dataclass
class SouthKensingtonConfig:
    static_dir: str = str(ASSET_ROOT / "data" / "imperial_10m" / "static")
    raw_buildings_path: str = str(
        ASSET_ROOT / "data" / "imperial_10m" / "raw" / "osm_buildings.json"
    )
    artifact_dir: str = str(ASSET_ROOT / "models" / "digit_v1")
    geometry_resolution_m: float = 2.0
    model_resolution_m: float = 4.0
    target_xy: tuple[int, int] | None = None
    z_dim: int = 24
    height_scale_m: float = 3.0
    input_shape: tuple[int, int, int, int, int] | None = None
    embed_pad_y: int = 32
    embed_pad_x: int = 32
    embed_z_start: int = 0
    inlet_flow: float = 0.25
    timesteppings: int = 100
    num_iterations: int = 5
    boundary_size: int = 1
    time_levels: tuple[int, int, int, int, int] = (0, 20, 45, 70, 95)
    slice_indices: tuple[int, int, int] = (1, 4, 20)
    animation_slice_idx: int = 4
    animation_slice_indices: tuple[int, int, int] = (1, 4, 20)
    animation_stride: int = 4
    velocity_scale_min: float = -4.0
    velocity_scale_max: float = 4.0
    output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_digit")


class UNet_New(nn.Module):
    def __init__(
        self,
        dim: int = 2,
        input_channels: int = 6,
        output_channels: int = 2,
        num_levels: int = 4,
        base_channels: int = 32,
        activation_final: nn.Module | None = None,
        if_norm: bool = False,
        if_maxpool: bool = True,
    ) -> None:
        super().__init__()
        self.if_norm = if_norm
        self.if_maxpool = if_maxpool
        self.num_levels = num_levels
        self.base_channels = base_channels

        if dim == 3:
            self.Conv = nn.Conv3d
            self.ConvTranspose = nn.ConvTranspose3d
            self.MaxPool = nn.MaxPool3d
        elif dim == 1:
            self.Conv = nn.Conv1d
            self.ConvTranspose = nn.ConvTranspose1d
            self.MaxPool = nn.MaxPool1d
        else:
            self.Conv = nn.Conv2d
            self.ConvTranspose = nn.ConvTranspose2d
            self.MaxPool = nn.MaxPool2d

        self.encoder_blocks = nn.ModuleList()
        self.decoder_blocks = nn.ModuleList()
        self.upconvs = nn.ModuleList()

        in_ch = input_channels
        for i in range(self.num_levels):
            out_ch = self.base_channels * (2**i)
            self.encoder_blocks.append(self.conv_block(in_ch, out_ch))
            in_ch = out_ch

        self.bottleneck = self.conv_block(in_ch, in_ch * 2)
        in_ch = in_ch * 2
        for i in reversed(range(self.num_levels)):
            out_ch = self.base_channels * (2**i)
            self.upconvs.append(self.ConvTranspose(in_ch, out_ch, kernel_size=2, stride=2))
            self.decoder_blocks.append(self.conv_block(in_ch, out_ch))
            in_ch = in_ch // 2

        self.final_conv = self.Conv(self.base_channels, output_channels, kernel_size=1)
        self.activation = activation_final if activation_final else nn.Identity()

    def conv_block(self, in_channels: int, out_channels: int) -> nn.Sequential:
        return nn.Sequential(
            self.Conv(in_channels, out_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.01),
            self.Conv(out_channels, out_channels, kernel_size=3, padding=1),
            nn.LeakyReLU(negative_slope=0.01),
        )

    def pool(self, x: torch.Tensor) -> torch.Tensor:
        if self.if_maxpool:
            return self.MaxPool(kernel_size=2, stride=2)(x)
        conv_layer = self.Conv(x.size(1), x.size(1), kernel_size=2, stride=2).to(x.device)
        return conv_layer(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        enc_feats = []
        for enc in self.encoder_blocks:
            x = enc(x)
            enc_feats.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)

        for i in range(self.num_levels):
            x = self.upconvs[i](x)
            skip = enc_feats[-(i + 1)]
            x = torch.cat([x, skip], dim=1)
            x = self.decoder_blocks[i](x)

        return self.activation(self.final_conv(x))


def scale_back(u_scaled: torch.Tensor, u_min: float, u_max: float) -> torch.Tensor:
    u_middle = (u_min + u_max) / 2.0
    return u_middle + 0.5 * u_scaled * (u_max - u_min)


def compute_velocity_magnitude_3d(velocity_data: np.ndarray) -> np.ndarray:
    u = velocity_data[:, 0, ...]
    v = velocity_data[:, 1, ...]
    w = velocity_data[:, 2, ...]
    return np.sqrt(u**2 + v**2 + w**2)


def ceil_to_multiple(value: int, divisor: int) -> int:
    return int(math.ceil(value / divisor) * divisor)


def resize_nearest_2d(array: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    src_h, src_w = array.shape
    dst_h, dst_w = target_shape
    row_idx = np.clip(np.round(np.linspace(0, src_h - 1, dst_h)).astype(int), 0, src_h - 1)
    col_idx = np.clip(np.round(np.linspace(0, src_w - 1, dst_w)).astype(int), 0, src_w - 1)
    return array[np.ix_(row_idx, col_idx)]


def block_reduce_max(array: np.ndarray, block_shape: tuple[int, int]) -> np.ndarray:
    block_y, block_x = block_shape
    src_y, src_x = array.shape
    pad_y = (-src_y) % block_y
    pad_x = (-src_x) % block_x
    if pad_y or pad_x:
        array = np.pad(array, ((0, pad_y), (0, pad_x)), mode="edge")
    new_y = array.shape[0] // block_y
    new_x = array.shape[1] // block_x
    return array.reshape(new_y, block_y, new_x, block_x).max(axis=(1, 3))


def parse_height_from_tags(tags: dict[str, str], default_height_m: float = 12.0) -> float:
    height_value = tags.get("height")
    if height_value:
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+", str(height_value))
        if match:
            parsed = float(match.group())
            if parsed > 0:
                return parsed

    levels_value = tags.get("building:levels")
    if levels_value:
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+", str(levels_value))
        if match:
            parsed = float(match.group())
            if parsed > 0:
                return parsed * 3.0

    return default_height_m


def infer_target_shape(grid: dict[str, object], resolution_m: float) -> tuple[int, int]:
    west, south, east, north = grid["bounds"]
    width = int(round((east - west) / resolution_m))
    height = int(round((north - south) / resolution_m))
    return height, width


def rasterize_buildings_from_osm(
    raw_buildings_path: str | Path,
    grid: dict[str, object],
    resolution_m: float,
    default_height_m: float = 12.0,
) -> tuple[np.ndarray, np.ndarray]:
    if not MATPLOTLIB_AVAILABLE or MplPath is None:
        raise RuntimeError("Rasterising raw OSM geometry requires matplotlib.")

    raw_path = Path(raw_buildings_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw OSM file not found: {raw_path}")

    osm_payload = json.loads(raw_path.read_text())
    elements = osm_payload.get("elements", [])
    lat_min, lat_max = grid["bbox_wgs84"][1], grid["bbox_wgs84"][3]
    lon_min, lon_max = grid["bbox_wgs84"][0], grid["bbox_wgs84"][2]
    height, width = infer_target_shape(grid, resolution_m)
    yy, xx = np.mgrid[0:height, 0:width]
    mask = np.zeros((height, width), dtype=np.uint8)
    heights = np.zeros((height, width), dtype=np.float32)

    def lon_to_x(lon: float) -> float:
        return ((lon - lon_min) / (lon_max - lon_min)) * (width - 1)

    def lat_to_y(lat: float) -> float:
        return ((lat_max - lat) / (lat_max - lat_min)) * (height - 1)

    for element in elements:
        geometry = element.get("geometry")
        if not geometry or len(geometry) < 3:
            continue

        coords = np.array(
            [[lon_to_x(point["lon"]), lat_to_y(point["lat"])] for point in geometry],
            dtype=np.float32,
        )
        if coords.shape[0] < 3:
            continue
        if not np.allclose(coords[0], coords[-1]):
            coords = np.vstack([coords, coords[0]])

        min_x = max(int(math.floor(coords[:, 0].min())), 0)
        max_x = min(int(math.ceil(coords[:, 0].max())), width - 1)
        min_y = max(int(math.floor(coords[:, 1].min())), 0)
        max_y = min(int(math.ceil(coords[:, 1].max())), height - 1)
        if min_x > max_x or min_y > max_y:
            continue

        patch_points = np.column_stack(
            (
                xx[min_y : max_y + 1, min_x : max_x + 1].ravel() + 0.5,
                yy[min_y : max_y + 1, min_x : max_x + 1].ravel() + 0.5,
            )
        )
        polygon_path = MplPath(coords)
        inside = polygon_path.contains_points(patch_points, radius=0.2).reshape(
            max_y - min_y + 1, max_x - min_x + 1
        )
        if not inside.any():
            continue

        local_mask = mask[min_y : max_y + 1, min_x : max_x + 1]
        local_height = heights[min_y : max_y + 1, min_x : max_x + 1]
        local_mask[inside] = 1
        building_height = parse_height_from_tags(element.get("tags", {}), default_height_m)
        local_height[inside] = np.maximum(local_height[inside], building_height)

    return mask, heights


def load_static_fields(config: SouthKensingtonConfig) -> dict[str, object]:
    static_dir = Path(config.static_dir)
    mask = np.load(static_dir / "building_mask.npy")
    height = np.load(static_dir / "building_height.npy")
    grid = json.loads((static_dir / "grid.json").read_text())
    if mask.shape != height.shape:
        raise ValueError(f"Mask shape {mask.shape} does not match height shape {height.shape}.")
    return {"static_dir": static_dir, "mask": mask, "height": height, "grid": grid}


def prepare_geometry_fields(
    config: SouthKensingtonConfig, static_fields: dict[str, object]
) -> dict[str, np.ndarray]:
    static_mask = static_fields["mask"]
    static_height = static_fields["height"]
    grid = static_fields["grid"]

    geometry_resolution = float(config.geometry_resolution_m)
    raw_path = Path(config.raw_buildings_path)
    if geometry_resolution < float(grid["resolution_m"]) and raw_path.exists():
        geometry_mask, geometry_height = rasterize_buildings_from_osm(
            raw_path, grid, geometry_resolution
        )
        geometry_source = "raw_osm"
    else:
        geometry_mask, geometry_height = static_mask, static_height
        geometry_resolution = float(grid["resolution_m"])
        geometry_source = "static_grid"

    model_resolution = float(config.model_resolution_m)
    if model_resolution < geometry_resolution:
        raise ValueError(
            f"model_resolution_m={model_resolution} cannot be finer than geometry_resolution_m={geometry_resolution}."
        )

    ratio = model_resolution / geometry_resolution
    if abs(ratio - round(ratio)) > 1e-6:
        raise ValueError(
            "model_resolution_m must be an integer multiple of geometry_resolution_m for this bundle."
        )

    factor = int(round(ratio))
    if factor == 1:
        mask_model = (geometry_mask > 0).astype(np.uint8)
        height_model = np.where(mask_model > 0, geometry_height, 0).astype(np.float32)
    else:
        mask_model = block_reduce_max(
            (geometry_mask > 0).astype(np.uint8), (factor, factor)
        ).astype(np.uint8)
        height_model = block_reduce_max(
            np.where(geometry_mask > 0, geometry_height, 0).astype(np.float32), (factor, factor)
        )
        height_model = np.where(mask_model > 0, height_model, 0).astype(np.float32)

    target_xy = config.target_xy or mask_model.shape
    mask_resampled, height_resampled = prepare_2d_geometry(mask_model, height_model, target_xy)
    return {
        "geometry_mask": (geometry_mask > 0).astype(np.uint8),
        "geometry_height": np.where(geometry_mask > 0, geometry_height, 0).astype(np.float32),
        "geometry_source": geometry_source,
        "geometry_resolution_m": np.array([geometry_resolution], dtype=np.float32),
        "mask_model": mask_model,
        "height_model": height_model,
        "mask_resampled": mask_resampled,
        "height_resampled": height_resampled,
    }


def prepare_2d_geometry(
    building_mask: np.ndarray,
    building_height: np.ndarray,
    target_xy: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    mask_binary = (building_mask > 0).astype(np.uint8)
    height_clean = np.where(mask_binary > 0, np.maximum(building_height, 0), 0).astype(np.float32)
    mask_resampled = resize_nearest_2d(mask_binary, target_xy).astype(np.uint8)
    height_resampled = resize_nearest_2d(height_clean, target_xy).astype(np.float32)
    height_resampled = np.where(mask_resampled > 0, height_resampled, 0).astype(np.float32)
    return mask_resampled, height_resampled


def build_voxel_mesh(
    building_mask: np.ndarray,
    building_height: np.ndarray,
    z_dim: int,
    height_scale_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    height_voxels = np.clip(np.rint(building_height / height_scale_m), 0, z_dim).astype(np.int32)
    height_voxels = np.where(building_mask > 0, np.maximum(height_voxels, 1), 0)
    levels = np.arange(z_dim, dtype=np.int32)
    filled = (height_voxels[..., None] > levels) & (building_mask[..., None] > 0)
    return filled.astype(np.uint8)[None, ...], height_voxels


def embed_mesh_in_sigma(
    mesh: np.ndarray, config: SouthKensingtonConfig
) -> tuple[torch.Tensor, torch.Tensor]:
    input_shape = infer_input_shape(mesh, config)
    _, _, nx, ny, nz = input_shape
    mesh_y, mesh_x, mesh_z = mesh.shape[1:]
    free_space_mesh = (1 - torch.tensor(mesh, dtype=torch.float32))[0]
    sigma = torch.ones(input_shape, dtype=torch.float32, device="cpu")
    embed_y_start = config.embed_pad_y
    embed_x_start = config.embed_pad_x
    y_end = embed_y_start + mesh_y
    x_end = embed_x_start + mesh_x
    z_end = config.embed_z_start + mesh_z
    sigma[0, 0, embed_y_start:y_end, embed_x_start:x_end, config.embed_z_start : z_end] = (
        free_space_mesh
    )
    building_distribution = sigma.clone().permute(0, 1, 4, 2, 3)
    building_distribution[0, 0, 0, :, :] = 0
    return sigma, building_distribution


def infer_input_shape(
    mesh: np.ndarray, config: SouthKensingtonConfig
) -> tuple[int, int, int, int, int]:
    if config.input_shape is not None:
        return config.input_shape
    mesh_y, mesh_x, _ = mesh.shape[1:]
    full_y = ceil_to_multiple(mesh_y + 2 * config.embed_pad_y, 8)
    full_x = ceil_to_multiple(mesh_x + 2 * config.embed_pad_x, 8)
    return (1, 1, full_y, full_x, 64)


def load_digit_model(config: SouthKensingtonConfig, device: torch.device) -> UNet_New:
    model = UNet_New(
        dim=3,
        input_channels=10,
        output_channels=3,
        num_levels=3,
        if_maxpool=True,
        activation_final=nn.Tanh(),
    )
    state_dict = torch.load(Path(config.artifact_dir) / "digit.pth", map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def run_digit_rollout(
    predictor: UNet_New,
    building_distribution: torch.Tensor,
    config: SouthKensingtonConfig,
    device: torch.device,
) -> torch.Tensor:
    obs_buildings_batch = building_distribution.float().to(device)
    nz = building_distribution.shape[-3]
    ny = building_distribution.shape[-2]
    nx = building_distribution.shape[-1]

    flow_data = np.zeros((3, nz, ny, nx), dtype=np.float32)
    flow_data[0] = config.inlet_flow * np.ones((nz, ny, nx), dtype=np.float32)
    flow_data_torch = torch.from_numpy(flow_data).float().unsqueeze(0).to(device)

    status_t0_batch = flow_data_torch.clone()
    status_t1_batch = flow_data_torch.clone()
    predictions = []

    for _ in range(config.timesteppings - 2):
        status_t2_current = status_t1_batch
        for _ in range(config.num_iterations):
            b = config.boundary_size
            status_t2_current_wb = status_t2_current

            status_t2_current_wb[:, 0, :, :, :b] = config.inlet_flow
            status_t2_current_wb[:, 0, :, :, -b:] = config.inlet_flow
            status_t2_current_wb[:, 0, :, :b, :] = status_t2_current_wb[:, 0, :, b : b + b, :]
            status_t2_current_wb[:, 0, :, -b:, :] = status_t2_current_wb[:, 0, :, -b - b : -b, :]
            status_t2_current_wb[:, 0, :b, :, :] = 0.0
            status_t2_current_wb[:, 0, -b:, :, :] = status_t2_current_wb[:, 0, -b - b : -b, :, :]

            status_t2_current_wb[:, 1, :, :, :b] = 0.0
            status_t2_current_wb[:, 1, :, :, -b:] = 0.0
            status_t2_current_wb[:, 1, :, :b, :] = 0.0
            status_t2_current_wb[:, 1, :, -b:, :] = 0.0
            status_t2_current_wb[:, 1, :b, :, :] = 0.0
            status_t2_current_wb[:, 1, -b:, :, :] = status_t2_current_wb[:, 1, -b - b : -b, :, :]

            status_t2_current_wb[:, 2, :, :, :b] = 0.0
            status_t2_current_wb[:, 2, :, :, -b:] = 0.0
            status_t2_current_wb[:, 2, :, :b, :] = 0.0
            status_t2_current_wb[:, 2, :, -b:, :] = 0.0
            status_t2_current_wb[:, 2, :b, :, :] = 0.0
            status_t2_current_wb[:, 2, -b:, :, :] = 0.0

            status_t0_batch = status_t0_batch * obs_buildings_batch
            status_t1_batch = status_t1_batch * obs_buildings_batch
            status_t2_current_wb = status_t2_current_wb * obs_buildings_batch

            with torch.no_grad():
                input_wholedomain = torch.cat(
                    (obs_buildings_batch, status_t0_batch, status_t1_batch, status_t2_current_wb),
                    dim=1,
                ).float()
                prediction = predictor(input_wholedomain)

            status_t2_current = prediction
            prediction = prediction * obs_buildings_batch

        predictions.append(prediction.cpu())
        status_t0_batch = status_t1_batch
        status_t1_batch = status_t2_current

    return torch.cat(predictions, dim=0)


def save_summary_and_arrays(
    results: dict[str, object], output_dir: str | Path | None = None
) -> dict[str, object]:
    config: SouthKensingtonConfig = results["config"]
    out_dir = Path(output_dir or config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    np.save(out_dir / "predictions_3d_vel_mag.npy", results["predictions_3d_vel_mag"])
    np.save(out_dir / "mask_resampled.npy", results["mask_resampled"])
    np.save(out_dir / "height_voxels.npy", results["height_voxels"])
    np.save(out_dir / "geometry_mask.npy", results["geometry_mask"])
    np.save(out_dir / "geometry_height.npy", results["geometry_height"])

    summary = {
        "config": asdict(config),
        "grid": results["grid"],
        "device": results["device"],
        "geometry_source": results["geometry_source"],
        "matplotlib_available": MATPLOTLIB_AVAILABLE,
        "velocity_shape": list(results["predictions_3d_vel_mag"].shape),
        "velocity_min": float(results["predictions_3d_vel_mag"].min()),
        "velocity_max": float(results["predictions_3d_vel_mag"].max()),
    }

    if MATPLOTLIB_AVAILABLE:
        geometry_path = save_geometry_preview(
            results["geometry_mask"],
            results["geometry_height"],
            results["height_voxels"],
            out_dir,
            results["geometry_source"],
            float(results["geometry_resolution_m"]),
            float(config.model_resolution_m),
        )
        summary["geometry_preview"] = str(geometry_path)
        summary["slice_paths"] = [
            str(path)
            for path in save_velocity_slices(results["predictions_3d_vel_mag"], config, out_dir)
        ]
        animation_paths = save_velocity_animations(
            results["predictions_3d_vel_mag"], config, out_dir
        )
        summary["animation_paths"] = {key: str(value) for key, value in animation_paths.items()}
    else:
        summary["geometry_preview"] = None
        summary["slice_paths"] = []
        summary["animation_paths"] = {}

    summary_path = out_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return {"summary_path": summary_path, **summary}


def save_geometry_preview(
    mask: np.ndarray,
    height: np.ndarray,
    height_voxels: np.ndarray,
    output_dir: Path,
    geometry_source: str,
    geometry_resolution_m: float,
    model_resolution_m: float,
) -> Path:
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    axs[0].imshow(mask, cmap="gray", origin="upper")
    axs[0].set_title(f"Building Mask ({geometry_resolution_m:.0f} m, {geometry_source})")
    axs[1].imshow(height, cmap="magma", origin="upper")
    axs[1].set_title("Building Height (m)")
    axs[2].imshow(height_voxels, cmap="viridis", origin="upper")
    axs[2].set_title(f"Voxelised Height ({model_resolution_m:.0f} m model)")
    for ax in axs:
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    output_path = output_dir / "south_kensington_geometry.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_velocity_magnitudes_onerow(
    target_magnitude: np.ndarray,
    time_levels: tuple[int, int, int, int, int] | list[int],
    cmap: str = "turbo",
    figsize: tuple[int, int] = (18, 5),
):
    max_idx = target_magnitude.shape[0] - 1
    safe_time_levels = [min(level, max_idx) for level in time_levels]
    fig, axs = plt.subplots(1, 5, figsize=figsize)
    cbar_ax = fig.add_axes([0.92, 0.2, 0.02, 0.6])
    combined_min = target_magnitude.min()
    combined_max = target_magnitude.max()
    for col, time_level in enumerate(safe_time_levels):
        im_true = axs[col].imshow(
            target_magnitude[time_level, :, :],
            cmap=cmap,
            vmin=combined_min,
            vmax=combined_max,
            origin="upper",
        )
        axs[col].set_title(f"Prediction (k={time_level})", fontsize=16)
        axs[col].tick_params(axis="both", labelsize=10)
    cbar = fig.colorbar(im_true, cax=cbar_ax)
    cbar.set_label("Velocity Magnitude", fontsize=14)
    plt.tight_layout(rect=[0, 0, 0.9, 1])
    return fig


def save_velocity_slices(
    predictions_3d_vel_mag: np.ndarray, config: SouthKensingtonConfig, output_dir: Path
) -> list[Path]:
    saved_paths = []
    max_slice = predictions_3d_vel_mag.shape[1] - 1
    max_time = predictions_3d_vel_mag.shape[0] - 1
    safe_time_levels = tuple(min(level, max_time) for level in config.time_levels)
    for slice_idx in config.slice_indices:
        safe_idx = min(slice_idx, max_slice)
        predictions_vel = predictions_3d_vel_mag[: safe_time_levels[-1] + 1, safe_idx, :, :]
        fig = plot_velocity_magnitudes_onerow(predictions_vel, safe_time_levels)
        output_path = output_dir / f"velocity_slice_z{safe_idx:02d}.png"
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        saved_paths.append(output_path)
    return saved_paths


def save_velocity_animation(
    predictions_3d_vel_mag: np.ndarray,
    config: SouthKensingtonConfig,
    output_dir: Path,
) -> dict[str, Path]:
    slice_idx = min(config.animation_slice_idx, predictions_3d_vel_mag.shape[1] - 1)
    frames = predictions_3d_vel_mag[:, slice_idx, :, :]
    frame_indices = list(range(0, frames.shape[0], max(1, config.animation_stride)))
    if frame_indices[-1] != frames.shape[0] - 1:
        frame_indices.append(frames.shape[0] - 1)
    sampled = frames[frame_indices]

    gif_path = output_dir / f"velocity_slice_z{slice_idx:02d}_animation.gif"
    html_path = output_dir / f"velocity_slice_z{slice_idx:02d}_animation.html"
    saved: dict[str, Path] = {"html": html_path}

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(sampled[0], vmin=sampled.min(), vmax=sampled.max(), cmap="turbo", origin="upper")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Velocity Magnitude")

    def update(frame_number: int) -> None:
        im.set_array(sampled[frame_number])
        ax.set_title(f"Velocity Magnitude, z={slice_idx}, k={frame_indices[frame_number]}")

    ani = mpl_animation.FuncAnimation(fig, update, frames=len(frame_indices), interval=150)
    html_path.write_text(ani.to_jshtml())

    try:
        writer = mpl_animation.PillowWriter(fps=6)
        ani.save(gif_path, writer=writer)
        saved["gif"] = gif_path
    except Exception:
        pass
    finally:
        plt.close(fig)

    return saved


def save_velocity_animations(
    predictions_3d_vel_mag: np.ndarray,
    config: SouthKensingtonConfig,
    output_dir: Path,
) -> dict[str, Path]:
    saved: dict[str, Path] = {}
    for slice_idx in config.animation_slice_indices:
        animation_config = SouthKensingtonConfig(**asdict(config))
        animation_config.animation_slice_idx = slice_idx
        animation_paths = save_velocity_animation(
            predictions_3d_vel_mag,
            animation_config,
            output_dir,
        )
        for kind, path in animation_paths.items():
            saved[f"z{min(slice_idx, predictions_3d_vel_mag.shape[1] - 1):02d}_{kind}"] = path
    return saved


def run_pipeline(config: SouthKensingtonConfig | None = None) -> dict[str, object]:
    config = config or SouthKensingtonConfig()
    static_fields = load_static_fields(config)
    geometry_fields = prepare_geometry_fields(config, static_fields)
    mask_resampled = geometry_fields["mask_resampled"]
    height_resampled = geometry_fields["height_resampled"]
    mesh, height_voxels = build_voxel_mesh(
        mask_resampled, height_resampled, config.z_dim, config.height_scale_m
    )
    sigma, building_distribution = embed_mesh_in_sigma(mesh, config)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_digit_model(config, device)
    predictions_3d = run_digit_rollout(model, building_distribution, config, device)
    predictions_3d = scale_back(
        predictions_3d, config.velocity_scale_min, config.velocity_scale_max
    )
    predictions_3d_np = predictions_3d.detach().cpu().numpy()
    predictions_3d_vel_mag = compute_velocity_magnitude_3d(predictions_3d_np)

    return {
        "config": config,
        "device": str(device),
        "grid": static_fields["grid"],
        "geometry_source": geometry_fields["geometry_source"],
        "geometry_resolution_m": float(geometry_fields["geometry_resolution_m"][0]),
        "geometry_mask": geometry_fields["geometry_mask"],
        "geometry_height": geometry_fields["geometry_height"],
        "mask_resampled": mask_resampled,
        "height_resampled": height_resampled,
        "height_voxels": height_voxels,
        "mesh": mesh,
        "sigma": sigma,
        "building_distribution": building_distribution,
        "predictions_3d": predictions_3d_np,
        "predictions_3d_vel_mag": predictions_3d_vel_mag,
    }


def show_animation(data: np.ndarray, title: str = "South Kensington Velocity Magnitude") -> object:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        raise RuntimeError("Animation output requires matplotlib and IPython.")
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle(title, fontsize=16)
    im = ax.imshow(data[0], vmin=data.min(), vmax=data.max(), cmap="jet", origin="upper")
    fig.colorbar(im, ax=ax)

    def update(timestep: int) -> None:
        im.set_array(data[timestep])
        ax.set_title(f"Timestep {timestep}")

    indices = np.linspace(0, data.shape[0] - 1, min(30, data.shape[0]), dtype=int)
    ani = mpl_animation.FuncAnimation(fig, update, frames=indices)
    return HTML(ani.to_jshtml())


def show_animation_from_results(results: dict[str, object], slice_idx: int | None = None) -> object:
    chosen_slice = slice_idx if slice_idx is not None else results["config"].animation_slice_idx
    chosen_slice = min(chosen_slice, results["predictions_3d_vel_mag"].shape[1] - 1)
    return show_animation(
        results["predictions_3d_vel_mag"][:, chosen_slice, :, :],
        title=f"South Kensington Velocity Magnitude (z={chosen_slice})",
    )


def extract_embedded_height_voxels(sigma: torch.Tensor | np.ndarray) -> np.ndarray:
    sigma_array = (
        sigma.detach().cpu().numpy() if isinstance(sigma, torch.Tensor) else np.asarray(sigma)
    )
    if sigma_array.ndim != 5:
        raise ValueError(f"Expected sigma with 5 dimensions, got shape {sigma_array.shape}.")
    free_space = sigma_array[0, 0]
    occupied = free_space < 0.5
    return occupied.sum(axis=-1).astype(np.int32)


def align_height_voxels_to_volume(
    height_voxels: np.ndarray,
    volume_shape_yx: tuple[int, int],
    embed_offset: tuple[int, int] | None = None,
) -> np.ndarray:
    target_y, target_x = volume_shape_yx
    src_y, src_x = height_voxels.shape
    if (src_y, src_x) == (target_y, target_x):
        return height_voxels.astype(np.int32)

    aligned = np.zeros((target_y, target_x), dtype=np.int32)
    if src_y <= target_y and src_x <= target_x:
        if embed_offset is None:
            offset_y = max((target_y - src_y) // 2, 0)
            offset_x = max((target_x - src_x) // 2, 0)
        else:
            offset_y = min(max(int(embed_offset[0]), 0), max(target_y - src_y, 0))
            offset_x = min(max(int(embed_offset[1]), 0), max(target_x - src_x, 0))
        aligned[offset_y : offset_y + src_y, offset_x : offset_x + src_x] = height_voxels.astype(
            np.int32
        )
        return aligned

    return resize_nearest_2d(height_voxels.astype(np.int32), (target_y, target_x)).astype(np.int32)


def plot_3d_velocity_volume(
    predictions_3d_vel_mag: np.ndarray,
    height_voxels: np.ndarray,
    timestep_idx: int = -1,
    slice_indices: tuple[int, int, int] | list[int] = (1, 4, 20),
    embed_offset: tuple[int, int] | None = None,
    building_stride: int = 2,
    figsize: tuple[int, int] = (10, 8),
):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("3D plotting requires matplotlib.")

    time_idx = timestep_idx if timestep_idx >= 0 else predictions_3d_vel_mag.shape[0] - 1
    time_idx = min(max(time_idx, 0), predictions_3d_vel_mag.shape[0] - 1)
    volume = predictions_3d_vel_mag[time_idx]
    aligned_height_voxels = align_height_voxels_to_volume(
        np.asarray(height_voxels), volume.shape[1:], embed_offset=embed_offset
    )
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")
    ny, nx = aligned_height_voxels.shape
    y_coords = np.arange(ny)
    x_coords = np.arange(nx)
    xx, yy = np.meshgrid(x_coords, y_coords)

    # Show buildings as a semi-transparent top surface so the urban form is readable.
    sampled_heights = aligned_height_voxels[::building_stride, ::building_stride].astype(float)
    sampled_heights[sampled_heights <= 0] = np.nan
    sampled_xx = xx[::building_stride, ::building_stride]
    sampled_yy = yy[::building_stride, ::building_stride]
    ax.plot_surface(
        sampled_xx,
        sampled_yy,
        sampled_heights,
        color="#8F99A8",
        alpha=0.28,
        linewidth=0,
        antialiased=False,
        shade=True,
    )

    cmap = plt.get_cmap("turbo")
    norm = plt.Normalize(vmin=float(volume.min()), vmax=float(volume.max()))
    safe_slices = [min(max(int(idx), 0), volume.shape[0] - 1) for idx in slice_indices]
    for slice_idx in safe_slices:
        slice_values = volume[slice_idx]
        facecolors = cmap(norm(slice_values))
        facecolors[..., 3] = np.where(aligned_height_voxels >= slice_idx, 0.0, 0.84)
        z_plane = np.full_like(slice_values, float(slice_idx), dtype=float)
        ax.plot_surface(
            xx,
            yy,
            z_plane,
            rstride=4,
            cstride=4,
            facecolors=facecolors,
            shade=False,
            linewidth=0,
            antialiased=False,
        )

    mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, ax=ax, shrink=0.7, pad=0.08)
    cbar.set_label("Velocity Magnitude")

    ax.set_title(
        f"3D Velocity Slices with Building Geometry (timestep k={time_idx})",
        fontsize=15,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.view_init(elev=28, azim=-56)
    ax.set_xlim(0, nx - 1)
    ax.set_ylim(ny - 1, 0)
    ax.set_zlim(
        0,
        max(
            volume.shape[0] - 1,
            int(np.nanmax(aligned_height_voxels)) if np.any(aligned_height_voxels > 0) else 1,
        ),
    )
    ax.set_box_aspect((nx, ny, max(volume.shape[0], 1) * 1.1))
    ax.invert_yaxis()
    ax.grid(False)
    ax.xaxis.pane.set_alpha(0.04)
    ax.yaxis.pane.set_alpha(0.04)
    ax.zaxis.pane.set_alpha(0.04)
    fig.tight_layout()
    return fig


def save_3d_velocity_view(
    results: dict[str, object],
    timestep_idx: int = -1,
    slice_indices: tuple[int, int, int] | list[int] = (1, 4, 20),
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> Path:
    config: SouthKensingtonConfig = results["config"]
    out_dir = Path(output_dir or config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    time_idx = timestep_idx if timestep_idx >= 0 else results["predictions_3d_vel_mag"].shape[0] - 1
    safe_time = min(max(time_idx, 0), results["predictions_3d_vel_mag"].shape[0] - 1)
    embedded_height_voxels = extract_embedded_height_voxels(results["sigma"])
    fig = plot_3d_velocity_volume(
        results["predictions_3d_vel_mag"],
        embedded_height_voxels,
        timestep_idx=safe_time,
        slice_indices=slice_indices,
        embed_offset=(config.embed_pad_y, config.embed_pad_x),
    )
    output_path = out_dir / (filename or f"velocity_3d_k{safe_time:03d}.png")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path
