"""
wind.py = wind field interface
"""

import numpy as np
from scipy.ndimage import map_coordinates


def get_wind(positions, time, config):
    """
    Compute the wind velocity at each bird's position
    - wind velocity is added to the bird's airspeed to get ground velocity v_ground = v_airspeed + v_wind
    - assumes bird masses are negligible so wind affects birds but not vice versa

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig

    Returns:
        wind: (N, 3) array, wind velocity vectors at each bird's position (m/s)
    """
    N = positions.shape[0]
    mode = config.wind_mode

    # WIND MODES
    if mode == "none":
        # no wind
        return np.zeros((N, 3))

    elif mode == "uniform":
        # constant wind everywhere i.e. all birds feel same wind
        direction = np.array(config.wind_direction, dtype=float)
        direction = direction / np.maximum(np.linalg.norm(direction), 1e-6)
        wind = direction * config.wind_strength
        return np.broadcast_to(wind, (N, 3)).copy()

    elif mode == "sinusoidal":
        # spatially + temporally varying wind (sinusoidal)
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]  # z unused for now

        # base flow (mean wind)
        base = np.array(config.wind_direction, dtype=float)
        base = base / np.maximum(np.linalg.norm(base), 1e-6) * config.wind_strength

        # spatial fluctuations (wavelength ~50m, slow drift with time)
        freq_space = 0.02  # spatial frequency (1/meters)
        freq_time = 0.1  # temporal frequency (1/seconds)
        amplitude = config.wind_strength * 0.4  # fluctuation amplitude

        wx = amplitude * np.sin(freq_space * y + freq_time * time)
        wy = amplitude * np.cos(freq_space * x + freq_time * time * 0.7)
        wz = amplitude * 0.3 * np.sin(freq_space * (x + y) + freq_time * time * 0.3)

        fluctuation = np.stack([wx, wy, wz], axis=-1)  # (N, 3)

        return np.broadcast_to(base, (N, 3)) + fluctuation

    elif config.wind_mode == "scaled":
        return _get_scaled_wind(positions, time, config)

    else:
        raise ValueError(
            f"Unknown wind mode: {mode}. Options: none, uniform, sinusoidal, neural_physics"
        )


_scaled_cache = {}


def _load_scaled_wind(path):
    """load and cache the precomputed SCALED wind field"""
    if path not in _scaled_cache:
        data = np.load(path)
        _scaled_cache[path] = {
            "wind": data["wind"],  # (n_steps, 3, depth, height, width)
            "geometry": data["geometry"],  # (depth, height, width) bool
            "grid_spacing": float(data["grid_spacing"]),
            "grid_spacing_z": float(data.get("grid_spacing_z", data["grid_spacing"])),
            "n_steps": data["wind"].shape[0],
        }
    return _scaled_cache[path]


def _get_scaled_wind(positions, time, config):
    """
    Sample precomputed SCALED wind field at bird positions via trilinear interpolation.

    The SCALED grid is (depth, height, width) = (z, y, x) with spacing grid_spacing in meters.
    Bird positions are in simulation coordinates (x, y, z) in meters.

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        time: float, current simulation time in seconds
        config: SimConfig (uses scaled_wind_path, scaled_wind_speed, scaled_grid_origin, dt)

    Returns:
        wind: (N, 3) array, wind velocity vectors at each bird position (m/s)
    """
    data = _load_scaled_wind(config.scaled_wind_path)
    spacing = data["grid_spacing"]
    n_steps = data["n_steps"]

    # which SCALED timestep to use (loop if simulation runs longer than precomputed data) TODO: this seems not ideal... should always be same length as simulation
    step_idx = (
        int(time / config.scaled_dt) % n_steps
    )  # each SCALED step = scaled_dt seconds of physical time

    wind_volume = data["wind"][step_idx]  # (3, depth, height, width) = (3, z, y, x)

    # convert bird positions to grid coordinates
    origin = np.array(config.scaled_grid_origin)
    grid_coords = np.zeros_like(positions)
    grid_coords[:, 0] = (positions[:, 0] - origin[0]) / spacing  # x: 8m cells
    grid_coords[:, 1] = (positions[:, 1] - origin[1]) / spacing  # y: 8m cells
    grid_coords[:, 2] = (positions[:, 2] - origin[2]) / data["grid_spacing_z"]  # z: 1m cells

    # SCALED grid axes are (depth=z, height=y, width=x), so reorder to (z, y, x) for interpolation
    coords_zyx = grid_coords[:, [2, 1, 0]].T  # (3, N) = (z_coords, y_coords, x_coords)

    # sample each velocity component via trilinear interpolation
    N = positions.shape[0]
    wind = np.zeros((N, 3))

    for c in range(3):  # u, v, w
        wind[:, c] = map_coordinates(
            wind_volume[c],  # (depth, height, width)
            coords_zyx,  # (3, N) = (z, y, x) coordinates
            order=1,  # trilinear interpolation
            mode="nearest",  # clamp at boundaries
        )

    # scale from normalized SCALED units to m/s
    wind *= config.scaled_wind_speed

    # zero out wind inside buildings (birds shouldn't be there, but just in case)
    geometry = data["geometry"]  # (depth, height, width)
    grid_ints = np.clip(coords_zyx.astype(int), 0, np.array(geometry.shape)[:, np.newaxis] - 1)
    in_building = geometry[grid_ints[0], grid_ints[1], grid_ints[2]]
    wind[in_building] = 0.0

    return wind
