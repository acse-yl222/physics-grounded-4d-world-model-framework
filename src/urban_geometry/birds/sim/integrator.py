"""
integrator.py = main simulation loop
"""

import numpy as np
import os
from urban_geometry.birds.sim.neighbors import find_topological_neighbors, compute_blind_angle_mask
from urban_geometry.birds.sim.forces import (
    compute_separation, 
    compute_alignment, 
    compute_cohesion, 
    compute_roost_attraction,
    compute_obstacle_avoidance,
    compute_centrality,
    compute_field_speed_modulation,
    compute_wind_response,
)
from urban_geometry.birds.sim.states import get_state_params, update_states, FORAGE, TRANSIT, MURMURATION, DESCENT, ROOST
from urban_geometry.birds.sim.sites import get_site_heightmaps, sample_surface_height
from urban_geometry.birds.sim.wind import get_wind
from urban_geometry.birds.sim.environment import get_environment
from urban_geometry.birds.sim.predator import compute_predator_avoidance
from urban_geometry.birds.sim.config import INDIVIDUAL_TRAITS, AFFECT_GAINS, WIND_RESPONSE_GAIN, FIELD_RESPONSES, FIELD_RESPONSE_GAIN, WAVE_GUIDANCE_GAIN
from urban_geometry.birds.sim.routing import get_arrival_time_field, compute_wave_guidance
from urban_geometry.birds.sim.foraging import update_forage, init_food_field
from urban_geometry.birds.sim.world_gen import generate_world

_geometry_cache = {}

def _load_geometry(config):
    """load and cache building geometry, preferring separate geometry file if provided"""
    geo_src = config.geometry_path or config.scaled_wind_path
    if geo_src not in _geometry_cache:
        if geo_src and os.path.exists(geo_src):
            data = np.load(geo_src)
            _geometry_cache[geo_src] = {
                'geometry': data['geometry'],
                'grid_spacing': float(data['grid_spacing']),
                'grid_spacing_z': float(data['grid_spacing_z']) if 'grid_spacing_z' in data else float(data['grid_spacing']),
                'grid_origin': tuple(data['grid_origin']) if 'grid_origin' in data else tuple(config.scaled_grid_origin),
            }
        else:
            _geometry_cache[geo_src] = None
    return _geometry_cache[geo_src]

def init_state(config):
    """
    Make the initial simulation state
    
    Args:
        config: SimConfig
    
    Returns:
        state: dict of arrays with keys:
            'pos': (N, 3) positions in meters
            'vel': (N, 3) airspeed in m/s (not ground speed)
            'bank': (N,) bank/roll angles in radians
            'bstate': (N,) behavioral state integers (see states.py)
            'energy': (N,) energy levels 0–1
            'valence': (N,) affective valence, -1 (bad) to 1 (good)
            'arousal': (N,) affective arousal, 0 (calm) to 1 (agitated)
            'forage_site': (N,) assigned forage-site indices
            'wave_rand': (N,) fixed per-bird random values for dawn wave assignment
            'outbound': (N,) whether each bird is heading to its forage site
            'food_fields': list of spatial food-density fields for forage sites
            'forage_heading': (N,) current ground-foraging headings
            'forage_mode': (N,) ARS modes, 0 = extensive, 1 = intensive
            'forage_giveup': (N,) consecutive foodless-hop counters
            'forage_dwell': (N,) time until the next foraging hop
            'forage_hop_timer': (N,) time remaining in the current hop
            'time': float, current simulation time in seconds
            'rng': numpy RandomState (carried so the sim stays reproducible)
            'traits': dict of per-bird fixed trait arrays
            'identity': dict of normalized per-bird trait values for visualization
    """
    rng = np.random.RandomState(config.seed)
    N = config.n_birds
    
    # spawn birds as a tight cluster at a specified point
    pos = rng.randn(N, 3) * config.init_flock_radius # tight isotropic cluster
    pos += np.array(config.spawn_point)
    
    # ensure birds start above buildings TODO: make this specifiable later or handle more elegantly
    geo_data = _load_geometry(config)

    # auto-generate world features (roosts, forage sites) if requested
    # occurs before anything reads config.world (heightmaps, routing, etc.)
    generate_world(config, geo_data)

    if geo_data is not None:
        geo = geo_data['geometry'] # (z, y, x)
        max_building_z = 0
        for z in range(geo.shape[0]):
            if geo[z].any():
                max_building_z = (z + 1) * geo_data['grid_spacing_z']
        min_start_alt = config.min_start_alt if config.min_start_alt is not None else max_building_z + 10.0
        pos[:, 2] = np.maximum(pos[:, 2], min_start_alt)
    else:
        pos[:, 2] = np.maximum(pos[:, 2], 5.0)
    
    # velocities = common heading tangential to the roost (not toward it)
    # so flock should fly alongside the roost as a polarized murmuration rather than diving into it
    # small perturbation gives realistic spread without breaking order
    base_heading = np.array([0.0, 1.0, 0.0]) # fly in +y, perpendicular to the x-offset
    perturbation = rng.randn(N, 3) * 0.1 # small, keeps the flock organized
    perturbation[:, 2] = 0.0
    headings = base_heading + perturbation
    headings = headings / np.maximum(np.linalg.norm(headings, axis=-1, keepdims=True), 1e-6)

    # initial speed near cruise, tight spread
    speed = config.cruise_speed + rng.randn(N, 1) * 0.5
    speed = np.clip(speed, config.v_min, config.v_max)

    vel = headings * speed
    
    # bank angles initially zero (wings are level)
    bank = np.zeros(N)

    # INTERNAL STATES
    # energy, 1.0 = fully rested, 0.0 = exhausted
    # depletes during flight (faster at higher speed), replenishes during roosting
    energy = np.ones(N) * 0.8 # start slightly below full
    # AFFECTIVE STATE = valence/arousal, start neutral-calm
    # valence 0 = neutral (neither good nor bad), arousal 0 = calm
    valence = np.zeros(N)
    arousal = np.zeros(N)
    
    # start in whatever state is specified by the config
    bstate = np.full(N, config.start_state, dtype=np.int32)

    # precompute roost heightmaps (drapes each roost onto geometry below it)
    # cached for the lifetime of the simulation, used by step(), states.py, forces.py
    _roost_hmaps = get_site_heightmaps(config, config.world['roosts'], geo_data, geo_data['grid_origin'])

    # pre-cache individual forage site heightmaps with geometry so that compute_roost_attraction and the speed slowdown (which call get_site_heightmaps without geo_data) get cache hits on correctly draped heightmaps
    _forage_sites_pre = config.world.get('forage_sites', []) if config.world else []
    for _fs in _forage_sites_pre:
        get_site_heightmaps(config, [_fs], geo_data, geo_data['grid_origin'])

    # SNAP each roost's center z to wherever it actually drapes onto the geometry
    # (so that the roost altitude used everywhere matches the real draped surface instead of the z specified in config)
    for _r, _h in zip(config.world['roosts'], _roost_hmaps):
        _r['center'][2] = float(np.mean(_h['heights'])) # average draped height of the roost footprint


    # INDIVIDUAL TRAITS = per-bird variation so the flock is individuals, not clones
    # each trait ~= Normal(config_value, spread*config_value), clipped to sane bounds
    traits = {}
    for name, (spread, lo, hi) in INDIVIDUAL_TRAITS.items():
        mean = getattr(config, name)
        if config.enable_individuality:
            traits[name] = np.clip(rng.normal(mean, spread * abs(mean), size=N), lo, hi)
        else:
            traits[name] = np.full(N, mean, dtype=float)

    # DERIVED IDENTITY = normalized [0,1] per trait, visualized as patterns in viewer
    def _norm(name, arr):
        _, lo, hi = INDIVIDUAL_TRAITS[name]
        return np.clip((arr - lo) / (hi - lo), 0.0, 1.0)

    identity = {
        'valence_disposition':  _norm('valence_disposition',  traits['valence_disposition']),
        'arousal_excitability': _norm('arousal_excitability', traits['arousal_excitability']),
        'energy_drain_rate':    _norm('energy_drain_rate',    traits['energy_drain_rate']),
    }

    # FORAGE-SITE ASSIGNMENT = feeding areas remembered by each bird
    # assign once with probability proportional to quality / distance^2 = IFD over space TODO: tweak
    forage_sites = config.world.get('forage_sites', []) if config.world else []
    if forage_sites:
        f_centers = np.array([s['center'] for s in forage_sites])
        f_qualities = np.array([s.get('quality', 1.0) for s in forage_sites])
        r_centers = np.array(config.world['roosts'][0]['center'])
        f_dists = np.linalg.norm(f_centers[:, :2] - r_centers[:2], axis=1) # horizontal distance from roost
        f_weights = f_qualities / np.maximum(f_dists**2, 1.0) # IFD weight = quality discounted by distance^2
        forage_site = rng.choice(len(forage_sites), size=N, p=f_weights / f_weights.sum())
    else:
        forage_site = np.full(N, -1, dtype=int)
    wave_rand = rng.rand(N) # fixed per-bird noise for thet dawn wave assignment
    outbound = np.zeros(N, dtype=bool)# True once a bird departs the roost heading out to forage
    
    # spatial food fields = each site gets a 2D grid of food density with random Gaussian patches
    food_fields = []
    for site_index, site in enumerate(forage_sites):
        grid = init_food_field(site, config, site_index)
        food_fields.append({'grid': grid, 'center': site['center'], 'size': site['size']})

    # per-bird ARS state
    forage_heading = rng.uniform(0, 2 * np.pi, size=N) # initial walk heading (random)
    forage_mode = np.zeros(N, dtype=np.int32) # 0 = extensive (searching), 1 = intensive (exploiting area where food was found)
    forage_giveup = np.zeros(N, dtype=np.int32) # foodless hops in a row (giving-up counter)
    forage_dwell = rng.uniform(0, config.ars_dwell_time, size=N) # seconds until first hop (staggered so birds don't hop in sync)
    forage_hop_timer = np.zeros(N) # seconds left in the current hop (0 = not hopping)

    return {
        'pos': pos,
        'vel': vel,
        'bank': bank,
        'bstate': bstate,
        'energy': energy,
        'valence': valence,
        'arousal': arousal,
        'forage_site': forage_site,
        'wave_rand': wave_rand,
        'outbound': outbound,
        'food_fields': food_fields,
        'forage_heading': forage_heading,
        'forage_mode': forage_mode,
        'forage_giveup': forage_giveup,
        'forage_dwell': forage_dwell,
        'forage_hop_timer': forage_hop_timer,
        'time': 0.0,
        'rng' : rng,
        'traits': traits,
        'identity': identity,
    }

