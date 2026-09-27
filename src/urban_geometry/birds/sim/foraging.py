"""
foraging.py = terrestrial feeding dynamics for birds in the FORAGE state

movement model = discrete hop/dwell area-restricted search (ARS)
Each bird cycles through:
  - DWELL = standing still for ars_dwell_time, probing/feeding in place
  - HOP = a ballistic jump lasting ars_hop_duration seconds, the bird moves along it heading with a parabolic height arc, over multiple sim steps

ARS = discretized as a correlated random walk: each hop draws a random turn angle around the bird's current heading, with the spread differing between extensive and intensive search
    - EXTENSIVE = narrow hop-turns i.e. nearly straight, covers ground
    - INTENSIVE = wide hop-turns i.e. reorients a lot, explores the same patch
- this is a form of klinokinesis, as turning is modulated by food encounters
    - extensive -> intensive transition when a hop lands on area with food above ars_food_threshold area
    - intensive -> extensive transition when more than ars_giveup_hops consecutive hops are foodless landings (giving-up time)
- local enhancement = an extensive bird biases its hop heading toward the centroid of feeding (intensive) birds at its site
"""

import numpy as np

# ----
# SPATIAL FOOD FIELD (per-site 2D grid)

def init_food_field(site, config, site_index):
    """
    Create a 2D food-density grid for one site
    - field is initialized with randomly positioned Gaussian food patches
    - uses the simulation seed and site index to give each site a reproducible but independent food distribution

    Args:
        site: forage-site configuration/geometry
        config: SimConfig
        site_index: integer index of the forage site, used to derive its random seed

    Returns:
        field: dict containing the food grid, site center, site size, and grid resolution
    """
    resolution = config.food_field_resolution
    food = np.zeros((resolution, resolution), dtype=np.float32)

    # seed per site so each gets its own repeatable food pattern
    rng = np.random.RandomState(config.seed + site_index)

    size = site['size']
    area = float(size[0] * size[1])

    # number of blobs scales with site area, so bigger sites get more blobs (rather than the same number of bigger blobs)
    n_patches = max(1, int(round(config.food_patch_density * area)))

    # fixed-resolution grid is stretched to fill the site, so meters-per-cell differs per axis
    # convert the metric sigma to per-axis cell sigma (isotropic in meters -> anisotropic in cells on non-square sites)
    m_per_cell_x = size[0] / resolution
    m_per_cell_y = size[1] / resolution
    sigma_x = config.food_patch_sigma_m / max(m_per_cell_x, 1e-6)
    sigma_y = config.food_patch_sigma_m / max(m_per_cell_y, 1e-6)

    yy, xx = np.mgrid[0:resolution, 0:resolution]

    # each patch is a Gaussian blob, overlapping patches add together
    for _ in range(n_patches):
        patch_cx = rng.randint(0, resolution)
        patch_cy = rng.randint(0, resolution)
        peak = 0.5 + rng.rand() * 0.5 # random peak density in [0.5, 1.0)
        food += peak * np.exp(-(((xx - patch_cx) ** 2) / (2.0 * sigma_x ** 2) +
                                ((yy - patch_cy) ** 2) / (2.0 * sigma_y ** 2)))

    return np.clip(food, 0.0, 1.0) # overlaps can exceed 1, cap to valid range


def _world_to_grid(bird_xy, site_center, site_size, resolution):
    """
    Convert world-space (x, y) positions to integer food-grid indices
    - positions are mapped into the site's 2D grid and clipped to the valid grid range so that boundary positions produce valid indices
    """

    # shift world coordinates so that the site's lower-left corner becomes (0, 0)
    half_size = np.array(site_size) * 0.5
    rel_x = bird_xy[:, 0] - (site_center[0] - half_size[0])
    rel_y = bird_xy[:, 1] - (site_center[1] - half_size[1])

    # convert the relative position from world units to grid-cell indices
    # clipping keeps birds exactly on/outside a boundary from producing invalid indices
    grid_x = np.clip((rel_x / site_size[0]) * resolution, 0, resolution - 1).astype(int)
    grid_y = np.clip((rel_y / site_size[1]) * resolution, 0, resolution - 1).astype(int)
    return grid_x, grid_y


def sample_food(food_grid, bird_xy, site_center, site_size):
    """
    Return the food density at each bird's world-space (x, y) position
    - returns one food-density value per bird, with values in [0, 1]

    Args:
        food_grid: 2D food-density grid
        bird_xy: (N, 2) array, bird positions in world-space (meters)
        site_center: (2,) array, forage-site center in world space (meters)
        site_size: (2,) array, forage-site width and height (meters)

    Returns:
        values: (N,) array, food density at each bird's position
    """
    grid_x, grid_y = _world_to_grid(bird_xy, site_center, site_size, food_grid.shape[0])
    return food_grid[grid_y, grid_x]


