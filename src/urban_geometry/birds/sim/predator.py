"""
predator.py = simple predator agent(s) that drive evasion behavior TODO: currently a placeholder
"""

import numpy as np

# TODO: currently predators are very hard-coded, in future make these more complex

def init_predator(config):
    """
    Create initial predator state. The predator starts offset from the flock and circles.
    
    Args:
        config: SimConfig
    
    Returns:
        predator: dict with 'pos' (3,), 'vel' (3,), 'active' bool
    """
    roost = np.array(config.roost_position)
    
    return {
        # start above and to the side of the roost
        'pos': roost + np.array([60.0, 60.0, 30.0]),
        'vel': np.array([-5.0, 3.0, 0.0]), # initial velocity
        'active': True,
    }


def update_predator(predator, time, config):
    """
    Update predator position. TODO: add more advanced predator behavior
    - simple circling pattern around the roost at fixed radius and altitude
    - occasionally dives (altitude drop) to trigger stronger evasion
    
    Args:
        predator: dict with 'pos', 'vel', 'active'
        time: float, current simulation time (seconds)
        config: SimConfig
    
    Returns:
        updated predator dict
    """
    if not predator['active']:
        return predator
    
    dt = config.dt
    roost = np.array(config.roost_position)
    
    # CIRCLING BEHAVIOR
    # orbit around the roost at radius 60m, altitude 45m
    # angular speed 0.1 rad/s
    orbit_radius = 60.0
    orbit_altitude = roost[2] + 30.0
    angular_speed = 0.1
    
    angle = angular_speed * time
    
    target_pos = np.array([
        roost[0] + orbit_radius * np.cos(angle),
        roost[1] + orbit_radius * np.sin(angle),
        orbit_altitude,
    ])
    
    # OCCASIONAL DIVE
    # every 40 seconds, drop altitude briefly (simulates attack run)
    dive_period = 40.0
    dive_phase = (time % dive_period) / dive_period
    if 0.4 < dive_phase < 0.55:
        # during dive, drop altitude toward the flock
        target_pos[2] = roost[2] + 5.0 # dive close to flock altitude
    
    # smooth movement toward target
    direction = target_pos - predator['pos']
    dist = np.linalg.norm(direction)
    if dist > 0.1:
        direction = direction / dist
    
    predator_speed = 15.0 # speed of the predator
    new_vel = direction * predator_speed
    new_pos = predator['pos'] + new_vel * dt
    
    # PREDATOR LEAVES (after some time)
    total_time = config.n_steps * config.dt
    active = time < total_time * 0.6 # predator leaves at 60% through sim
    
    return {
        'pos': new_pos,
        'vel': new_vel,
        'active': active,
    }


def compute_predator_avoidance(bird_positions, predator, config):
    """
    Compute evasion force from the predator.
    - birds within detection_radius of the predator steer sharply away
    - force is stronger the closer the predator is (inverse square law) TODO: empirical backing for inverse square law
    
    Args:
        bird_positions: (N, 3) array, bird positions in 3D space (meters)
        predator: dict with 'pos', 'active'
        config: SimConfig
    
    Returns:
        force: (N, 3) array, evasion force vectors
        threat: (N,) array, values scalar 0–1 indicating how threatened each bird feels (used to update stress)
    """
    N = bird_positions.shape[0]
    force = np.zeros((N, 3))
    threat = np.zeros(N)
    
    if not predator['active']:
        return force, threat
    
    pred_pos = predator['pos']
    
    # vector from predator to each bird (escape direction)
    away = bird_positions - pred_pos # (N, 3)
    dist = np.linalg.norm(away, axis=-1) # (N,)
    
    # only affect birds within detection radius
    in_range = dist < config.predator_detection_radius # (N,) bool
    
    # normalized escape direction
    safe_dist = np.maximum(dist, 1e-6)
    away_unit = away / safe_dist[:, np.newaxis] # (N, 3)
    
    # force = inverse square, strong when close TODO: empirical backing for inverse square law
    strength = (config.predator_detection_radius / safe_dist) ** 2
    strength = np.where(in_range, strength, 0.0) # (N,)
    
    force = away_unit * strength[:, np.newaxis] # (N, 3)
    
    # threat level ranges from 0 (no predator) to 1 (predator on top of bird)
    # used for stress calculation in integrator
    threat = np.clip(strength / 10.0, 0.0, 1.0) # normalize
    
    return force, threat
