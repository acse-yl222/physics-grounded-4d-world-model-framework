"""
routing.py = wave-based navigation field (first-arrival-time) toward the roost
"""

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.ndimage import map_coordinates

_arrival_cache = {} # static field -> compute once per run
_gradient_cache = {} # precomputed gradients of T, keyed same as _arrival_cache

def build_arrival_time_field(geo_data, origin, roost_centers, config, wind_time=0.0):
    """
    Discrete cost-to-go field T = minimum accumulated routing cost from each cell to the roost
    - solves a discretized Zermelo navigation problem (min-time to a goal through a current (in this case wind) field
    - uses 26-connected voxel grid i.e. directed edge cost = time to fly that edge given the wind
      - tailwinds are cheap, reduce travel time
      - unbeatable headwinds are impassable
    - directed-graph (Dijkstra) approximation of the anisotropic static Hamilton-Jacobi / eikonal equation
      - provides a discrete minimum-time formulation related to the paper's advective wave model (eqns 1—4), rather than solving PDE directly
      - a more accurate numerical method for the anisotropic eikonal problem would be the Ordered Upwind Method (OUM), but the graph approximation is sufficient for the resolution and scope of this simulation
    - trajectories follow -grad T toward decreasing time-to-roost
      - this is analogous to the paper's gradient-based trajectory extraction (eqns 8—11)
    - isotropic penalties are implemented as edge-cost shaping (i.e. each edge between two neighboring voxels is assigned a numerical cost)
      - analogous to the paper's cost-field formulation (eqns 10—11)

    Args:
        geo_data: dict, voxel geometry and grid spacing
        origin: (3,) array, world-space origin of the voxel grid (meters)
        roost_centers: list of (x, y, z) roost center positions (meters)
        config: SimConfig
        wind_time: float, time at which the wind field is evaluated (seconds)

    Returns:
        T: (nz, ny, nx) array, minimum accumulated routing cost from each voxel to the nearest roost
    """
    geo = geo_data['geometry'] # (nz, ny, nx) bool, True = solid
    sp = geo_data['grid_spacing']
    sp_z = geo_data['grid_spacing_z']
    nz, ny, nx = geo.shape
    
    # build the set of traversable voxels and assign each voxel a unique graph index
    # the routing problem is represented as a graph, free voxels are nodes, and neighboring free voxels are connected by directed flight edges
    free = ~geo
    idx = np.arange(nz * ny * nx).reshape(nz, ny, nx)

    # each voxel is represented by its physical center coordinates
    # these are used below to evaluate environmental fields and to define the altitude-dependent cost
    z_centers = origin[2] + (np.arange(nz) + 0.5) * sp_z

    # mark additional cells below the simulated ground/floor as inaccessible
    # this must match the collision geometry used by the simulation so that the routing field does not guide birds into regions they cannot physically enter
    # i.e. -grad T never points into void a bird can't enter
    column_has_solid = geo.any(axis=0) # (ny, nx)
    blocked_floor = (~column_has_solid)[None, :, :] & (z_centers < config.floor_z)[:, None, None]
    free = free & ~blocked_floor

    # construct an isotropic (aka effect same in every direction) cost multiplier
    # these preferences do not depend on travel direction = altitude/pollution/noise simply make traversing a region more or less costly
    pref = np.ones_like(geo, dtype=float)

    # evaluate environmental fields at every voxel center when any spatially varying routing preference is enabled
    need_fields = config.route_use_wind or config.route_use_pollution or config.route_use_noise
    if need_fields:
        gx_c = origin[0] + (np.arange(nx) + 0.5) * sp
        gy_c = origin[1] + (np.arange(ny) + 0.5) * sp
        gxx, gyy, gzz = np.meshgrid(gx_c, gy_c, z_centers, indexing='ij') # (nx,ny,nz)
        cell_pos = np.stack([gxx, gyy, gzz], axis=-1).reshape(-1, 3)

    # pollution and noise modify the traversal cost but do not make a direction physically impossible (unlike wind, which can make a direction impossible)
    if config.route_use_pollution or config.route_use_noise:
        from urban_geometry.birds.sim.environment import get_environment
        env = get_environment(cell_pos, wind_time, config)
        if config.route_use_pollution:
            poll = np.clip(env['pollution'], 0.0, 1.0).reshape(nx, ny, nz).transpose(2, 1, 0)
            pref = pref * (1.0 + config.route_pollution_cost * poll)
        if config.route_use_noise:
            noise = np.clip(env['noise'], 0.0, 1.0).reshape(nx, ny, nz).transpose(2, 1, 0)
            pref = pref * (1.0 + config.route_noise_cost * noise)

    # evaluate the wind field used by the Zermelo navigation model
    # unlike the isotropic preferences above, wind is directional = the travel time from A to B can differ from the travel time from B to A
    if config.route_use_wind:
        from urban_geometry.birds.sim.wind import get_wind
        w = get_wind(cell_pos, wind_time, config) # (nx*ny*nz, 3)
        w_grid = w.reshape(nx, ny, nz, 3).transpose(2, 1, 0, 3) # (nz,ny,nx,3) world x,y,z
    else:
        w_grid = np.zeros((nz, ny, nx, 3))
    
    # the bird's airspeed is fixed at v_air
    # the wind changes the resulting ground speed in each chosen direction, rather than changing the bird's airspeed
    v_air = config.v_max # airspeed budget for routing

    # construct the directed flight graph (26-connectivity directed Zermelo edges)
    # each free voxel is connected to its 26 neighboring voxels
    # using 26 rather than only the 6 axis-aligned neighbors allows diagonal flight directions and reduces grid-induced metrication error

    # for one voxel offset, compute the physical displacement, its length, and its unit travel direction
    # the same calculation is applied to every occurrence of this offset throughout the grid.
    def offset_edges(offset):
        dz, dy, dx = offset
        disp = np.array([dx * sp, dy * sp, dz * sp_z]) # world (x,y,z) displacement
        length = float(np.linalg.norm(disp))
        d = disp / length # ground-direction unit vector
        sa, sb = [], [] # array slices selecting start points, array slices selecting end points (all for the given offset)
        for ax, o in enumerate(offset): # off is (z,y,x), matching geo axes
            N = geo.shape[ax]
            if o == 0:   sa.append(slice(0, N));     sb.append(slice(0, N))
            elif o > 0:  sa.append(slice(0, N - 1)); sb.append(slice(1, N))
            else:        sa.append(slice(1, N));     sb.append(slice(0, N - 1))
        sa, sb = tuple(sa), tuple(sb)
        both_free = free[sa] & free[sb] # whether both endpoints of edge are free vs occupied

        # approximate the wind along this edge using the average wind at its endpoints
        # this gives a single representative wind vector for the flight from A to B
        wavg = 0.5 * (w_grid[sa] + w_grid[sb]) # (...,3)

        # decompose the wind into components parallel and perpendicular to the desired ground direction
        # the parallel component helps or opposes progress, the perpendicular component consumes part of the bird's available airspeed
        w_along = wavg @ d

        # Zermelo navigation: after accounting for the crosswind, compute the maximum ground speed achievable in direction d while maintaining airspeed v_air
        budget = v_air ** 2 - (np.sum(wavg * wavg, axis=-1) - w_along ** 2) # airspeed left after crosswind
        max_ground_speed = w_along + np.sqrt(np.maximum(budget, 0.0)) # max ground speed toward b (Zermelo)

        # an edge is usable only if the bird can overcome the crosswind and still make positive forward progress, otherwise that directed flight is impossible
        feasible = both_free & (budget > 1e-6) & (max_ground_speed > 1e-3) # crosswind-beatable & net forward progress

        # convert ground speed into travel time for this edge
        # the isotropic preference multiplier then increases or decreases the effective routing cost
        cost = (length / np.maximum(max_ground_speed, 1e-3)) * 0.5 * (pref[sa] + pref[sb])
        return idx[sa][feasible], idx[sb][feasible], cost[feasible]

    # generate all directed edges for all 26 neighbor directions and collect them into sparse graph arrays
    ea, eb, ec = [], [], []
    for offset in [(dz, dy, dx) for dz in (-1, 0, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if (dz, dy, dx) != (0, 0, 0)]:
        a, b, c = offset_edges(offset)
        ea.append(a); eb.append(b); ec.append(c)
    ea, eb, ec = np.concatenate(ea), np.concatenate(eb), np.concatenate(ec)

    n = nz * ny * nx


    # store the voxel graph as a sparse directed adjacency matrix

    # compute the minimum cost TO the roost
    # each edge currently represents the physical flight A -> B
    # but Dijkstra starts at a source and computes costs AWAY from that source
    # since we want cost-to-roost, transpose the directed graph and start Dijkstra at the roost
    graph = coo_matrix((ec, (ea, eb)), shape=(n, n)).tocsr()
    sources = []
    for rc in roost_centers:
        gi = int(np.clip((rc[0] - origin[0]) / sp, 0, nx - 1))
        gj = int(np.clip((rc[1] - origin[1]) / sp, 0, ny - 1))
        gk = int(np.clip((rc[2] - origin[2]) / sp_z, 0, nz - 1))
        sources.append(idx[gk, gj, gi])

    # T is now the global cost-to-go field i.e. every finite voxel contains the minimum accumulated routing cost from that voxel to the nearest roost
    T = dijkstra(graph.transpose().tocsr(), directed=True, indices=sources, min_only=True)
    return T.reshape(nz, ny, nx)


def get_arrival_time_field(geo_data, origin, roost_centers, config, time=0.0):
    """
    Cached accessor 
    - static geometry -> build once; if wind is in the cost, rebuild only when the wind frame changes (every scaled_dt), not every step

    Args:
        geo_data: dict, voxel geometry and grid spacing
        origin: (3,) array, world-space origin of the voxel grid (meters)
        roost_centers: list of (x, y, z) roost center positions (meters)
        config: SimConfig
        time: float, current simulation time (seconds)

    Returns:
        T: (nz, ny, nx) array, minimum accumulated routing cost from each voxel to the nearest roost
    """

    # cache the expensive global field:
    # with static routing costs, one field is sufficient
    # with time-varying wind, rebuild it only when the wind frame changes
    frame = 0 if (not config.route_use_wind or config.route_wind_static) else int(time / config.scaled_dt)
    key = (
        hash(geo_data['geometry'].tobytes()),
        tuple(tuple(c) for c in roost_centers),
        tuple(origin),
        config.v_max,
        config.floor_z,
        config.route_pollution_cost if config.route_use_pollution else None,
        config.route_noise_cost if config.route_use_noise else None,
        config.route_use_wind,
        config.scaled_wind_speed if config.route_use_wind else None,
        frame,
    )
    # the cache key includes every parameter that changes the resulting routing field
    if key not in _arrival_cache:
        wind_time = frame * config.scaled_dt
        _arrival_cache[key] = build_arrival_time_field(geo_data, origin, roost_centers, config, wind_time)
        _gradient_cache.clear() # new T, old gradients are stale
    return _arrival_cache[key]

def get_gradient(T, sp, sp_z):
    """
    Compute and cache the spatial gradient of the arrival-time field T
    - the gradient is computed once for each distinct arrival-time field and reused on subsequent simulation steps
        - this is because T only changes when the routing field is rebuilt (e.g. when the wind frame changes), not on every bird-simulation step
    - unreachable voxels contain inf in T
        - before taking the gradient, these values are replaced by a large finite value so that the gradient near unreachable regions points toward lower-cost, reachable space

    Args:
        T: (nz, ny, nx) array, arrival-time/cost field
        sp: float, horizontal grid spacing (meters)
        sp_z: float, vertical grid spacing (meters)

    Returns:
        dT_dx, dT_dy, dT_dz: tuple of 3 (nz, ny, nx) array, spatial derivatives of T
    """
    key = id(T) # T is cached in _arrival_cache, so its id remains stable while the field is active

    if key not in _gradient_cache:
        # replace unreachable voxels (inf) with a large finite value before differentiating
        # otherwise np.gradient would propagate inf/NaN
        reachable = np.isfinite(T)
        fill_value = (
            np.nanmax(np.where(reachable, T, np.nan)) * 2.0
            if reachable.any()
            else 1.0
        )
        T_filled = np.where(reachable, T, fill_value)

        # np.gradient returns derivatives in array-axis order i.e. axis 0 = z, axis 1 = y, axis 2 = x
        # convert the results to physical x/y/z names before caching them
        dT_dz, dT_dy, dT_dx = np.gradient(T_filled, sp_z, sp, sp)

        _gradient_cache[key] = (dT_dx, dT_dy, dT_dz)

    return _gradient_cache[key]


def compute_wave_guidance(positions, T, origin, sp, sp_z):
    """
    Compute the unit guidance direction toward decreasing arrival time for every bird position
    - the cached spatial gradient of T is sampled at each bird's continuous world-space position using trilinear interpolation
        - the resulting guidance vector is -grad(T), so birds move toward lower predicted travel time to the roost
        - the sampled vector is then normalized to unit length
    - positions are given in world coordinates (x, y, z), whereas the gradient field is stored as a NumPy array in (z, y, x) order, so the coordinates are reordered before sampling

    Args:
        positions: (N, 3) array, bird positions in world space (meters)
        T: (nz, ny, nx) array, arrival-time/cost field
        origin: (3,) array, world-space origin of the voxel grid (meters)
        sp: float, horizontal grid spacing (meters)
        sp_z: float, vertical grid spacing (meters)

    Returns:
        guidance: (N, 3) array, unit guidance directions toward decreasing routing cost
    """
    # arrival-time field is defined on the voxel grid, so compute its spatial gradient once and reuse it for all birds at this simulation step
    dT_dx, dT_dy, dT_dz = get_gradient(T, sp, sp_z)

    # extract each bird's world-space position
    # positions has shape (n_birds, 3) with columns ordered as (x, y, z)
    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]

    # convert world coordinates into voxel-grid coordinates for interpolation
    # map_coordinates expects coordinates in array-axis order (z, y, x), but the simulation stores positions in world order (x, y, z).
    sample_coords = np.vstack([
        (z - origin[2]) / sp_z,
        (y - origin[1]) / sp,
        (x - origin[0]) / sp,
    ])

    # trilinearly interpolate the three gradient components at each bird's continuous position
    # this avoids restricting guidance to the nearest voxel and gives a smooth direction field between grid cells
    sampled_dT_dx = map_coordinates(
        dT_dx, sample_coords, order=1, mode='nearest'
    )
    sampled_dT_dy = map_coordinates(
        dT_dy, sample_coords, order=1, mode='nearest'
    )
    sampled_dT_dz = map_coordinates(
        dT_dz, sample_coords, order=1, mode='nearest'
    )

    # the gradient points toward increasing arrival time
    # birds  follow -grad(T), which points toward decreasing time-to-roost i.e. lower routing cost
    guidance = -np.stack(
        [sampled_dT_dx, sampled_dT_dy, sampled_dT_dz],
        axis=-1,
    )

    # normalize each guidance vector so the result represents direction only
    guidance_norm = np.linalg.norm(guidance, axis=-1, keepdims=True)
    return guidance / np.maximum(guidance_norm, 1e-6) # small floor prevents division by zero in flat regions where |grad(T)| is approximately zero