def deplete_food(food_grid, bird_xy, site_center, site_size, amount):
    """
    Deplete food at each bird's current grid cell, modifying the field in place
    - if multiple birds occupy the same cell, each bird contributes its own depletion

    Args:
        food_grid: 2D food-density grid
        bird_xy: (N, 2) array, bird positions in world-space (meters)
        site_center: (2,) array, forage-site center in world space (meters)
        site_size: (2,) array, forage-site width and height (meters)
        amount: float, food density removed per bird

    Returns:
        None
    """
    grid_x, grid_y = _world_to_grid(bird_xy, site_center, site_size, food_grid.shape[0])

    # subtract at each sampled cell, including repeated indices: multiple birds probing the same cell each contribute their own depletion
    np.subtract.at(food_grid, (grid_y, grid_x), amount)
    np.clip(food_grid, 0.0, 1.0, out=food_grid)

def _blend_heading(heading_a, heading_b, weight):
    """
    Blend two heading angles by `weight` using circular interpolation
    - the angles are converted to unit vectors before blending so that the -pi/pi boundary is handled correctly
    """

    # convert angles to unit vectors before blending, so headings near +/-pi are treated as adjacent directions rather than numerically far apart
    ax, ay = np.cos(heading_a), np.sin(heading_a)
    bx, by = np.cos(heading_b), np.sin(heading_b)
    return np.arctan2(ay * (1 - weight) + by * weight,
                      ax * (1 - weight) + bx * weight)


# ----
# HOP-AND-DWELL AREA-RESTRICTED SEARCH (the main update)

