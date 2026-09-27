"""
environment.py = environmental fields that birds sense and respond to

each field is a standalone sampler (positions, time, config) -> (N,) array, callable at arbitrary positions
"""

import numpy as np

def day_phase(time, config):
    # gives fraction through the current simulated day
    # 0 = midnight, 0.25 = dawn, 0.5 = noon, 0.75 = dusk (cycles every day_length)
    day_len = (config.n_steps * config.dt) / max(config.n_days, 1e-6)
    return ((time / day_len) + config.day_phase_start) % 1.0

def day_fraction(time, config):
    # day light level = 0 (midnight) -> 1 (noon)
    # cosine should give smooth dawn/dusk
    frac = day_phase(time, config)
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * frac))

def sample_pollution(positions, time, config):
    """
    Scalar pollution field, 0-1
    - ground-level sources
    - exponential distance falloff
    
    Args:
        positions: (N, 3) array, positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        values: (N,) array, pollution values at positions
    """
    world = config.world
    x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
    N = positions.shape[0]
    pollution = np.zeros(N)

    for road in world.get('roads', []):
        road_dist = np.abs(y - road['y'])
        pollution += np.exp(-road_dist / road['pollution_decay'])

    for src in world.get('point_sources', []):
        if src['type'] != 'pollution':
            continue
        sp = src['pos'] # [x, y, z]
        dist = np.sqrt((x - sp[0])**2 + (y - sp[1])**2 + (z - sp[2])**2) # 3D distance from source
        pollution += src['strength'] * np.exp(-dist / src['decay'])

    return np.clip(pollution, 0.0, 1.0)

def sample_noise(positions, time, config):
    """
    Scalar noise field, 0-1 
    - ground-level sources
    - exponential distance falloff
    
    Args:
        positions: (N, 3) array, positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        values: (N,) array, noise values at positions
    """
    world = config.world
    x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
    N = positions.shape[0]
    noise = np.zeros(N)

    for road in world.get('roads', []):
        road_dist = np.abs(y - road['y'])
        noise += 0.7 * np.exp(-road_dist / road['noise_decay']) # TODO: make 0.7 configurable

    for src in world.get('point_sources', []):
        if src['type'] != 'noise':
            continue
        sp = src['pos'] # [x, y, z]
        dist = np.sqrt((x - sp[0])**2 + (y - sp[1])**2 + (z - sp[2])**2) # 3D distance from source
        noise += src['strength'] * np.exp(-dist / src['decay'])

    return np.clip(noise, 0.0, 1.0)


def sample_light(positions, time, config):
    """
    Light level field, 0-1 
    - sky luminance from day cycle plus streetlight halos
    
    Args:
        positions: (N, 3) array, positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        values: (N,) array, light values at positions
    """
    world = config.world
    y = positions[:, 1]
    N = positions.shape[0]

    sky_light = day_fraction(time, config)

    streetlight_intensity = np.clip(1.0 - sky_light * 2.0, 0.0, 0.6)
    streetlight_effect = np.zeros(N)
    for road in world.get('roads', []):
        road_dist = np.abs(y - road['y'])
        streetlight_effect += streetlight_intensity * np.exp(-road_dist / 15.0)

    return np.clip(sky_light + streetlight_effect, 0.0, 1.0)


def sample_temperature(positions, time, config):
    """
    Temperature field in Celsius
    - day-cycle base
    - urban warming near roads
    - altitude cooling
       
    Args:
        positions: (N, 3) array, positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        values: (N,) array, temperature values at positions
    """
    world = config.world
    y, z = positions[:, 1], positions[:, 2]
    N = positions.shape[0]

    base_temp = 12.0 - 5.0 * (1.0 - day_fraction(time, config)) # TODO: make configurable
    urban_warming = np.zeros(N)
    for road in world.get('roads', []):
        road_dist = np.abs(y - road['y'])
        urban_warming += 2.0 * np.exp(-road_dist / 30.0)
    altitude_cooling = z * 0.0065
    return base_temp + urban_warming - altitude_cooling

# REGISTRY = name -> sampler
# adding a field = adding a sampler function and a line here (+ a FIELD_RESPONSES entry later)
FIELD_SAMPLERS = {
    'pollution':   sample_pollution,
    'noise':       sample_noise,
    'light':       sample_light,
    'temperature': sample_temperature,
}

def get_environment(positions, time, config):
    """
    Sample all environmental fields at each bird's position
    - a wrapper for entire registry FIELD_SAMPLERS
    
    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        env: dict of (N,) arrays:
            'pollution': 0–1
            'noise':     0–1
            'light':     0–1
            'temperature': °C
    """
    return {name: fn(positions, time, config) for name, fn in FIELD_SAMPLERS.items()}