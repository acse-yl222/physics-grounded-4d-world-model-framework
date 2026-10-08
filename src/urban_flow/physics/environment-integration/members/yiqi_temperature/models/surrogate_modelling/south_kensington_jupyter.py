"""Shared geometry/plotting helpers retained for temperature workflows.
DIGIT network and inference implementation were removed at user request.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from contextlib import nullcontext
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np
import torch

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
    raw_buildings_path: str = str(ASSET_ROOT / "data" / "imperial_10m" / "raw" / "osm_buildings.json")
    artifact_dir: str = str(ASSET_ROOT / "models" / "digit_v1")
    geometry_resolution_m: float = 2.0
    geometry_rotation_deg: int = 0
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
    use_mixed_precision: bool = True
    output_dir: str = str(BUNDLE_ROOT / "outputs" / "south_kensington_digit")




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
    row_idx = np.clip(
        np.round(np.linspace(0, src_h - 1, dst_h)).astype(int), 0, src_h - 1
    )
    col_idx = np.clip(
        np.round(np.linspace(0, src_w - 1, dst_w)).astype(int), 0, src_w - 1
    )
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


def rotation_quarter_turns(rotation_deg: int | float) -> int:
    rotation_deg = int(round(float(rotation_deg))) % 360
    if rotation_deg % 90 != 0:
        raise ValueError("geometry_rotation_deg must be a multiple of 90 for interpolation-free rotation.")
    return (rotation_deg // 90) % 4


def rotate_2d_field(field: np.ndarray, rotation_deg: int | float) -> np.ndarray:
    turns = rotation_quarter_turns(rotation_deg)
    if turns == 0:
        return field
    return np.rot90(field, k=turns).copy()


def prepare_geometry_fields(config: SouthKensingtonConfig, static_fields: dict[str, object]) -> dict[str, np.ndarray]:
    static_mask = static_fields["mask"]
    static_height = static_fields["height"]
    grid = static_fields["grid"]

    geometry_resolution = float(config.geometry_resolution_m)
    raw_path = Path(config.raw_buildings_path)
    if geometry_resolution < float(grid["resolution_m"]) and raw_path.exists():
        geometry_mask, geometry_height = rasterize_buildings_from_osm(raw_path, grid, geometry_resolution)
        geometry_source = "raw_osm"
    else:
        geometry_mask, geometry_height = static_mask, static_height
        geometry_resolution = float(grid["resolution_m"])
        geometry_source = "static_grid"

    rotation_deg = int(getattr(config, "geometry_rotation_deg", 0))
    if rotation_deg % 360:
        geometry_mask = rotate_2d_field(geometry_mask, rotation_deg)
        geometry_height = rotate_2d_field(geometry_height, rotation_deg)
        geometry_source = f"{geometry_source}_rot{rotation_deg % 360:03d}"

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
        mask_model = block_reduce_max((geometry_mask > 0).astype(np.uint8), (factor, factor)).astype(np.uint8)
        height_model = block_reduce_max(np.where(geometry_mask > 0, geometry_height, 0).astype(np.float32), (factor, factor))
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
    height_clean = np.where(mask_binary > 0, np.maximum(building_height, 0), 0).astype(
        np.float32
    )
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


def embed_mesh_in_sigma(mesh: np.ndarray, config: SouthKensingtonConfig) -> tuple[torch.Tensor, torch.Tensor]:
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
    sigma[0, 0, embed_y_start:y_end, embed_x_start:x_end, config.embed_z_start:z_end] = free_space_mesh
    building_distribution = sigma.clone().permute(0, 1, 4, 2, 3)
    building_distribution[0, 0, 0, :, :] = 0
    return sigma, building_distribution


def infer_input_shape(mesh: np.ndarray, config: SouthKensingtonConfig) -> tuple[int, int, int, int, int]:
    if config.input_shape is not None:
        return config.input_shape
    mesh_y, mesh_x, _ = mesh.shape[1:]
    full_y = ceil_to_multiple(mesh_y + 2 * config.embed_pad_y, 8)
    full_x = ceil_to_multiple(mesh_x + 2 * config.embed_pad_x, 8)
    return (1, 1, full_y, full_x, 64)


def load_digit_model(*args, **kwargs):
    """Removed DIGIT backend; retained only to report a clear legacy-call error."""
    raise RuntimeError("DIGIT wind model was removed. Supply precomputed wind to the temperature workflow; no replacement wind model is selected automatically.")


def run_digit_rollout(*args, **kwargs):
    """Removed DIGIT backend; retained only to report a clear legacy-call error."""
    raise RuntimeError("DIGIT wind model was removed. Supply precomputed wind to the temperature workflow; no replacement wind model is selected automatically.")


def save_summary_and_arrays(results: dict[str, object], output_dir: str | Path | None = None) -> dict[str, object]:
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
        summary["slice_paths"] = [str(path) for path in save_velocity_slices(results["predictions_3d_vel_mag"], config, out_dir)]
        animation_paths = save_velocity_animations(results["predictions_3d_vel_mag"], config, out_dir)
        summary["animation_paths"] = {key: str(value) for key, value in animation_paths.items()}
        vertical_animation_paths = save_vertical_velocity_section_animation(results, output_dir=out_dir)
        summary["vertical_section_animation_paths"] = {
            key: str(value) for key, value in vertical_animation_paths.items()
        }
        summary["flow_3d_path"] = str(
            save_3d_velocity_field_view(results, timestep_idx=-1, output_dir=out_dir)
        )
    else:
        summary["geometry_preview"] = None
        summary["slice_paths"] = []
        summary["animation_paths"] = {}
        summary["vertical_section_animation_paths"] = {}
        summary["flow_3d_path"] = None

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


def save_velocity_slices(predictions_3d_vel_mag: np.ndarray, config: SouthKensingtonConfig, output_dir: Path) -> list[Path]:
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


def run_pipeline(*args, **kwargs):
    """Removed DIGIT backend; retained only to report a clear legacy-call error."""
    raise RuntimeError("DIGIT wind model was removed. Supply precomputed wind to the temperature workflow; no replacement wind model is selected automatically.")


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
    sigma_array = sigma.detach().cpu().numpy() if isinstance(sigma, torch.Tensor) else np.asarray(sigma)
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
        aligned[offset_y : offset_y + src_y, offset_x : offset_x + src_x] = height_voxels.astype(np.int32)
        return aligned

    return resize_nearest_2d(height_voxels.astype(np.int32), (target_y, target_x)).astype(np.int32)


def plot_vertical_velocity_section(
    predictions_3d_vel_mag: np.ndarray,
    height_voxels: np.ndarray,
    timestep_idx: int = 0,
    section_y_idx: int | None = None,
    embed_offset: tuple[int, int] | None = None,
    cmap: str = "jet",
    figsize: tuple[int, int] = (12, 7),
):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("Vertical section plotting requires matplotlib.")
    if predictions_3d_vel_mag.ndim != 4:
        raise ValueError(
            f"Expected predictions_3d_vel_mag shaped as (time, z, y, x), got {predictions_3d_vel_mag.shape}."
        )

    time_idx = timestep_idx if timestep_idx >= 0 else predictions_3d_vel_mag.shape[0] - 1
    time_idx = min(max(time_idx, 0), predictions_3d_vel_mag.shape[0] - 1)
    volume = np.asarray(predictions_3d_vel_mag[time_idx], dtype=np.float32)
    aligned_height_voxels = align_height_voxels_to_volume(
        np.asarray(height_voxels), volume.shape[1:], embed_offset=embed_offset
    )

    safe_section_y = section_y_idx if section_y_idx is not None else volume.shape[1] // 2
    safe_section_y = min(max(int(safe_section_y), 0), volume.shape[1] - 1)
    section = volume[:, safe_section_y, :].copy()

    building_heights_x = aligned_height_voxels[safe_section_y].astype(np.int32)
    z_coords = np.arange(section.shape[0], dtype=np.int32)[:, None]
    solid_mask = z_coords < building_heights_x[None, :]
    section[solid_mask] = 0.0

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(
        section,
        cmap=cmap,
        vmin=float(predictions_3d_vel_mag.min()),
        vmax=float(predictions_3d_vel_mag.max()),
        origin="lower",
        aspect="auto",
        interpolation="nearest",
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Velocity Magnitude")

    x = np.arange(section.shape[1], dtype=np.float32)
    ax.fill_between(x, 0, building_heights_x, color="#0b0b7a", alpha=0.98, step="mid")

    fig.suptitle("Velocity Magnitude", fontsize=22)
    ax.set_title(f"Timestep {time_idx}", fontsize=18)
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_xlim(0, section.shape[1] - 1)
    ax.set_ylim(0, section.shape[0] - 1)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return fig


def _prepare_vertical_section_frames(
    predictions_3d_vel_mag: np.ndarray,
    height_voxels: np.ndarray,
    section_y_idx: int | None = None,
    embed_offset: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    if predictions_3d_vel_mag.ndim != 4:
        raise ValueError(
            f"Expected predictions_3d_vel_mag shaped as (time, z, y, x), got {predictions_3d_vel_mag.shape}."
        )
    reference_volume = np.asarray(predictions_3d_vel_mag[0], dtype=np.float32)
    aligned_height_voxels = align_height_voxels_to_volume(
        np.asarray(height_voxels), reference_volume.shape[1:], embed_offset=embed_offset
    )
    safe_section_y = section_y_idx if section_y_idx is not None else reference_volume.shape[1] // 2
    safe_section_y = min(max(int(safe_section_y), 0), reference_volume.shape[1] - 1)
    building_heights_x = aligned_height_voxels[safe_section_y].astype(np.int32)
    sections = np.asarray(predictions_3d_vel_mag[:, :, safe_section_y, :], dtype=np.float32).copy()
    z_coords = np.arange(sections.shape[1], dtype=np.int32)[:, None]
    solid_mask = z_coords < building_heights_x[None, :]
    sections[:, solid_mask] = 0.0
    return sections, building_heights_x, safe_section_y


def show_vertical_section_animation_from_results(
    results: dict[str, object],
    section_y_idx: int | None = None,
    stride: int = 4,
    cmap: str = "jet",
) -> object:
    if not MATPLOTLIB_AVAILABLE or HTML is None:
        raise RuntimeError("Animation output requires matplotlib and IPython.")
    config: SouthKensingtonConfig = results["config"]
    embedded_height_voxels = extract_embedded_height_voxels(results["sigma"])
    sections, building_heights_x, safe_section_y = _prepare_vertical_section_frames(
        results["predictions_3d_vel_mag"],
        embedded_height_voxels,
        section_y_idx=section_y_idx,
        embed_offset=(config.embed_pad_y, config.embed_pad_x),
    )
    frame_indices = list(range(0, sections.shape[0], max(1, int(stride))))
    if frame_indices[-1] != sections.shape[0] - 1:
        frame_indices.append(sections.shape[0] - 1)
    sampled = sections[frame_indices]

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(
        sampled[0],
        cmap=cmap,
        vmin=float(results["predictions_3d_vel_mag"].min()),
        vmax=float(results["predictions_3d_vel_mag"].max()),
        origin="lower",
        aspect="auto",
        interpolation="nearest",
    )
    x = np.arange(sampled.shape[2], dtype=np.float32)
    ax.fill_between(x, 0, building_heights_x, color="#0b0b7a", alpha=0.98, step="mid")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Velocity Magnitude")
    fig.suptitle("Vertical Velocity Magnitude Section", fontsize=22)
    ax.set_title(f"Timestep {frame_indices[0]} (y={safe_section_y})", fontsize=18)
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_xlim(0, sampled.shape[2] - 1)
    ax.set_ylim(0, sampled.shape[1] - 1)

    def update(frame_number: int) -> None:
        im.set_array(sampled[frame_number])
        ax.set_title(f"Timestep {frame_indices[frame_number]} (y={safe_section_y})", fontsize=18)

    ani = mpl_animation.FuncAnimation(fig, update, frames=len(frame_indices), interval=150)
    return HTML(ani.to_jshtml())


def save_vertical_velocity_section_animation(
    results: dict[str, object],
    section_y_idx: int | None = None,
    output_dir: str | Path | None = None,
    filename_prefix: str = "velocity_vertical_section",
    stride: int | None = None,
    cmap: str = "jet",
) -> dict[str, Path]:
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("Vertical section plotting requires matplotlib.")
    config: SouthKensingtonConfig = results["config"]
    out_dir = Path(output_dir or config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    embedded_height_voxels = extract_embedded_height_voxels(results["sigma"])
    sections, building_heights_x, safe_section_y = _prepare_vertical_section_frames(
        results["predictions_3d_vel_mag"],
        embedded_height_voxels,
        section_y_idx=section_y_idx,
        embed_offset=(config.embed_pad_y, config.embed_pad_x),
    )
    frame_stride = max(1, int(config.animation_stride if stride is None else stride))
    frame_indices = list(range(0, sections.shape[0], frame_stride))
    if frame_indices[-1] != sections.shape[0] - 1:
        frame_indices.append(sections.shape[0] - 1)
    sampled = sections[frame_indices]

    html_path = out_dir / f"{filename_prefix}_animation.html"
    gif_path = out_dir / f"{filename_prefix}_animation.gif"
    saved: dict[str, Path] = {"html": html_path}

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(
        sampled[0],
        cmap=cmap,
        vmin=float(results["predictions_3d_vel_mag"].min()),
        vmax=float(results["predictions_3d_vel_mag"].max()),
        origin="lower",
        aspect="auto",
        interpolation="nearest",
    )
    x = np.arange(sampled.shape[2], dtype=np.float32)
    ax.fill_between(x, 0, building_heights_x, color="#0b0b7a", alpha=0.98, step="mid")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Velocity Magnitude")
    fig.suptitle("Vertical Velocity Magnitude Section", fontsize=22)

    def update(frame_number: int) -> None:
        im.set_array(sampled[frame_number])
        ax.set_title(f"Timestep {frame_indices[frame_number]} (y={safe_section_y})", fontsize=18)

    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_xlim(0, sampled.shape[2] - 1)
    ax.set_ylim(0, sampled.shape[1] - 1)
    update(0)
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


def sample_3d_velocity_vectors(
    velocity_field: np.ndarray,
    height_voxels: np.ndarray,
    *,
    vector_stride_xy: int = 8,
    vector_stride_z: int = 3,
    min_speed_percentile: float = 70.0,
    max_vectors: int = 900,
) -> dict[str, np.ndarray]:
    if velocity_field.ndim != 4 or velocity_field.shape[0] != 3:
        raise ValueError(
            f"Expected velocity field shaped as (3, z, y, x), got {velocity_field.shape}."
        )

    _, z_dim, y_dim, x_dim = velocity_field.shape
    y_coords = np.arange(0, y_dim, max(1, int(vector_stride_xy)))
    x_coords = np.arange(0, x_dim, max(1, int(vector_stride_xy)))
    z_coords = np.arange(1, z_dim, max(1, int(vector_stride_z)))
    if z_coords.size == 0:
        z_coords = np.array([0], dtype=int)

    zz, yy, xx = np.meshgrid(z_coords, y_coords, x_coords, indexing="ij")
    zz_flat = zz.ravel()
    yy_flat = yy.ravel()
    xx_flat = xx.ravel()

    solid_height = np.asarray(height_voxels, dtype=np.int32)[yy_flat, xx_flat]
    free_space_mask = zz_flat > solid_height
    if not np.any(free_space_mask):
        free_space_mask = zz_flat >= solid_height

    u = velocity_field[0, zz_flat, yy_flat, xx_flat]
    v = velocity_field[1, zz_flat, yy_flat, xx_flat]
    w = velocity_field[2, zz_flat, yy_flat, xx_flat]
    speed = np.sqrt(u**2 + v**2 + w**2)

    if np.any(free_space_mask):
        free_space_speeds = speed[free_space_mask]
        threshold = np.percentile(
            free_space_speeds, float(np.clip(min_speed_percentile, 0.0, 100.0))
        )
        strength_mask = speed >= threshold
        mask = free_space_mask & strength_mask
        if not np.any(mask):
            mask = free_space_mask
    else:
        mask = np.ones_like(speed, dtype=bool)

    selected = np.flatnonzero(mask)
    if selected.size > max_vectors:
        order = np.argsort(speed[selected])[::-1][:max_vectors]
        selected = selected[order]

    return {
        "x": xx_flat[selected].astype(np.float32),
        "y": yy_flat[selected].astype(np.float32),
        "z": zz_flat[selected].astype(np.float32),
        "u": u[selected].astype(np.float32),
        "v": v[selected].astype(np.float32),
        "w": w[selected].astype(np.float32),
        "speed": speed[selected].astype(np.float32),
    }


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


def plot_3d_velocity_field(
    predictions_3d: np.ndarray,
    height_voxels: np.ndarray,
    timestep_idx: int = -1,
    slice_indices: tuple[int, int, int] | list[int] = (1, 4, 20),
    embed_offset: tuple[int, int] | None = None,
    building_stride: int = 2,
    vector_stride_xy: int = 8,
    vector_stride_z: int = 3,
    max_vectors: int = 900,
    min_speed_percentile: float = 70.0,
    vertical_scale: float = 1.8,
    figsize: tuple[int, int] = (12, 9),
):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("3D plotting requires matplotlib.")
    if predictions_3d.ndim != 5 or predictions_3d.shape[1] != 3:
        raise ValueError(
            f"Expected predictions shaped as (time, 3, z, y, x), got {predictions_3d.shape}."
        )

    time_idx = timestep_idx if timestep_idx >= 0 else predictions_3d.shape[0] - 1
    time_idx = min(max(time_idx, 0), predictions_3d.shape[0] - 1)
    velocity_field = np.asarray(predictions_3d[time_idx], dtype=np.float32)
    speed_volume = np.sqrt(np.sum(velocity_field**2, axis=0))
    aligned_height_voxels = align_height_voxels_to_volume(
        np.asarray(height_voxels), speed_volume.shape[1:], embed_offset=embed_offset
    )

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")
    ny, nx = aligned_height_voxels.shape
    y_coords = np.arange(ny)
    x_coords = np.arange(nx)
    xx, yy = np.meshgrid(x_coords, y_coords)

    sampled_heights = aligned_height_voxels[::building_stride, ::building_stride].astype(float)
    sampled_heights[sampled_heights <= 0] = np.nan
    sampled_xx = xx[::building_stride, ::building_stride]
    sampled_yy = yy[::building_stride, ::building_stride]
    ax.plot_surface(
        sampled_xx,
        sampled_yy,
        sampled_heights,
        color="#6B7280",
        alpha=0.30,
        linewidth=0,
        antialiased=False,
        shade=True,
    )

    cmap = plt.get_cmap("turbo")
    norm = plt.Normalize(vmin=float(speed_volume.min()), vmax=float(speed_volume.max()))
    safe_slices = [min(max(int(idx), 0), speed_volume.shape[0] - 1) for idx in slice_indices]
    for slice_idx in safe_slices:
        slice_values = speed_volume[slice_idx]
        facecolors = cmap(norm(slice_values))
        facecolors[..., 3] = np.where(aligned_height_voxels >= slice_idx, 0.0, 0.70)
        z_plane = np.full_like(slice_values, float(slice_idx), dtype=float)
        ax.plot_surface(
            xx,
            yy,
            z_plane,
            rstride=3,
            cstride=3,
            facecolors=facecolors,
            shade=False,
            linewidth=0,
            antialiased=False,
        )

    vectors = sample_3d_velocity_vectors(
        velocity_field,
        aligned_height_voxels,
        vector_stride_xy=vector_stride_xy,
        vector_stride_z=vector_stride_z,
        min_speed_percentile=min_speed_percentile,
        max_vectors=max_vectors,
    )
    if vectors["x"].size:
        colors = cmap(norm(vectors["speed"]))
        ax.quiver(
            vectors["x"],
            vectors["y"],
            vectors["z"],
            vectors["u"],
            vectors["v"],
            vectors["w"] * float(vertical_scale),
            length=2.4,
            normalize=True,
            colors=colors,
            linewidths=0.7,
            arrow_length_ratio=0.35,
            alpha=0.95,
        )

    mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, ax=ax, shrink=0.72, pad=0.08)
    cbar.set_label("Velocity Magnitude")

    ax.set_title(
        f"3D Velocity Field with Height-Resolved Flow (timestep k={time_idx})",
        fontsize=15,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.view_init(elev=27, azim=-58)
    ax.set_xlim(0, nx - 1)
    ax.set_ylim(ny - 1, 0)
    ax.set_zlim(
        0,
        max(
            speed_volume.shape[0] - 1,
            int(np.nanmax(aligned_height_voxels)) if np.any(aligned_height_voxels > 0) else 1,
        ),
    )
    ax.set_box_aspect((nx, ny, max(speed_volume.shape[0], 1) * 1.25))
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


def save_3d_velocity_field_view(
    results: dict[str, object],
    timestep_idx: int = -1,
    slice_indices: tuple[int, int, int] | list[int] = (1, 4, 20),
    output_dir: str | Path | None = None,
    filename: str | None = None,
    vector_stride_xy: int = 8,
    vector_stride_z: int = 3,
    max_vectors: int = 900,
    min_speed_percentile: float = 70.0,
    vertical_scale: float = 1.8,
) -> Path:
    config: SouthKensingtonConfig = results["config"]
    out_dir = Path(output_dir or config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    time_idx = timestep_idx if timestep_idx >= 0 else results["predictions_3d"].shape[0] - 1
    safe_time = min(max(time_idx, 0), results["predictions_3d"].shape[0] - 1)
    embedded_height_voxels = extract_embedded_height_voxels(results["sigma"])
    fig = plot_3d_velocity_field(
        results["predictions_3d"],
        embedded_height_voxels,
        timestep_idx=safe_time,
        slice_indices=slice_indices,
        embed_offset=(config.embed_pad_y, config.embed_pad_x),
        vector_stride_xy=vector_stride_xy,
        vector_stride_z=vector_stride_z,
        max_vectors=max_vectors,
        min_speed_percentile=min_speed_percentile,
        vertical_scale=vertical_scale,
    )
    output_path = out_dir / (filename or f"velocity_3d_field_k{safe_time:03d}.png")
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path