def update_forage(pos, new_pos, vel, forage_mask, forage_site, food_fields, surf_z,
                  energy, heading, mode, giveup_counter, dwell_timer, hop_timer,
                  config, rng):
    """
    Advance all FORAGE birds by one simulation timestep
    - birds alternate between:
        - DWELL: remain stationary while feeding/probing if intensive
        - HOP: move ballistically along a fixed heading
    - when a hop ends, the landing is evaluated for food
    - food encounters can switch a bird from extensive to intensive search
    - repeated foodless landings eventually trigger the giving-up transition back to extensive search
    - extensive birds may also bias their next hop toward intensive feeding birds at their site

    Args:
        pos: (N, 3) array, current bird positions in 3D space (meters)
        new_pos: (N, 3) array, output bird positions
        vel: (N, 3) array, bird velocities
        forage_mask: (N,) boolean array, birds currently in FORAGE state
        forage_site: (N,) integer array, assigned forage-site index for each bird
        food_fields: list of per-site food-field dictionaries
        surf_z: (N,) array, ground-surface height for each bird (meters)
        energy: (N,) array, bird energy values in [0, 1]
        heading: (N,) array, current horizontal hop headings (radians)
        mode: (N,) integer array, ARS mode (0 = extensive, 1 = intensive)
        giveup_counter: (N,) array, consecutive foodless landing count
        dwell_timer: (N,) array, remaining dwell time (seconds)
        hop_timer: (N,) array, remaining hop time (seconds)
        config: SimConfig
        rng: random-number generator

    Returns:
        tuple containing new_pos, vel, food_fields, energy, heading, mode, giveup_counter, dwell_timer, hop_timer: updated simulation state
    """

    # nothing to update if there are no birds currently in FORAGE
    if not forage_mask.any():
        return (new_pos, vel, food_fields, energy, heading, mode,
                giveup_counter, dwell_timer, hop_timer)

    # work with the indices of FORAGE birds so the rest of the update can stay vectorized
    forage_idx = np.where(forage_mask)[0]

    # default: every forager holds position on the ground, dwelling
    # BUT active hops overwrite these values with their airborne position and horizontal velocity
    new_pos[forage_idx] = pos[forage_idx]
    new_pos[forage_idx, 2] = surf_z[forage_idx]
    vel[forage_idx] = 0.0

    # DWELL COUNTDOWN
    # only birds that are not currently hopping count down their dwell timer
    # a hop thus pauses the dwell countdown until the bird lands
    dwelling = forage_mask & (hop_timer <= 0.0)
    dwell_timer[dwelling] -= config.dt

    # START NEW HOPS 
    # birds whose dwell has expired are ready to choose a new hop
    # so choose the hop heading (based on turn + enhancement + boundary reflection)
    starting = dwelling & (dwell_timer <= 0.0)
    start_idx = np.where(starting)[0]

    if len(start_idx) > 0:

        # cache each starting bird's current search mode and site for the hop decision
        # mode 0 = extensive search; mode 1 = intensive search
        start_mode = mode[start_idx]
        start_site = forage_site[start_idx]
        is_extensive = (start_mode == 0)

        # draw the turn from a zero-mean Gaussian: extensive search produces relatively straight hops, while intensive search produces wider turns
        turn_sigma = np.where(is_extensive, config.ars_turn_extensive, config.ars_turn_intensive)
        new_heading = heading[start_idx] + rng.randn(len(start_idx)) * turn_sigma

        # LOCAL ENHANCEMENT = extensive birds bias their hop heading toward feeding neighbours
        for site_idx in range(len(food_fields)): # process each site separately
            feeders_here = forage_mask & (forage_site == site_idx) & (mode == 1)
            if not feeders_here.any():
                continue

            # use the mean position of intensive feeders as the local attraction point
            feeding_centroid = pos[feeders_here, :2].mean(axis=0)

            # only extensive birds are socially biased, since intensive birds are already exploiting a patch
            biased = is_extensive & (start_site == site_idx)
            if not biased.any():
                continue

            # compute the direction from each extensive bird to the local feeding group
            to_group = feeding_centroid - pos[start_idx[biased], :2]
            heading_to_group = np.arctan2(to_group[:, 1], to_group[:, 0])

            # partially rotate the ARS-chosen heading toward the feeding group
            # ars_enhancement controls how strongly social information overrides the random turn
            new_heading[biased] = _blend_heading(new_heading[biased], heading_to_group,
                                                 config.ars_enhancement)

        # BOUNDARY
        # predict the landing point before committing to the hop, so we can reflect the heading if the full hop would cross the site boundary
        hop_length = np.where(is_extensive, config.ars_hop_extensive, config.ars_hop_intensive)
        predicted_x = pos[start_idx, 0] + np.cos(new_heading) * hop_length
        predicted_y = pos[start_idx, 1] + np.sin(new_heading) * hop_length

        # check boundaries separately for each site because each site has its own rectangle
        for site_idx in range(len(food_fields)):
            here = (start_site == site_idx)
            if not here.any():
                continue
            field = food_fields[site_idx]
            cx, cy = field['center'][0], field['center'][1]
            half_w, half_h = field['size'][0] * 0.5, field['size'][1] * 0.5

            # identify hops whose predicted landing point crosses each pair of walls
            out_x = here & ((predicted_x < cx - half_w) | (predicted_x > cx + half_w))
            out_y = here & ((predicted_y < cy - half_h) | (predicted_y > cy + half_h))
            new_heading[out_x] = np.pi - new_heading[out_x] # reflect across the x wall
            new_heading[out_y] = -new_heading[out_y] # reflect across the y wall

        heading[start_idx] = new_heading # commit the newly chosen heading and start the hop clock
        hop_timer[start_idx] = config.ars_hop_duration # the heading then stays fixed for the duration of this ballistic hop

    # ADVANCE ALL ACTIVE HOPS = move along heading + parabolic height arc
    # horizontal speed = hop_length / hop_duration; height = 4*h*t*(1-t) (peak mid-hop)
    # unlike the dwell phase, hopping updates position continuously each simulation step
    hopping = forage_mask & (hop_timer > 0.0)
    hop_idx = np.where(hopping)[0]

    if len(hop_idx) > 0:

        # hop distance is determined by the search mode selected when the hop began
        hop_mode = mode[hop_idx]
        hop_length = np.where(hop_mode == 0, config.ars_hop_extensive, config.ars_hop_intensive)
        hop_speed = hop_length / max(config.ars_hop_duration, 1e-6) # ground speed during the hop

        # advance along the fixed hop heading by one simulation timestep
        step_dx = np.cos(heading[hop_idx]) * hop_speed * config.dt
        step_dy = np.sin(heading[hop_idx]) * hop_speed * config.dt
        new_pos[hop_idx, 0] = pos[hop_idx, 0] + step_dx
        new_pos[hop_idx, 1] = pos[hop_idx, 1] + step_dy

        # ballistic height = progress t in [0,1] through the hop, parabola peaking mid-hop
        hop_timer[hop_idx] -= config.dt
        progress = 1.0 - np.clip(hop_timer[hop_idx], 0.0, None) / config.ars_hop_duration # convert the remaining hop time into normalized elapsed progress [0, 1]
        arc_height = config.ars_hop_height * 4.0 * progress * (1.0 - progress) # 4t(1-t) is zero at takeoff/landing and reaches 1 at the midpoint, giving the hop a smooth symmetric arc
        new_pos[hop_idx, 2] = surf_z[hop_idx] + arc_height

        # velocity aligned with the hop so the viewer orients the bird along its jump
        vel[hop_idx, 0] = np.cos(heading[hop_idx]) * hop_speed
        vel[hop_idx, 1] = np.sin(heading[hop_idx]) * hop_speed
        vel[hop_idx, 2] = 0.0 # no vertical velocity, so viewer applies no pitch

        # LANDINGS
        # birds whose hop timer reached zero have completed their hop and now make the next ARS search/feeding decision
        landed = hop_idx[hop_timer[hop_idx] <= 0.0]
        if len(landed) > 0:
            new_pos[landed, 2] = surf_z[landed] # feet on the ground
            vel[landed] = 0.0

            # record whether each landing finds food above the ARS threshold
            # this result drives both the giving-up counter and mode switching
            landed_site = forage_site[landed]
            landed_found = np.zeros(len(landed), dtype=bool)
            for site_idx in range(len(food_fields)):
                here = (landed_site == site_idx)
                if not here.any():
                    continue
                field = food_fields[site_idx]

                # probe food at the actual landing position, rather than at the bird's position before the hop.
                xy = new_pos[landed[here], :2]
                food_here = sample_food(field['grid'], xy, field['center'], field['size'])

                # landing counts as a food encounter only if density exceeds the ARS threshold
                landed_found[here] = (food_here > config.ars_food_threshold)
                deplete_food(field['grid'], xy, field['center'], field['size'],
                             config.ars_depletion_per_probe) # probe the landing area and deplete some of its food

            # giving-up bookkeeping + ARS mode switch (a landing = one search decision)
            # successful landings reset giving-up time
            # unsuccessful landings add one consecutive foodless hop to the counter
            giveup_counter[landed] = np.where(landed_found, 0, giveup_counter[landed] + 1)
            went_intensive = (mode[landed] == 0) & landed_found # finding food switches an extensive-search bird into intensive search
            mode[landed[went_intensive]] = 1
            went_extensive = (mode[landed] == 1) & (giveup_counter[landed] > config.ars_giveup_hops) # after enough consecutive foodless landings, an intensive bird gives up on the current patch and returns to extensive search
            mode[landed[went_extensive]] = 0

            # randomize the next dwell duration so nearby birds do not repeatedly synchronize their hop cycles
            dwell_timer[landed] = config.ars_dwell_time * (0.5 + rng.rand(len(landed)))

    # FEEDING DURING DWELL = intensive birds feed at current area, gaining energy in proportion to local food density, and continuously depleting the food in that area
    # NOTE: has crowding interference
    # only landed intensive birds feed, since extensive birds are searching rather than exploiting
    dwell_feeding = forage_mask & (hop_timer <= 0.0) & (mode == 1)
    for site_idx in range(len(food_fields)):
        feeders = np.where(dwell_feeding & (forage_site == site_idx))[0]
        n_feeding = len(feeders)
        if n_feeding == 0:
            continue
        field = food_fields[site_idx]
        xy = new_pos[feeders, :2]
        food_here = sample_food(field['grid'], xy, field['center'], field['size'])

        # share the available feeding opportunity among birds at the same site i.e. doubling the number of feeders reduces per-bird intake by sqrt(2)
        interference = 1.0 / np.sqrt(n_feeding) # per-bird intake falls with crowding

        # intake scales with local food density and is reduced by crowding, while energy remains bounded to the model's [0, 1] range
        energy[feeders] = np.clip(
            energy[feeders] + config.ars_energy_intake * food_here * interference, 0.0, 1.0)
        
        deplete_food(field['grid'], xy, field['center'], field['size'],
                     config.ars_depletion_per_probe * config.dt) # continuous feeding depletes the patch gradually while birds remain dwelling

    # FOOD PATCH RECOVERY
    # all food patches recover continuously each timestep, regardless of whether birds are currently feeding on them.
    for field in food_fields:
        field['grid'] = np.clip(field['grid'] + config.ars_food_recovery * config.dt, 0.0, 1.0) # clip keeps recovery from pushing density above the valid [0, 1] range

    return (new_pos, vel, food_fields, energy, heading, mode,
            giveup_counter, dwell_timer, hop_timer)