"""
states.py = bird behavioral states
"""

import numpy as np
from urban_geometry.birds.sim.sites import get_site_heightmaps, sample_surface_height
from urban_geometry.birds.sim.config import STATE_PARAMS
from urban_geometry.birds.sim.environment import day_phase

# state constants
FORAGE = 0 # TODO: add foraging state and appropriate transitions
TRANSIT = 1 # flight toward roost
MURMURATION = 2 # circling over roost
DESCENT = 3 # descent to roost
ROOST = 4 # stationary, settled on roost

def get_state_params(bstates):
    """
    Look up force weights and target speed for each bird based on state.
    
    Args:
        bstates: (N,) array, each bird's current state (integers 0-3)
    
    Returns:
        params: (N, 5) array, each row is [w_separation, w_alignment, w_cohesion, w_roost, target_speed]
    """
    return STATE_PARAMS[bstates] # indexing = one row per bird


def update_states(positions, bstates, time, config, env=None, energy=None, stress=None, rng=None, wave_rand=None, outbound=None):
    """
    Apply state transition rules driven by environment.
    
    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        bstates: (N,) array, each bird's current state (integers 0-3)
        time: float, current simulation time (seconds)
        config: SimConfig
        env: dict of (N,) arrays from environment.py (keys: 'light', 'temperature', 'pollution', 'noise'), or None
        energy: (N,) energy levels 0–1, or None
        stress: (N,) stress levels 0–1, or None
        rng: np.random.RandomState, RNG carried for reproducibility
        wave_rand: (N,) array, per-bird random offset for dawn wave departure
        outbound: True if bird is heading to forage site / False if returning to roosts
    
    Returns:
        new_bstates: (N,) array, each bird's new state (integers 0-3)
    """

    if config.lock_state >= 0:
        return bstates # state machine frozen (for optimization, so no transitions occur)

    new_states = bstates.copy()
    
    # distance to nearest roost
    roost_positions = np.array([r['center'] for r in config.world['roosts']]) # (R, 3)
    diffs = roost_positions[np.newaxis, :, :2] - positions[:, np.newaxis, :2] # (N, R, 2) horizontal only, so a small entry radius doesn't drag birds down into the roost
    dists = np.linalg.norm(diffs, axis=-1) # (N, R)
    dist_to_roost = np.min(dists, axis=1) # (N,)
    
    # transit/murmuration transition = triggered by proximity to roost, but only when birds are inbound
    close_enough = dist_to_roost < config.murmuration_entry_radius
    inbound = ~outbound if outbound is not None else np.ones(len(bstates), dtype=bool)
    transit_to_murm = (bstates == TRANSIT) & close_enough & inbound
    new_states[transit_to_murm] = MURMURATION
    
    # roost to transit = dawn departure in waves
    # birds leave the roost in discrete waves at successive light intensities, earlier beds are more well fed
    # so we should bracket departure by light level and energy (so higher-energy birds leave in earlier (dimmer) waves)
    if env is not None and config.world and config.world.get('forage_sites') and wave_rand is not None:
        morning = day_phase(time, config) < 0.5 # dawn, so won't misfire at dusk
        local_light = env['light']
        e = np.clip(energy, 0.0, 1.0) if energy is not None else np.full(len(bstates), 0.5)
        # per-bird wave number = energy bias (heavier earlier) + fixed noise, quantized into discrete waves
        wave_score = (1.0 - e) * config.wave_energy_bias + wave_rand * (1.0 - config.wave_energy_bias)
        wave_num = np.clip((wave_score * config.n_dawn_waves).astype(int), 0, config.n_dawn_waves - 1)
        departure_light = config.dawn_light_threshold + wave_num * config.wave_light_step
        depart = (bstates == ROOST) & morning & (local_light > departure_light)
        new_states[depart] = TRANSIT

    # forage to transit
    # light-triggered, furthest birds leave earliest (i.e. a travel-time budget)
    # well-fed birds leave sooner (can afford the commute, so don't need to keep feeding)
    if env is not None and config.world and config.world.get('forage_sites'):
        evening = day_phase(time, config) > 0.5 # evening has begun
        foraging = (bstates == FORAGE)
        if evening and foraging.any(): 
            local_light = env['light'] # light level perceived by each bird
            e = np.clip(energy, 0.0, 1.0) if energy is not None else np.full(len(bstates), 0.5) # bird energy, clipped to [0,1], use 0.5 if unavailable
            dist_factor = np.clip(dist_to_roost / config.dusk_distance_scale, 0.0, 1.0) # normalized distance to roost, farthest birds get largest departure boost
            noise = wave_rand * config.dusk_departure_noise if wave_rand is not None else 0.0 # random variation in each bird's departure threshold
            threshold = (config.dusk_light_threshold
                        + dist_factor * config.dusk_distance_boost
                        + e * config.dusk_energy_bias
                        + noise) # higher threshold means the bird leaves at a higher light level
            depart_forage = foraging & (local_light < threshold) # depart when local light falls below that bird's threshold
            new_states[depart_forage] = TRANSIT # move departing foragers into transit

    # murmuration to roost transition = driven by each bird's own perception of light level
    # additional factors for earlier roosting = low energy, high stress, colder temperature
    # TODO: find empirical sources for energy and stress effects on roost timing
    if env is not None:
        local_light = env['light'] # (N,) each bird's perceived light
        local_temp = env['temperature'] # (N,) local temperature
        
        # effective roosting threshold per bird, higher = roost sooner
        threshold = np.full(len(bstates), config.roost_light_threshold)
        
        if energy is not None:
            # tired birds raise their threshold so roost earlier
            # TODO: find empirical source for energy-driven roost timing
            energy_factor = np.clip((config.energy_roost_threshold - energy) * config.energy_roost_sensitivity, 0.0, config.energy_roost_max_boost)
            threshold += energy_factor
        
        if stress is not None:
            # stressed birds raise threshold i.e. roost earlier
            # TODO: find empirical source for stress-driven roost timing
            stress_factor = np.clip(stress * config.stress_roost_sensitivity, 0.0, config.stress_roost_max_boost)
            threshold += stress_factor
        
        # cold birds also exit murmuration earlier = earlier roost
        cold_factor = np.clip((config.cold_threshold - local_temp) * config.cold_roost_sensitivity, 0.0, config.cold_roost_max_boost)
        threshold += cold_factor
        
        # transition = light below bird's personal threshold
        # stochastic, probability increases as light drops further below threshold
        random_draw = rng.random(len(bstates)) if rng is not None else np.random.random(len(bstates))

        # surface height from heightmap (draped onto geometry, supports multiple roosts)
        # each bird checks its closest roost's actual surface height TODO: closest roost vs optimal roost
        roost_hmaps = get_site_heightmaps(config, config.world['roosts'])
        if roost_hmaps:
            surface_z, _ = sample_surface_height(roost_hmaps, positions)
        else:
            # fallback = closest roost center z per bird
            roost_positions_z = np.array([r['center'] for r in config.world['roosts']])
            diffs_z = roost_positions_z[np.newaxis, :, :] - positions[:, np.newaxis, :]
            closest_z = np.argmin(np.linalg.norm(diffs_z, axis=-1), axis=1)
            surface_z = roost_positions_z[closest_z, 2]

        # height above actual surface (from heightmap, not flat plane)
        height_above_surface = positions[:, 2] - surface_z

        # daylight gate = roosting only allowed when light is below bird's personal threshold
        dark_enough = local_light < threshold # (N,) bool

        # proximity-based probability i.e. closer to surface = higher chance of entering descent
        # creates natural top-down cascade as bottom birds peel off first
        proximity_factor = np.clip(1.0 - height_above_surface / 30.0, 0.0, 1.0)
        roost_land_prob = proximity_factor * config.roost_max_chance_per_step

        # murmuration -> descent only fires during dusk not dawn
        evening = day_phase(time, config) > 0.5
        murm_to_descent = (bstates == MURMURATION) & dark_enough & (random_draw < roost_land_prob) & evening
        new_states[murm_to_descent] = DESCENT
    
    else: # NOTE: ideally never used
        # fallback to time-based state transition if no environment is provided
        total_time = config.n_steps * config.dt
        roost_time = total_time * config.roost_descent_time_frac
        if time > roost_time:
            time_past = time - roost_time
            roost_probability = 1.0 / (1.0 + np.exp(-(time_past - 30.0) / 10.0)) # sigmoid, 50% probability at 30s past threshold, ramp width 10s
            random_draw = rng.random(len(bstates)) if rng is not None else np.random.random(len(bstates))
            murm_to_descent = (bstates == MURMURATION) & (random_draw < roost_probability * config.dt)
            new_states[murm_to_descent] = DESCENT
    
    return new_states