def step(state, config, predator=None):
    """
    Takes the current state and returns the next state, advancing the simulation by one timestep.

    Args:
        state: dict of arrays with keys:
            'pos': (N, 3) positions in meters
            'vel': (N, 3) airspeed in m/s (not ground speed)
            'bank': (N,) bank/roll angles in radians
            'bstate': (N,) behavioral state integers (see states.py)
            'energy': (N,) energy levels 0–1
            'valence': (N,) affective valence, -1 (bad) to 1 (good)
            'arousal': (N,) affective arousal, 0 (calm) to 1 (agitated)
            'forage_site': (N,) assigned forage-site indices
            'wave_rand': (N,) fixed per-bird random values for dawn wave assignment
            'outbound': (N,) whether each bird is heading to its forage site
            'food_fields': list of spatial food-density fields for forage sites
            'forage_heading': (N,) current ground-foraging headings
            'forage_mode': (N,) ARS modes, 0 = extensive, 1 = intensive
            'forage_giveup': (N,) consecutive foodless-hop counters
            'forage_dwell': (N,) time until the next foraging hop
            'forage_hop_timer': (N,) time remaining in the current hop
            'time': float, current simulation time in seconds
            'rng': numpy RandomState (carried so the sim stays reproducible)
            'traits': dict of per-bird fixed trait arrays
            'identity': dict of normalized per-bird trait values for visualization
        config: SimConfig
        predator: dict from predator.py, or None
    
    Returns:
        new_state: dict with same keys, updated
    """
    pos = state['pos']
    vel = state['vel']
    bank = state['bank']
    bstate = state['bstate']
    energy = state['energy']
    valence = state['valence']
    arousal = state['arousal']
    time = state['time']
    rng = state['rng']
    traits = state['traits']
    forage_site = state.get('forage_site', np.full(pos.shape[0], -1, dtype=int))
    wave_rand = state.get('wave_rand', np.zeros(pos.shape[0]))
    outbound = state.get('outbound', np.zeros(pos.shape[0], dtype=bool))
    food_fields = state.get('food_fields', [])
    forage_heading = state.get('forage_heading', np.zeros(pos.shape[0]))
    forage_mode = state.get('forage_mode', np.zeros(pos.shape[0], dtype=np.int32))
    forage_giveup = state.get('forage_giveup', np.zeros(pos.shape[0], dtype=np.int32))
    forage_dwell = state.get('forage_dwell', np.zeros(pos.shape[0]))
    forage_hop_timer = state.get('forage_hop_timer', np.zeros(pos.shape[0]))
    dt = config.dt
    N = pos.shape[0]
    
    # FIND TOPOLOGICAL NEIGHBORS
    if N > 1:
        nb_idx, nb_dist = find_topological_neighbors(pos, config.k_neighbors)
    else:
        nb_idx = np.zeros((1, 0), dtype=int)
        nb_dist = np.zeros((1, 0))

    # COMPUTE BLIND ANGLE MASK
    if N > 1:
        # HEAD NYSTAGMUS = birds stabilize their head during banking, so visual perception uses level-flight heading, not banked
        # i.e. the blind angle cone stays horizontal even when the bird's body is tilted
        level_vel = vel.copy() # start with actual velocity
        level_vel[:, 2] = 0.0 # remove vertical component to get horizontal velocity
        level_speed = np.linalg.norm(level_vel, axis=-1, keepdims=True) # horizontal speed
        nearly_vertical = (level_speed < 1e-4).reshape(-1) # detect birds with no meaningful horizontal heading
        if np.any(nearly_vertical): # TODO: note that currently there is a discontinuity where, if the bird goes from flying horizontally to vertically, at a discrete point the blind cone jumps from purely horizontal to along the axis of the bird
            level_vel[nearly_vertical] = vel[nearly_vertical] # for those birds, use original velocity as fallback
        visibility_mask = compute_blind_angle_mask(pos, level_vel, nb_idx, config.blind_angle) # velocities are used to extract headings
        centrality = compute_centrality(pos, nb_idx)
    else:
        visibility_mask = None
        centrality = None
    
    # SENSE ENVIRONMENT
    if config.enable_environment:
        env = get_environment(pos, time, config)
    else:
        env = None
    
    # GET STATE-DEPENDENT PARAMETERS
    sparams = get_state_params(bstate)
    w_sep   = sparams[:, 0:1]
    w_ali   = sparams[:, 1:2]
    w_coh   = sparams[:, 2:3]
    w_roo   = sparams[:, 3:4]
    v_target = sparams[:, 4:5]
    
    # temperature modifies cohesion e.g. colder = tighter clustering
    if env is not None:
        cold_mask = env['temperature'] < config.cold_threshold
        cold_boost = np.where(cold_mask, config.cold_cohesion_boost, 0.0)
        w_coh = w_coh + cold_boost[:, np.newaxis]
    
    # low energy reduces target speed (tired birds fly slower)
    energy_speed_factor = np.clip(energy * 1.2, 0.5, 1.0)[:, np.newaxis] # TODO: add 1.2 and 0.5 to config
    v_target = v_target * energy_speed_factor
    
    # DESCENT birds perceive altitude and slow down as they approach surface
    # closer to surface = lower target speed = bird decelerates naturally
    surface_z = np.zeros(N)
    if bstate is not None:
        descent_mask = (bstate == DESCENT)
        if descent_mask.any():
            # default = inbound birds descend to a roost surface
            roost_hmaps = get_site_heightmaps(config, config.world['roosts'])
            if roost_hmaps:
                surface_z, _ = sample_surface_height(roost_hmaps, pos)

            # outbound birds descend to assigned forage site
            forage_sites_sd = config.world.get('forage_sites', []) if config.world else []
            if forage_sites_sd and outbound is not None:
                for site_idx in range(len(forage_sites_sd)):
                    site_descent = descent_mask & outbound & (forage_site == site_idx)
                    if not site_descent.any():
                        continue
                    fs_hmaps = get_site_heightmaps(config, [forage_sites_sd[site_idx]])
                    if fs_hmaps:
                        fs_z, _ = sample_surface_height(fs_hmaps, pos)
                        surface_z[site_descent] = fs_z[site_descent]

            alt_above = pos[:, 2] - surface_z
            # at descent_slowdown_height = full target speed, at 0m = 10% of target speed TODO: remove hardcoded value
            speed_scale = np.clip(alt_above / config.descent_slowdown_height, 0.1, 1.0)
            v_target[descent_mask] *= speed_scale[descent_mask, np.newaxis]
    state['surface_z'] = surface_z

    # COMPUTE ALL FORCES
    if N > 1:
        f_sep = compute_separation(pos, nb_idx, nb_dist,
                                   config.r_hard_sphere, config.r_separation,
                                   config.separation_gaussian_floor)
        f_ali = compute_alignment(vel, nb_idx, mask=visibility_mask)
        f_coh = compute_cohesion(pos, nb_idx, neighbor_distances=nb_dist,
                                 mask=visibility_mask, centrality=centrality,
                                 r_hard_sphere=config.r_hard_sphere)
    else:
        f_sep = np.zeros_like(pos)
        f_ali = np.zeros_like(pos)
        f_coh = np.zeros_like(pos)

    # roost attraction, inbound birds target roosts, outbound birds target their assigned forage site
    f_roost = compute_roost_attraction(pos, vel, config.world['roosts'], config, bstate=bstate, env=env)
    forage_sites_roost = config.world.get('forage_sites', []) if config.world else []
    if forage_sites_roost and outbound.any():
        for site_idx in range(len(forage_sites_roost)):
            site_mask = outbound & (forage_site == site_idx)
            if not site_mask.any():
                continue
            f_forage = compute_roost_attraction(pos, vel, [forage_sites_roost[site_idx]], config, bstate=bstate, env=env)
            f_roost[site_mask] = f_forage[site_mask]

    geo_data = _load_geometry(config)
    if geo_data is not None:
        f_obstacle = compute_obstacle_avoidance(
            pos, vel, geo_data['geometry'], geo_data['grid_spacing'],
            geo_data['grid_spacing_z'],
            np.array(geo_data['grid_origin']), config.building_detection_dist
        )
    else:
        f_obstacle = np.zeros_like(pos) # fallback when no building data
    
    # predator avoidance
    threat = np.zeros(N)
    f_pred = np.zeros_like(pos)
    if predator is not None and config.enable_predator:
        f_pred, threat = compute_predator_avoidance(pos, predator, config)
    
    # GET WIND
    wind = get_wind(pos, time, config)

    # BERDAHL FIELD SPEED-MODULATION (orthokinesis)
    # modulate target speed by the local scalar fields each bird senses
    if env is not None:
        wind_mag = np.linalg.norm(wind, axis=-1) / config.v_max  # |wind| normalized to ~0-1
        field_values = {
            'pollution': env['pollution'],
            'noise':     env['noise'],
        }
        field_gain = FIELD_RESPONSE_GAIN[bstate][:, np.newaxis] # (N,1) per-state
        v_target = compute_field_speed_modulation(field_values, FIELD_RESPONSES, v_target, field_gain, v_min=config.v_min_sustained, v_max=config.v_max)
    
    # separation force = use full strength inside hard sphere, state-dependent outside sphere
    # enforce minimum 1 Newton inside hard sphere regardless of state i.e. the value from (table 1 in H2010)
    effective_sep_weight = w_sep
    if N > 1:
        inside_hard_sphere = (nb_dist[:, 0:1] < config.r_hard_sphere).astype(float)
        effective_sep_weight = np.maximum(w_sep, inside_hard_sphere * 1.0)

    # WAVE ROUTING = steer down -grad T (first-arrival-time field) toward home (routing.py)
    # static field, cached, and obstacle avoidance is inherent (T never decreases into a wall)
    if config.enable_wave_routing and geo_data is not None and config.world.get('roosts'):
        _T = get_arrival_time_field(geo_data, np.array(geo_data['grid_origin']),
                                    [r['center'] for r in config.world['roosts']], config, time)
        wave_dir = compute_wave_guidance(pos, _T, np.array(geo_data['grid_origin']),
                                         geo_data['grid_spacing'], geo_data['grid_spacing_z'])
        
        f_wave = WAVE_GUIDANCE_GAIN[bstate][:, np.newaxis] * wave_dir

        # precompute and cache forage site wave fields on the first step
        forage_sites_pre = config.world.get('forage_sites', []) if config.world else []
        for forage_site_pre in forage_sites_pre:
            get_arrival_time_field(geo_data, np.array(geo_data['grid_origin']),
                                [forage_site_pre['center']], config, time)
    else:
        f_wave = np.zeros_like(pos)

    # OUTBOUND WAVE ROUTING = birds heading out to forage use a wave field solved from their assigned forage site
    f_sites = config.world.get('forage_sites', []) if config.world else []
    if f_sites and outbound.any() and geo_data is not None:
        for site_idx in range(len(f_sites)):
            site_mask = outbound & (forage_site == site_idx)
            if not site_mask.any():
                continue
            arrival_time_field = get_arrival_time_field(geo_data, np.array(geo_data['grid_origin']),
                                          [f_sites[site_idx]['center']], config, time)
            forage_dir = compute_wave_guidance(pos[site_mask], arrival_time_field, np.array(geo_data['grid_origin']),
                                          geo_data['grid_spacing'], geo_data['grid_spacing_z'])
            f_wave[site_mask] = WAVE_GUIDANCE_GAIN[bstate[site_mask]][:, np.newaxis] * forage_dir

    # COMBINE FORCES
    desired = (
        effective_sep_weight * f_sep +
        config.w_wave_guidance * f_wave +
        w_ali * f_ali +
        w_coh * f_coh +
        w_roo * f_roost +
        config.w_building_avoidance * f_obstacle +
        config.w_predator_avoidance * f_pred
    )

    # WIND RESPONSE (anemotaxis) = body-local reaction to the sensed wind vector
    # added to desired (steering force)
    # intended travel direction = the normalized behavioural steering so far (pre-wind, pre-noise) = "where the bird wants to go" (which the bail-off tacks around)
    desired_mag = np.linalg.norm(desired, axis=-1, keepdims=True)
    intended_dir = desired / np.maximum(desired_mag, 1e-6)
    weak_intent = (desired_mag[:, 0] < 1e-6) # content birds with basically no steering intention should use their current heading as the "intended direction"
    if weak_intent.any():
        vmag = np.linalg.norm(vel, axis=-1, keepdims=True)
        intended_dir[weak_intent] = (vel / np.maximum(vmag, 1e-6))[weak_intent]

    wind_gain = WIND_RESPONSE_GAIN[bstate][:, np.newaxis] # (N,1) per-state gain, indexed like STATE_PARAMS
    f_wind = compute_wind_response(
        wind, intended_dir, config.v_max, config.mass,
        config.tau_wind, wind_gain,
    )
    desired = desired + f_wind

    # ADD RANDOM FORCE (instead of heading noise)
    noise_vec = rng.randn(N, 3)
    noise_vec = noise_vec / np.maximum(np.linalg.norm(noise_vec, axis=-1, keepdims=True), 1e-6)
    desired = desired + config.w_noise * noise_vec
    
    # PHYSICS SUB-STEPPING = flight physics are integrated at finer resolution than bird steering
    # steering forces are fixed for this timestep, representing the bird's reaction time
    # TODO: expand physics rigor of this approach

    # constants
    m = config.mass # bird mass (kg)
    g = config.gravity # gravity const (m/s^2)
    v0 = config.cruise_speed # cruise speed (m/s)
    cl_cd = config.cl_cd_ratio # lift coeff to draf coeff ratio i.e. high = efficient glide, less energy wasted
    tau = config.speed_relaxation # relxation time (s) = how quickly bird returns to its target speed after deviating
    global_up = np.array([0.0, 0.0, 1.0]) # direction of global up
    sub_dt = dt / config.physics_sub_steps 
    
    # NOTE: simplified fixed wing aerodynamics relates lift L, drag D, thrust T produced by bird to current speed v (eqns 15 in H2010)
    # generally when bird flying constant cruise speed v0, net forces = zero
    # our bird only has one thrust setting T0, to find this T0 we consider a perfectly horizontal flight...
    #   net force vertically: lift equals weight L0 = mg
    #   net force horizontally: D0 = T0 i.e. drag equals thrust
    # so our thrust in horizontal flight is T0 = (CD/CL)*m*g
    # thrust magnitude at cruise speed: T0 (thrust) = D0 (drag) = 1/2 rho Sv^2CD
    # but since we say bird only has this one type of thrust, this T0 is what we use always
    # TODO: variable thrusts?
    thrust_mag = (1.0 / cl_cd) * m * g
    
    # copy current state into working variables that will be updated each sub-step
    sub_vel = vel.copy() # (N, 3) airspeed vectors
    sub_pos = pos.copy() # (N, 3) positions
    sub_bank = bank.copy() # (N,) bank angles (rad)
    

    # per-bird roost surface height from heightmap (used for ROOST ground clamping)
    # computed once before sub-stepping, not per sub-step
    roost_hmaps = get_site_heightmaps(config, config.world['roosts'], geo_data, geo_data['grid_origin'])
    if roost_hmaps:
        roost_surface_z_arr, _ = sample_surface_height(roost_hmaps, pos)
    else:
        roost_surface_z_arr = np.full(N, 0.5) # if no roosts, then ground level fallback

    # ROOST friction per sub-step = computed so total friction per dt is consistent regardless of how many sub-steps we use
    roost_friction_per_substep = 0.15 ** (1.0 / config.physics_sub_steps) # target = bird retains 15% of speed per full timestep TODO: remove hardcoded value


    for _ in range(config.physics_sub_steps):
        prev_pos = sub_pos.copy() # store previous position for hard collisions so we can revert position if enter a building

        # NOTE: bird has three axes (e_x = heading/roll axis, e_y = pitch axis, e_z = yaw axis)
        
        sub_speed = np.linalg.norm(sub_vel, axis=-1, keepdims=True) # (N, 1), bird's scalar speed magnitude
        heading = sub_vel / np.maximum(sub_speed, 1e-6) # (N, 3), heading = unit vector in direction of flight = velocity / magnitude
        
        # construct bird's pitch axis at level flight (zero bank)
        ey_level = np.cross(heading, global_up) # (N, 3), cross product of heading/roll axis and global up gives perpendicular pitch/wings axis a level flight
        ey_norm = np.linalg.norm(ey_level, axis=-1, keepdims=True) # normalize e_y to unit vector
        nearly_vertical = (ey_norm < 1e-4).reshape(-1) # check if bird flying nearly vertical
        ey_level = ey_level / np.maximum(ey_norm, 1e-6) # normalize
        if np.any(nearly_vertical): # for nearly-vertical birds, assign arbitrary wing/pitch axis
            ey_level[nearly_vertical] = np.array([0.0, 1.0, 0.0])
        
        ez_level = np.cross(ey_level, heading) # (N, 3), bird's yaw axis cross product of pitch and roll axes
        
        # APPLY BANKING = rotate ey_level and ez_level around the e_x axis (roll axis) by bank angle beta
        cos_b = np.cos(sub_bank)[:, np.newaxis] # (N, 1)
        sin_b = np.sin(sub_bank)[:, np.newaxis] # (N, 1)
        ey_body = cos_b * ey_level - sin_b * ez_level # (N, 3)
        ez_body = sin_b * ey_level + cos_b * ez_level # (N, 3)
        
        # BANKING DYNAMICS

        # NOTE: laterial acceleration a_lateral_i = (F_steering dot e_y_i) / m (eqn 17 in H2010)
        # dot product extracts only part of the steering force that pushes laterally in bird's frame of reference
        # positive = right / negative = left, and forward/back, up/down components ignored here
        lateral_accel = np.sum(desired * ey_body, axis=-1) / m # (N,) signed scalar
        
        # NOTE: roll into the turn, proportional to how hard bird is pushed laterally 
        # tan(β_in) = w_β_in × ‖aₗ‖ × Δt (eqn 18 in H2010) (w is a weight), solve for β_in
        # arctan means roll angle bounded even for large lateral forces
        beta_in = np.sign(lateral_accel) * np.arctan(
            config.w_bank_in * np.abs(lateral_accel) * sub_dt
        ) # (N,) radians, postive = roll right / negative = roll left
        
        # NOTE: roll out toward level flight, proportional to current bank angle
        # tan(β_out) = w_β_out × sin(β) × Δt (eqn 19 in H2010) (w is a weight)
        # sin means maximum restoring force when fully banked, none when level
        beta_out = np.arctan(config.w_bank_out * np.sin(sub_bank) * sub_dt) # (N,)
        
        # NOTE: update bank angle = current + roll in - roll out (eqn 20 in H2010)
        sub_bank = sub_bank + beta_in - beta_out
        sub_bank = np.clip(sub_bank, -config.max_bank_angle, config.max_bank_angle) # (N,), safety clamp to prevent birds from fully inverting
        
        # using updated bank angle, recompute the banked up axis with the new bank angle
        # important because lift direction depends on updated bank
        cos_b = np.cos(sub_bank)[:, np.newaxis] # (N, 1)
        sin_b = np.sin(sub_bank)[:, np.newaxis] # (N, 1)
        ez_body = sin_b * ey_level + cos_b * ez_level # (N, 3) updated bank axis
        
        # FLIGHT FORCES

        speed_scalar = sub_speed.reshape(-1) # (N,), speed as flat array
        speed_ratio_sq = (speed_scalar / v0) ** 2 # (N,), (v_i / v_0)^2 = how fast the bird is relative to cruise speed, squared
        
        # during MURMURATION...
        # lift = (vi/v0)^2 * mg, directed up along bird's local up axis (axis yaw occurs around) (eqn 15c in H2010)
        # i.e. lift increases with speed squared
        # NOTE: when bird is banked, this lift will not be purely upward
        lift_mag = speed_ratio_sq * m * g # (N,), lift magnitude in Newtons
        # this relies on an approximation that C_L (lift coefficient) is constant, which assumes birds keep the same angle of attack (e.g. through wing configuration)
        # at cruise speed v0, bird maintains level flight because v=v0, so L = mg, so everything is fine (lift equals gravity)
        # but this approx has the implication that a bird above cruise speed will rise, bc if vi > v0, L > mg
        # we keep this approximation during MURMURATION since it is what StarDisplay uses

        # during TRANSIT...
        # whereas MURMURATION birds using StarDisplay approximation (constant lift coeff C_L) will cause birds to rise when flying faster than cruise speed,
        # a real bird will adjust its angle-of-attack (flight term: trim) to hold level flight, which requires variable C_L
        # L*(ez_body dot z) = mg
        # this eqn says multiply the lift by the dot of the bird's local z axis dot the world's z axis, i.e. getting L_z, the lift component that actually counteracts gravity
        # re-arranging this eqn, we get:
        # L = mg / (ez_body dot z) = mg/cos(bank) = n * mg, where load factor n = 1/cos(bank)
        # the rest of the lift is oriented horizontally (like in a banked turn), and is what causes the bird to turn in its banked flight
        # the equation there is F_horizontal = L*sin(bank), and since L = mg/cos(bank), we get F_h = mg * sin(bank)/cos(bank) = mg * tan(bank)
        # so the sideways force during a banked turn which causes bird to follow a banked path F = ma -> F_h = mv^2/r = mg * tan(bank)
        # 
        # at cruise speed, both MURMURATION (H2010) and transit models will produce same results, but when not at cruise speed, TRANSIT model is more accurate
        # in this new TRANSIT model, the model bird can maintain level flight regardless of its speed (up to some structural limit)
        # in the MURMURATION (H2010) model, the bird does not have this ability (which basically means bird has no explicit control over its pitch decoupled from its speed)
        # BUT we keep the H2010 model for MURMURATION because that is what metrics are validated against in that state
        if bstate is not None:
            transit_mask = (bstate == TRANSIT)
            if transit_mask.any():
                up_z = np.maximum(ez_body[transit_mask, 2], 1e-3) # vertical component of body-up axis
                # NOTE: as bank angle -> 90 deg, cos(bank) -> 0 and mg/cos(bank) -> infinity
                # the 1e-3 floor + max_load_factor clamp keep it finite
                # physically this ceiling is the wing failing to make enough lift in a steep turn (flight term: stall, i.e. lose lift because critical angle-of-attack exceeded), so the bird can't hold altitude and starts to drop = correct behavior, not just a numeric guard

                lift_mag[transit_mask] = np.minimum(m * g / up_z, config.max_load_factor * m * g)

        f_lift = lift_mag[:, np.newaxis] * ez_body # (N, 3), lift force vector
        
        # drag = (CD/CL) * (vi/v0)^2 * mg, directed back against roll axis (eqn 15c in H2010)
        # drag increases with speed squared
        drag_mag = (1.0 / cl_cd) * speed_ratio_sq * m * g # (N,), drag magnitude in Newtons
        if bstate is not None and 'surface_z' in state: # DESCENT birds flare near surface, and pitch up = increases drag
            descent_mask = (bstate == DESCENT)
            if descent_mask.any():
                alt_above = sub_pos[:, 2] - state['surface_z']
                flare_drag = 1.0 + config.descent_flare_drag * np.clip(1.0 - alt_above / config.descent_slowdown_height, 0.0, 1.0) # drag multiplier
                drag_mag[descent_mask] *= flare_drag[descent_mask]
        f_drag = -drag_mag[:, np.newaxis] * heading # (N, 3), drag force vector, negative because drag opposes motion
        
        # thrust = constant, as mentioned above, balances drag at horizontal cruise speed (eqns 15 in H2010)
        f_thrust = thrust_mag * heading # (N, 3), thrust force vector
        
        # gravity = constant downward
        f_gravity = np.zeros_like(sub_pos) # (N, 3)
        f_gravity[:, 2] = -m * g
        
        f_flight = f_lift + f_drag + f_thrust + f_gravity # (N, 3)
        
        # SPEED CONTROL

        # NOTE: f_si = (m/tau) × (v_0 − v_i) * e_x_i (where tau is timescale for reaching target speed) (eqn 1 in H2010)
        # models bird actively adjusting flapping to reach target speed, target speed depends on behavioral state
        # if bird slower than target, positive force along heading/roll axis, if faster than target, negative force
        speed_error = v_target.reshape(-1) - speed_scalar # (N,), how far from target speed
        f_speed = ((m / tau) * speed_error)[:, np.newaxis] * heading # (N, 3), force along heading/roll axis
        
        # EULER INTEGRATION

        # NOTE: Eq 21: vi(t+Δt) = vi(t) + (1/m)(F_Steering + F_Flight) * Δt (eqn 21 in H2010)
        # all forces summed and divided by mass to get acceleration
        # "desired" =  F_Steering (bird behavioral forces), f_flight (flight dynamics), f_speed (speed control adjustment)
        accel = (desired + f_flight + f_speed) / m # (N, 3), acceleration in m/s^2

        # ROOST birds = on the ground, zero thrust, drag decelerates to stop
        roost_birds = (bstate == ROOST)
        if roost_birds.any():
            accel[roost_birds] = 0.0
            # sub-step-independent friction i.e. total deceleration per dt is consistent regardless of physics_sub_steps count
            sub_vel[roost_birds] *= roost_friction_per_substep
            # freeze when nearly stopped
            roost_speeds = np.linalg.norm(sub_vel[roost_birds], axis=-1)
            stopped = roost_speeds < 0.3
            stopped_indices = np.where(roost_birds)[0][stopped]
            sub_vel[stopped_indices] = 0.0

        # FORAGE birds are grounded, so skip flight physics (update_forage overrides position/velocity)
        forage_grounded = (bstate == FORAGE)
        if forage_grounded.any():
            accel[forage_grounded] = 0.0
            sub_vel[forage_grounded] = 0.0

        sub_vel = sub_vel + accel * sub_dt # (N, 3) updated airspeed vector

        sub_speed_new = np.linalg.norm(sub_vel, axis=-1, keepdims=True) # (N, 1) new speed
        # ROOST birds can slow to zero, all others clamped to v_min
        bird_vmin = np.where(
            ((bstate == ROOST) | (bstate == FORAGE))[:, np.newaxis],
            0.0,
            np.where(
                (bstate == DESCENT)[:, np.newaxis],
                config.v_min_descent,
                config.v_min
            )
        )
        sub_vel = sub_vel / np.maximum(sub_speed_new, 1e-6) * np.clip(
            sub_speed_new, bird_vmin, config.v_max
        ) # (N, 3) direction preserved, magnitude clamped

        # CLIMB-ANGLE LIMIT = a bird cannot fly steeper than max_climb_angle from horizontal
        flying_states = bstate != ROOST
        if flying_states.any():
            horiz_speed = np.linalg.norm(sub_vel[:, :2], axis=-1) # (N,) horizontal speed
            max_vz = horiz_speed * np.tan(config.max_climb_angle) # (N,) allowed |vertical velocity v_z|
            vz = sub_vel[:, 2]
            over = flying_states & (np.abs(vz) > max_vz)
            sub_vel[over, 2] = np.sign(vz[over]) * max_vz[over]   

        # NOTE: pi(t+Δt) = pi(t) + vi(t+Δt) * Δt (eqn 22 in H10)
        # position update, wind added for ground-relative motion (Eq 22)
        # sub_vel (airspeed), wind (air's velocity relative to ground), positions updates by groundspeed because position is in ground coordinates
        sub_pos = sub_pos + (sub_vel + wind) * sub_dt # (N, 3) updated position
        if roost_birds.any(): # roosted birds don't move with wind
                    sub_pos[roost_birds] = prev_pos[roost_birds]
        if forage_grounded.any(): # foraging birds are ground-locked (update_forage handles their motion)
            sub_pos[forage_grounded] = prev_pos[forage_grounded]
        
        # DOMAIN FLOOR = ground plane at config.floor_z but only over open void with no geometry beneath the bird
        # fires where a column has NO solid voxels at all (empty ground inside the grid, or anywhere outside it)
        # shouldn't trigger anywhere there is a valley in geometry, even if below floor_z
        # inelastic = clamp altitude, kill downward airspeed, lift can peel them off
        if geo_data is not None:
            origin = np.array(geo_data['grid_origin'])
            geo = geo_data['geometry'] # (nz, ny, nx), True = solid
            sp = geo_data['grid_spacing']
            gi = ((sub_pos[:, 0] - origin[0]) / sp).astype(int)
            gj = ((sub_pos[:, 1] - origin[1]) / sp).astype(int)
            in_grid = (gi >= 0) & (gi < geo.shape[2]) & (gj >= 0) & (gj < geo.shape[1])
            gi_c = np.clip(gi, 0, geo.shape[2] - 1)
            gj_c = np.clip(gj, 0, geo.shape[1] - 1)
            solid_below = np.zeros(sub_pos.shape[0], dtype=bool)
            solid_below[in_grid] = geo[:, gj_c[in_grid], gi_c[in_grid]].any(axis=0) # any solid in column
            no_ground = ~solid_below # empty column (in-grid void OR outside grid)
        else:
            no_ground = np.ones(sub_pos.shape[0], dtype=bool) # if no geometry at all, then whole domain is void

        below_floor = no_ground & (sub_pos[:, 2] < config.floor_z)
        sub_pos[below_floor, 2] = config.floor_z
        sub_vel[below_floor, 2] = np.maximum(sub_vel[below_floor, 2], 0.0)

        # outdated ground clamp...
        # sub_pos[:, 2] = np.maximum(sub_pos[:, 2], 0.5) # prevent birds from going underground TODO: hardcoded ground clamp?

        # HARD COLLISIONS = axis-by-axis resolution
        # try each axis independently so birds slide along surfaces instead of getting stuck at corners
        if geo_data is not None:
            geo = geo_data['geometry']
            _sp = geo_data['grid_spacing']
            _sp_z = geo_data['grid_spacing_z']
            _origin = np.array(geo_data['grid_origin'])
            
            gi = np.clip(((sub_pos[:, 0] - _origin[0]) / _sp).astype(int), 0, geo.shape[2] - 1)
            gj = np.clip(((sub_pos[:, 1] - _origin[1]) / _sp).astype(int), 0, geo.shape[1] - 1)
            gk = np.clip(((sub_pos[:, 2] - _origin[2]) / _sp_z).astype(int), 0, geo.shape[0] - 1)
            inside = geo[gk, gj, gi]
            
            if np.any(inside):
                hit = np.where(inside)[0]
                
                for idx in hit:
                    # try each axis: revert axes that cause penetration
                    # start from old position, add one axis at a time
                    base = prev_pos[idx].copy()
                    final = sub_pos[idx].copy()
                    resolved = base.copy()
                    
                    for axis in range(3):
                        test = resolved.copy()
                        test[axis] = final[axis]
                        
                        if axis == 0:
                            ti = int(np.clip((test[0] - _origin[0]) / _sp, 0, geo.shape[2] - 1))
                            tj = int(np.clip((resolved[1] - _origin[1]) / _sp, 0, geo.shape[1] - 1))
                            tk = int(np.clip((resolved[2] - _origin[2]) / _sp_z, 0, geo.shape[0] - 1))
                        elif axis == 1:
                            ti = int(np.clip((resolved[0] - _origin[0]) / _sp, 0, geo.shape[2] - 1))
                            tj = int(np.clip((test[1] - _origin[1]) / _sp, 0, geo.shape[1] - 1))
                            tk = int(np.clip((resolved[2] - _origin[2]) / _sp_z, 0, geo.shape[0] - 1))
                        else:
                            ti = int(np.clip((resolved[0] - _origin[0]) / _sp, 0, geo.shape[2] - 1))
                            tj = int(np.clip((resolved[1] - _origin[1]) / _sp, 0, geo.shape[1] - 1))
                            tk = int(np.clip((test[2] - _origin[2]) / _sp_z, 0, geo.shape[0] - 1))
                        
                        if not geo[tk, tj, ti]:
                            resolved[axis] = final[axis]  # this axis is clear
                        else:
                            sub_vel[idx, axis] = 0.0  # blocked on this axis
                    
                    sub_pos[idx] = resolved
    
    # copy sub-stepped results back to main state variables
    new_pos = sub_pos # final positions after all sub-steps
    vel_air = sub_vel # final airspeed vectors after all sub-steps
    new_bank = sub_bank # final bank angles after all sub-steps

    # UPDATE INTERNAL STATES
    
    # energy depletes during flight with cost proportional to airspeed^3
    airspeed = np.linalg.norm(vel_air, axis=-1) # (N,)
    flight_cost = (airspeed / config.v_max) ** config.energy_drain_speed_exponent
    new_energy = energy - traits['energy_drain_rate'] * flight_cost * dt # different birds have personal energy drain rates
    
    # roosting birds recover energy
    roosting = (bstate == ROOST)
    new_energy[roosting] += 0.05 * dt # slow recovery at roost TODO: add this value to the config
    new_energy = np.clip(new_energy, 0.0, 1.0)

    # AFFECTIVE STATE UPDATE = valence/arousal from additive influences
    # each influence pushes a (d_valence, d_arousal) onto the TARGET, then the smoothed state relaxes toward that target 
    # valence takes the sign of an influence, arousal takes its magnitude
    g = AFFECT_GAINS
    valence_target = np.zeros(N)
    arousal_target = np.zeros(N)

    # baseline = mild positive pull toward contentment when nothing is wrong
    valence_target += g['calm_baseline'][0]

    # ENVIRONMENT = pollution/noise are bad TODO: rate of change?
    # per-bird sensitivity scales how strongly the environment moves each bird
    if env is not None:
        neg_gain = (2.0 - traits['valence_disposition']) # e.g. inherently low valence birds perceive bad environment as more unpleasant than "optimistic" birds
        poll = env['pollution'] * neg_gain
        nois = env['noise'] * neg_gain
        valence_target += g['pollution'][0] * poll + g['noise'][0] * nois
        arousal_target += g['pollution'][1] * poll + g['noise'][1] * nois

    # PREDATOR = threat is very bad and very activating (fear = negative valence + high arousal)
    valence_target += g['predator'][0] * threat
    arousal_target += g['predator'][1] * threat

    # LOW ENERGY = depletion drags valence down (feeling worn out), doesn't arouse
    depletion = np.clip(1.0 - new_energy, 0.0, 1.0)
    valence_target += g['low_energy'][0] * depletion

    # MANEUVERING = magnitude of steering force = how hard the bird is working
    # normalized by a rough reference so the gain stays interpretable
    steer_mag = np.linalg.norm(desired, axis=-1) / (config.w_predator_avoidance + 1e-6)
    arousal_target += g['maneuvering'][1] * np.clip(steer_mag, 0.0, 1.0)

    # FLOCK TURBULENCE = how much the bird's neighbors disagree in heading
    # high local velocity variance = being jostled = activating
    if N > 1 and visibility_mask is not None:
        nb_vel = vel[nb_idx] # (N, k, 3) neighbor velocities
        vel_var = np.var(nb_vel, axis=1).sum(axis=-1) # (N,) scalar spread of neighbor velocities
        turbulence = np.clip(vel_var / (config.v_max ** 2), 0.0, 1.0)
        arousal_target += g['flock_turbulence'][1] * turbulence

    # per-bird excitability scales the whole arousal response
    arousal_target = arousal_target * traits['arousal_excitability']

    # clamp targets to their natural ranges (valence signed, arousal unsigned)
    valence_target = np.clip(valence_target, -1.0, 1.0)
    arousal_target = np.clip(arousal_target,  0.0, 1.0)

    # RELAX toward target with per-axis time constant (exponential smoothing)
    # arousal faster (short tau), valence slower (long tau) = mood vs reflex NOTE: justify?
    # valence_disposition couples into valence recovery i.e. optimistic birds (>1) use a shorter effective tau (recover faster), pessimistic birds a longer one
    eff_tau_valence = config.tau_valence / traits['valence_disposition']
    new_valence = valence + (valence_target - valence) * (dt / eff_tau_valence)
    new_arousal = arousal + (arousal_target - arousal) * (dt / config.tau_arousal)
    new_valence = np.clip(new_valence, -1.0, 1.0)
    new_arousal = np.clip(new_arousal,  0.0, 1.0)
    
    # UPDATE BEHAVIORAL STATES (environment-driven)
    new_bstate = update_states(
        new_pos, bstate, time + dt, config,
        env=env, energy=new_energy, rng=rng, wave_rand=wave_rand, outbound=outbound
    )
    # OUTBOUND FLAG i.e. a bird that just left the roost (ROOST -> TRANSIT at dawn) is now heading out to its forage site
    # mark it so transit steering sends it there, not back to the roost
    new_outbound = outbound.copy()
    new_outbound[(bstate == ROOST) & (new_bstate == TRANSIT)] = True

    # DUSK DEPARTURE = give returning foragers an initial velocity toward roost
    # (NOTE: this is bc they have vel=0 from ground foraging, but flight physics needs a non-zero heading)
    dusk_departing = (bstate == FORAGE) & (new_bstate == TRANSIT)
    if dusk_departing.any():
        roost_center = np.array(config.world['roosts'][0]['center'])
        to_roost = roost_center[:2] - new_pos[dusk_departing, :2]
        to_roost_dist = np.maximum(np.linalg.norm(to_roost, axis=1, keepdims=True), 1e-6) # distance to roost, floor prevents division by zero
        to_roost_dir = to_roost / to_roost_dist # unit vector pointing from each bird toward the roost

        # set horizontal velocity toward the roost at the minimum flight speed
        vel_air[dusk_departing, 0] = to_roost_dir[:, 0] * config.v_min
        vel_air[dusk_departing, 1] = to_roost_dir[:, 1] * config.v_min
        
        vel_air[dusk_departing, 2] = 1.0 # upward component to get airborne
        # reset forage timers for clean re-entry on the next day
        forage_hop_timer[dusk_departing] = 0.0
        forage_dwell[dusk_departing] = 0.0
        forage_mode[dusk_departing] = 0 # reset to extensive search for the next foraging visit
        forage_giveup[dusk_departing] = 0

    # DESCENT -> ROOST: birds land when they touch the actual surface below the roost
    # surface height comes from the heightmap (drapes roost onto geometry below it)
    # supports multiple roosts bc each bird checks its closest roost's surface
    descent_mask = (new_bstate == DESCENT)
    if descent_mask.any() and roost_hmaps:
        # get the actual surface height below each descending bird
        surface_z, closest_ri = sample_surface_height(roost_hmaps, new_pos)
        height_above_surface = new_pos[:, 2] - surface_z

        # check if bird is within its closest roost's footprint TODO: closest roost vs optimal roost
        # birds outside the footprint stay in DESCENT and circle back via roost pull
        within_footprint = np.zeros(N, dtype=bool)
        for ri in range(len(roost_hmaps)):
            hmap = roost_hmaps[ri]
            mask = (closest_ri == ri) & descent_mask # only check descending birds for this roost
            if not mask.any():
                continue
            # project bird position into roost-local coordinates
            rel = new_pos[mask] - hmap['center']
            u = rel @ hmap['forward']  # along roost length
            v = rel @ hmap['side'] # along roost width
            half_len = hmap['size'][0] / 2.0
            half_wid = hmap['size'][1] / 2.0
            # bird is within footprint if inside the rectangle
            within = (np.abs(u) < half_len) & (np.abs(v) < half_wid)
            within_footprint[np.where(mask)[0]] = within

        # bird lands only if it is in DESCENT + within roost footprint + close to surface
        tol = config.roost_land_tolerance
        touched_surface = descent_mask & within_footprint & (height_above_surface < tol) & (height_above_surface > -tol)
        # snap landed birds to the surface and transition to ROOST
        landed_indices = np.where(touched_surface)[0]
        if len(landed_indices) > 0:
            new_pos[landed_indices, 2] = surface_z[landed_indices] # place exactly on surface
            new_bstate[landed_indices] = ROOST

    # FORAGE arrival, landing, ground feeding
    forage_sites = config.world.get('forage_sites', []) if config.world else []
    if forage_sites:
        forage_centers = np.array([s['center'] for s in forage_sites])
        forage_sizes = np.array([s['size'] for s in forage_sites])
        assigned_center = forage_centers[np.clip(forage_site, 0, len(forage_sites) - 1)] # (N,3) assigned site centre
        assigned_size = forage_sizes[np.clip(forage_site, 0, len(forage_sites) - 1)] # (N,2) assigned site size
        horizontal_distance = np.linalg.norm(new_pos[:, :2] - assigned_center[:, :2], axis=1)

        # TRANSIT -> DESCENT = outbound bird arrives over its site footprint, begins descending
        arriving = new_outbound & (new_bstate == TRANSIT) & (horizontal_distance < np.maximum(assigned_size[:, 0], assigned_size[:, 1]) * config.forage_arrival_frac)
        new_bstate[arriving] = DESCENT

        # DESCENT -> FORAGE: outbound bird has descended to ground level inside its footprint, beings feeding
        forage_heightmaps = get_site_heightmaps(config, forage_sites, geo_data, np.array(geo_data['grid_origin']))
        forage_surface, _ = sample_surface_height(forage_heightmaps, new_pos) # ground height under each bird
        within = (np.abs(new_pos[:, 0] - assigned_center[:, 0]) < assigned_size[:, 0] * 0.5) & (np.abs(new_pos[:, 1] - assigned_center[:, 1]) < assigned_size[:, 1] * 0.5)
        landed = new_outbound & (new_bstate == DESCENT) & within & ((new_pos[:, 2] - forage_surface) < config.forage_land_tolerance)
        new_bstate[landed] = FORAGE
        new_outbound[landed] = False # arrived, so no longer outbound (after foraging is complete it will be flying inbound back toward roost)

        # ground foraging = area-restricted search on a spatial food field
        forage_mask = (new_bstate == FORAGE)
        if forage_mask.any():
            new_pos, vel_air, food_fields, new_energy, forage_heading, forage_mode, forage_giveup, forage_dwell, forage_hop_timer = update_forage(
                pos, new_pos, vel_air, forage_mask, forage_site, food_fields, forage_surface,
                new_energy, forage_heading, forage_mode, forage_giveup, forage_dwell, forage_hop_timer, config, rng
            )
            new_bank[forage_mask] = 0.0 # grounded birds should have level wings, flight physics still evolves bank for them each sub-step, so zero the leftover to prevent the viewer from tilting them

    # ASSEMBLE AND RETURN
    return {
        'pos': new_pos,
        'vel': vel_air,
        'bank': new_bank,
        'bstate': new_bstate,
        'energy': new_energy,
        'valence': new_valence,
        'arousal': new_arousal,
        'forage_site': forage_site,
        'wave_rand': wave_rand,
        'outbound': new_outbound,
        'food_fields': food_fields,
        'forage_heading': forage_heading,
        'forage_mode': forage_mode,
        'forage_dwell': forage_dwell,
        'forage_hop_timer': forage_hop_timer,
        'time': time + dt,
        'rng': rng,
        'traits': traits,
        'identity': state['identity'],
    }