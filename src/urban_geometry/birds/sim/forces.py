"""
forces.py = forces for bird movement

functions return (N, 3) array of force vectors for N birds
"""

import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates
from urban_geometry.birds.sim.states import TRANSIT, MURMURATION, DESCENT
from urban_geometry.birds.sim.sites import get_site_heightmaps, sample_surface_height


def compute_separation(
    positions,
    neighbor_indices,
    neighbor_distances,
    r_hard_sphere,
    r_separation,
    separation_gaussian_floor=0.01,
    mode="single",
):
    """
    Separation = steer away from neighbors that are too close
    - uses the single closest neighbor OR multiple, depending on mode
    - acts on topological neighbors, but only activates within a distance threshold (r_repulsion)
    - inverse-distance weighted i.e. closer intruders produce stronger repulsion
    - weighted using halved Gaussian falloff with hard sphere

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        neighbor_indices: (N, k) array, indices of each bird's k closest neighbors
        neighbor_distances: (N, k) array, distances to those closest neighbors
        r_hard_sphere: float, radius of maximum avoidance (meters)
        r_separation: float, radius beyond which separation drops to zero (meters)
        separation_gaussian_floor: float, separation force at r_separation as fraction of max
        mode: string, 'single' or 'multi' neighbor repulsion

    Returns:
        force: (N, 3) array, separation force vectors
    """
    N = neighbor_indices.shape[0]

    # halved Gaussian falloff (shared by both modes)
    sigma = (r_separation - r_hard_sphere) / np.sqrt(-np.log(separation_gaussian_floor))
    sigma = max(sigma, 1e-6)

    def _weight(dist):
        # full strength inside hard sphere, Gaussian decay outside, zero past r_separation
        w = np.where(
            dist <= r_hard_sphere, 1.0, np.exp(-((dist - r_hard_sphere) ** 2) / (sigma**2))
        )
        return np.where(dist <= r_separation, w, 0.0)

    if mode == "single":
        # H2015 "Diffusion and Topological Neighbours in Flocks of Starlings" = react only to the single closest neighbor
        closest_idx = neighbor_indices[:, 0]
        closest_dist = neighbor_distances[:, 0]
        away = positions - positions[closest_idx]
        away_unit = away / np.maximum(np.linalg.norm(away, axis=-1, keepdims=True), 1e-6)
        force = away_unit * _weight(closest_dist)[:, np.newaxis]
        return force

    else:
        # H2010 = sum weighted repulsion over ALL topological neighbors within range
        # uses the SAME halved-Gaussian weight as single-neighbor mode, so the only difference under test is neighbor COUNT
        N, k = neighbor_indices.shape
        neighbor_pos = positions[neighbor_indices]  # (N, k, 3)
        away = positions[:, np.newaxis, :] - neighbor_pos  # (N, k, 3)
        away_unit = away / np.maximum(
            np.linalg.norm(away, axis=-1, keepdims=True), 1e-6
        )  # (N, k, 3)

        # same _weight as single mode, applied per neighbor
        w = np.where(
            neighbor_distances <= r_hard_sphere,
            1.0,
            np.exp(-((neighbor_distances - r_hard_sphere) ** 2) / (sigma**2)),
        )
        w = np.where(neighbor_distances <= r_separation, w, 0.0)  # (N, k)

        force = np.sum(away_unit * w[:, :, np.newaxis], axis=1)  # (N, 3)
        return force


def compute_alignment(velocities, neighbor_indices, mask):
    """
    Alignment = steer bird's heading toward the average heading of neighbors
    - topological = computed over k closest neighbors
    - excludes neighbors in the rear blind angle
    - uses heading (unit velocity vector) to match direction but not speed

    Args:
        velocities: (N, 3) array, bird velocities (used to extract headings)
        neighbor_indices: (N, k) array, indices of each bird's k closest neighbors
        mask: (N, k) array, boolean True = neighbor is visible. None = all visible

    Returns:
        force: (N, 3) array, alignment force vectors pointing from current heading toward average neighbor heading
    """
    # compute unit headings for all birds
    speeds = np.linalg.norm(velocities, axis=-1, keepdims=True)  # (N, 1)
    headings = velocities / np.maximum(speeds, 1e-6)  # (N, 3)

    # gather neighbor headings
    neighbor_headings = headings[neighbor_indices]  # (N, k, 3)

    # average neighbor heading (= desired collective direction)
    if mask is not None:
        # zero out invisible neighbors, then average only over visible ones
        mask_3d = mask[:, :, np.newaxis].astype(float)  # (N, k, 1)
        masked_headings = neighbor_headings * mask_3d
        visible_count = np.maximum(mask.sum(axis=1, keepdims=True), 1)  # (N, 1)
        avg_heading = masked_headings.sum(axis=1) / visible_count  # (N, 3)
    else:
        avg_heading = np.mean(neighbor_headings, axis=1)

    # normalize the average to get unit vector
    avg_norm = np.linalg.norm(avg_heading, axis=-1, keepdims=True)
    avg_heading_unit = avg_heading / np.maximum(avg_norm, 1e-6)  # (N, 3)

    # alignment force = desired heading - current heading
    force = avg_heading_unit - headings  # (N, 3)

    return force


def compute_cohesion(
    positions, neighbor_indices, neighbor_distances, mask, centrality, r_hard_sphere
):
    """
    Cohesion = sum of unit vectors toward each neighbor
    - topological = computed over k closest neighbors
    - excludes neighbors in the rear blind angle
    - excludes neighbors within hard sphere
    - scaled by centrality so peripheral birds cohere more strongly

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        neighbor_indices: (N, k) array, indices of each bird's k closest neighbors
        neighbor_distances: (N, k) array, distances needed for hard-sphere exclusion
        mask: (N, k) array, boolean True = neighbor is visible. None = all visible
        centrality: (N,) array, centrality scores 0–1
        r_hard_sphere: float, hard sphere radius (meters)

    Returns:
        force: (N, 3) array, cohesion force, scaled by centrality
    """
    # gather neighbor positions
    neighbor_pos = positions[neighbor_indices]  # (N, k, 3)

    # build combined mask for both visibility AND whether outside hard sphere
    N, k = neighbor_indices.shape
    combined_mask = np.ones((N, k), dtype=bool)

    if mask is not None:
        combined_mask &= mask

    if neighbor_distances is not None:
        combined_mask &= neighbor_distances > r_hard_sphere

    # build (N,k,1) float mask and per-bird valid-neighbor count for the eqn5 sum below
    mask_3d = combined_mask[:, :, np.newaxis].astype(float)  # (N, k, 1)
    valid_count = np.maximum(combined_mask.sum(axis=1, keepdims=True), 1)  # (N, 1)

    # eqn 5 H2010: sum unit vectors toward each valid neighbor, divide by neighbor count
    # summing unit vectors means interior birds self-cancel to ~0, only border birds get pulled
    to_neighbor = (
        neighbor_pos - positions[:, np.newaxis, :]
    )  # (N,k,3), vector from bird to each neighbor
    to_neighbor_unit = (
        to_neighbor
        / np.maximum(  # (N,k,3), normalize each vector to unit length (direction only, equal weight per neighbor)
            np.linalg.norm(to_neighbor, axis=-1, keepdims=True), 1e-6
        )
    )  # max(...,1e-6) guards against divide-by-zero
    summed = (to_neighbor_unit * mask_3d).sum(
        axis=1
    )  # (N,3) zero out invisible/hard-sphere neighbors, then sum the unit vectors
    force = summed / valid_count  # (N,3) divide by neighbor count (eqn5 denominator |N*_i|)

    # scale by centrality, peripheral birds cohere more strongly
    if centrality is not None:
        force = force * centrality[:, np.newaxis]

    return force


def compute_centrality(positions, neighbor_indices):
    """
    Centrality = how close to the center of the flock a bird is
    - NOTE: uses k topological neighbors, not 2*R_i metric neighborhood (eqn7 H2010)

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        neighbor_indices: (N, k) array, indices of each bird's k closest neighbors

    Returns:
        centrality: (N,) array, values in [0, 1] where 0 = fully interior, 1 = fully peripheral
    """
    neighbor_pos = positions[neighbor_indices]  # (N, k, 3)

    # unit vectors from each bird toward each neighbor
    toward = neighbor_pos - positions[:, np.newaxis, :]  # (N, k, 3)
    toward_dist = np.linalg.norm(toward, axis=-1, keepdims=True)
    toward_unit = toward / np.maximum(toward_dist, 1e-6)  # (N, k, 3)

    # centrality = magnitude of average direction vector
    avg_direction = np.mean(toward_unit, axis=1)  # (N, 3)
    centrality = np.linalg.norm(avg_direction, axis=-1)  # (N,)

    return centrality


def compute_roost_attraction(positions, velocities, roosts, config, bstate=None, env=None):
    """
    Roost attraction = steer toward the roost (or possibly forage) site
    - horizontal: tanh pull toward closest roost, scaled by roost quality
    - vertical: altitude spring holds birds at preferred height (eqn12 H10)
      - MURMURATION/TRANSIT birds target flight altitude (roost center + roost_flight_offset)
      - DESCENT birds target roost surface altitude (roost center)
      - spring weakens as darkness increases so cohesion can pull the flock down during dusk cascade
    - ROOST birds are handled separately in integrator (snapped to assigned spots)

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        velocities: (N, 3) array, bird velocities (for dampening)
        roosts: list of dicts, each with 'center' [x,y,z] and 'quality' float
        config: SimConfig
        bstate: (N,) int array, behavioral states. None = all birds treated as MURMURATION
        env: dict with 'light' (N,) array. None = full vertical spring strength

    Returns:
        force: (N, 3) array, roost attraction force vectors. Magnitude scales with distance (farther = stronger pull)

    TODO: quality currently just scales force linearly... consider threshold-based selection with empirical backing
    TODO: RENAME THIS TO INCORPORATE THE FACT WE ALSO USE IT ON FORAGE SITES!
    """
    N = positions.shape[0]

    if not roosts:
        return np.zeros((N, 3))

    # compute distance to each roost, pick closest per bird
    roost_positions = np.array([r["center"] for r in roosts])  # (R, 3)
    qualities = np.array([r.get("quality", 1.0) for r in roosts])  # (R,)

    # vectors from each bird to each roost
    diffs = roost_positions[np.newaxis, :, :] - positions[:, np.newaxis, :]  # (N, R, 3)
    dists = np.linalg.norm(diffs, axis=-1)  # (N, R)

    # closest roost per bird
    closest = np.argmin(dists, axis=1)  # (N,)

    # gather vector toward each bird's closest roost
    toward_roost = diffs[np.arange(N), closest]  # (N, 3)
    dist = dists[np.arange(N), closest]  # (N,)
    quality = qualities[closest]  # (N,)

    # adjust TRANSIT target so that it's roost center + preferred altitude offset, not just the center
    # o/w we would have birds aiming for the roost center during TRANSIT and then jumping up to the preferred murmuration altitude once they enter MURMURATION
    if bstate is not None:
        transit_mask = bstate == TRANSIT
        if transit_mask.any():
            flight_z = roost_positions[closest, 2] + config.roost_flight_offset  # (N,)
            toward_roost[transit_mask, 2] = flight_z[transit_mask] - positions[transit_mask, 2]

    # distance-dependent magnitude with tanh saturation, scaled by quality
    scale = np.tanh(dist / config.roost_tanh_halfdist) * quality
    direction = toward_roost / np.maximum(dist[:, np.newaxis], 1e-6)  # (N, 3)
    force = direction * scale[:, np.newaxis]  # (N, 3)
    # vertical steering: MURMURATION/DESCENT delegate altitude to the spring below aka horizontal steering only = vertical controlled by altitude spring below matches H2010 separation of wRoostH (horizontal) vs wRoostV (vertical)
    # but TRANSIT has NO spring, so it keeps the full 3D pull = a soft, distance-saturating attraction toward the roost's location (height included)
    # ideally should draw birds to site without pinning them to an altitude band
    if bstate is not None:
        non_transit = bstate != TRANSIT
        force[non_transit, 2] = 0.0
    else:
        force[:, 2] = 0.0  # no state info = original horizontal-only behavior

    # DESCENT birds below roost surface have redirected pull to aim above the roost
    # keeps horizontal orbit intact (prevents flyoff) while adding upward component
    # TODO: this may be janky, but I can't think of a physical situation where birds would want to approach roost directly from the bottom
    if bstate is not None:
        descent_below = bstate == DESCENT
        if descent_below.any():
            roost_hmaps = get_site_heightmaps(config, roosts)
            if roost_hmaps:
                surf_z, closest_ri = sample_surface_height(roost_hmaps, positions)
                below = descent_below & (positions[:, 2] < surf_z - 0.5)
                if below.any():
                    # target point = roost center but 10m above surface TODO: remove hardcoded value
                    # bird orbits toward this elevated point, naturally clearing the roof TODO: doesn't always work anyway, but maybe this is a problem with bird pathing in general
                    for ri in range(len(roost_hmaps)):
                        ri_mask = below & (closest_ri == ri)
                        if ri_mask.any():
                            elevated_target = roost_hmaps[ri]["center"].copy()
                            elevated_target[2] = surf_z[ri_mask].mean() + 10.0
                            toward_elevated = elevated_target - positions[ri_mask]
                            dist_elev = np.linalg.norm(toward_elevated, axis=-1, keepdims=True)
                            force[ri_mask] = (
                                toward_elevated
                                / np.maximum(dist_elev, 1e-6)
                                * scale[ri_mask, np.newaxis]
                            )

    # MURMURATION birds hover at flight offset above site
    # preferred flight altitude = roost center z + offset (birds circle above roost)
    site_center_z = roost_positions[closest, 2]
    preferred_altitude = site_center_z + config.roost_flight_offset

    # DESCENT birds target the actual surface below them from the heightmap
    if bstate is not None:
        descent_mask = bstate == DESCENT
        if descent_mask.any():
            roost_hmaps = get_site_heightmaps(config, roosts)
            if roost_hmaps:
                surface_z, _ = sample_surface_height(roost_hmaps, positions)
                preferred_altitude[descent_mask] = surface_z[descent_mask]
            else:
                # fallback = use closest roost center z per bird
                roost_centers = np.array([r["center"] for r in roosts])
                diffs = roost_centers[np.newaxis, :, :] - positions[descent_mask, np.newaxis, :]
                closest = np.argmin(np.linalg.norm(diffs, axis=-1), axis=1)
                preferred_altitude[descent_mask] = roost_centers[closest, 2]

    # soft altitude band applies to flying birds (murmuration/transit), gives them vertical freedom so the flock doesn't collapse to a plane
    # BUT descent birds keep the hard spring so they actually land on the surface
    raw_error = preferred_altitude - positions[:, 2]
    altitude_error = raw_error.copy()
    if bstate is not None:
        band = config.roost_altitude_band
        flying = (bstate == MURMURATION) | (bstate == TRANSIT)
        altitude_error[flying] = np.sign(raw_error[flying]) * np.maximum(
            np.abs(raw_error[flying]) - band, 0.0
        )
    else:  # fallback in case no state info
        # if no state info, then band applies to all
        band = config.roost_altitude_band
        altitude_error = np.sign(raw_error) * np.maximum(np.abs(raw_error) - band, 0.0)

    # vertical altitude spring (eqn12 H10) with velocity damping
    # birds perceive altitude and correct toward preferred flight height, spring pushes toward preferred altitude, damping prevents oscillation
    vertical_velocity = velocities[:, 2]  # positive = rising

    # vertical spring strength = weakens as darkness increases so cohesion can pull flock down
    vertical_strength = np.full(N, config.w_roost_vertical)

    if env is not None and bstate is not None:
        local_light = env["light"]
        threshold = config.roost_light_threshold
        # 0 = bright (full spring), 1 = fully dark (weak spring)
        darkness = np.clip((threshold - local_light) / threshold, 0.0, 1.0)
        # for murmuration birds, spring weakens from 100% to 20% as darkness increases
        murm_mask = bstate == MURMURATION
        vertical_strength[murm_mask] *= 1.0 - 0.8 * darkness[murm_mask]

    if bstate is not None:
        # for descent birds, very weak spring just enough to guide toward surface
        vertical_strength[bstate == DESCENT] = (
            config.w_roost_vertical * config.descent_vertical_multiplier
        )

    # the altitude band is a MURMURATION mechanism, so TRANSIT birds get NO altitude spring
    # in transit a bird flies at whatever altitude its flocking + wind/field responses put it, free to climb or dip
    # DESCENT keeps its guided spring to land.
    if bstate is not None:
        vertical_strength[bstate == TRANSIT] = 0.0
    force[:, 2] += (
        vertical_strength * altitude_error - config.roost_vertical_damping * vertical_velocity
    )

    return force


def compute_obstacle_avoidance(
    positions, velocities, geometry, grid_spacing, grid_spacing_z, grid_origin, detection_dist
):
    """
    Obstacle avoidance = steer away from occupied grid cells.
    - uses a precomputed Euclidean distance field for smooth, fast avoidance
    - distance field computed once at startup and cached
    - birds follow the gradient of the distance field (toward open space)

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        velocities: (N, 3) array, bird velocities (used to extract headings)
        geometry: (depth, height, width) bool array, True = building
        grid_spacing: float, horizontal meters per grid cell (x, y)
        grid_spacing_z: float, vertical meters per grid cell (z)
        grid_origin: (3,) array, (x, y, z) of grid cell (0,0,0) in sim coords
        detection_dist: float, how far birds sense buildings (meters)

    Returns:
        force: (N, 3) array, avoidance force vectors
    """

    N = positions.shape[0]
    origin = np.array(grid_origin)
    gz, gy, gx = (
        geometry.shape
    )  # geometry is stored as (z, y, x) = (depth, height, width) following SCALED convention

    # precompute distance field once and cache it
    # the distance field gives, for every empty cell, its Euclidean distance to the nearest building
    # the gradient of this field points away from buildings = the direction birds should steer
    if not hasattr(compute_obstacle_avoidance, "_cache"):
        compute_obstacle_avoidance._cache = {}

    cache_key = id(geometry)
    if cache_key not in compute_obstacle_avoidance._cache:
        # distance_transform_edt expects False = obstacle, True = free space
        # so we invert the geometry (where True = building)
        # sampling parameter gives physical size of each voxel in (z, y, x) order
        dist_field = distance_transform_edt(
            ~geometry, sampling=(grid_spacing_z, grid_spacing, grid_spacing)
        ).astype(np.float32)

        # gradient of the distance field = points from buildings toward open space
        # np.gradient returns arrays in the same axis order as the input: (z, y, x)
        grad_z, grad_y, grad_x = np.gradient(dist_field, grid_spacing_z, grid_spacing, grid_spacing)

        # distance field inside buildings (for push-out when birds penetrate)
        # this gives each building cell its distance to the nearest free cell
        interior_dist = distance_transform_edt(
            geometry,  # True = building = source
            sampling=(grid_spacing_z, grid_spacing, grid_spacing),
        ).astype(np.float32)
        ig_z, ig_y, ig_x = np.gradient(interior_dist, grid_spacing_z, grid_spacing, grid_spacing)

        compute_obstacle_avoidance._cache[cache_key] = {
            "dist": dist_field,  # (gz, gy, gx) distance to nearest building in meters
            "grad_x": grad_x.astype(np.float32),  # (gz, gy, gx) x-component of gradient
            "grad_y": grad_y.astype(np.float32),  # (gz, gy, gx) y-component of gradient
            "grad_z": grad_z.astype(np.float32),  # (gz, gy, gx) z-component of gradient
            "interior_grad_x": ig_x.astype(np.float32),
            "interior_grad_y": ig_y.astype(np.float32),
            "interior_grad_z": ig_z.astype(np.float32),
        }

    cached = compute_obstacle_avoidance._cache[cache_key]

    # convert bird positions from sim coordinates to grid coordinates
    grid_pos = np.zeros_like(positions)
    grid_pos[:, 0] = (positions[:, 0] - origin[0]) / grid_spacing  # x in grid units
    grid_pos[:, 1] = (positions[:, 1] - origin[1]) / grid_spacing  # y in grid units
    grid_pos[:, 2] = (positions[:, 2] - origin[2]) / grid_spacing_z  # z in grid units

    # reorder to (z, y, x) to match the distance field array layout
    coords_zyx = grid_pos[:, [2, 1, 0]].T  # (3, N)

    # look up how far each bird is from nearest building by sampling distance field at bird's pos
    # 3D grid stores how many meters to closest building wall, interpolate between cells for smooth value
    dist_at_bird = map_coordinates(cached["dist"], coords_zyx, order=1, mode="nearest")  # (N,)

    # sample gradient components at each bird's position
    # these give the direction pointing away from the nearest building surface
    gx_at_bird = map_coordinates(cached["grad_x"], coords_zyx, order=1, mode="nearest")  # (N,)
    gy_at_bird = map_coordinates(cached["grad_y"], coords_zyx, order=1, mode="nearest")  # (N,)
    gz_at_bird = map_coordinates(cached["grad_z"], coords_zyx, order=1, mode="nearest")  # (N,)

    # assemble gradient into sim coordinate order (x, y, z)
    grad = np.stack([gx_at_bird, gy_at_bird, gz_at_bird], axis=-1)  # (N, 3)

    # normalize to unit vector
    grad_mag = np.linalg.norm(grad, axis=-1, keepdims=True)
    grad_unit = grad / np.maximum(grad_mag, 1e-6)  # (N, 3)

    # force strength = quadratic falloff from full strength at building surface to zero at detection_dist
    # birds farther than detection_dist from any building feel no force
    strength = np.maximum(1.0 - dist_at_bird / detection_dist, 0.0) ** 2  # (N,)

    # check if heading toward building
    speeds = np.linalg.norm(velocities, axis=-1, keepdims=True)
    headings = velocities / np.maximum(speeds, 1e-6)  # (N, 3)
    approaching = np.sum(
        headings * grad_unit, axis=-1
    )  # (N,) positive = heading away, negative = heading toward
    approaching_factor = np.clip(
        -approaching, 0.0, 1.0
    )  # (N,), 1.0 = heading straight at building, 0.0 = heading away

    force = grad_unit * (strength * approaching_factor)[:, np.newaxis]  # (N, 3)

    return force


def compute_wind_response(wind, intended_dir, v_max, mass, tau_wind, state_gain):
    """
    Wind response (anemotaxis) = a bird's body-local reaction to the wind it feels
    - bird senses only the wind flowing over its own body, so use just local wind vector at each bird (and bird's intended travel direction)
    - uses local wind vector at each bird plus bird's own on
    - COMPENSATION = counteract crosswind drift + push into a headwind (never oppose a tailwind)
        - decomposes the wind relative to the bird's intended direction:
            - crosswind (drift) -> turn slightly into it, so the bird leans/banks upwind (flight term = crab) to hold its ground track
            - headwind -> forward push for higher airspeed, but fades to 0 as the headwind saturates
            - tailwind -> left alone, so the bird rides it for free groundspeed

    Args:
        wind: (N, 3) local wind velocity at each bird (m/s)
        intended_dir: (N, 3) unit vectors, direction each bird wants to travel
        v_max: scalar, the bird's own max airspeed (m/s)
        mass: scalar, bird mass (kg)
        tau_wind: scalar, compensation timescale (s)
        state_gain: (N, 1) per-state gain (e.g. full in TRANSIT, low in MURMURATION, 0 in ROOST)

    Returns:
        force: (N, 3) array, combined wind-response steering force
    """

    # COMPENSATION = crab the crosswind + push into a headwind only (never oppose a tailwind)
    w_par = np.sum(
        wind * intended_dir, axis=-1, keepdims=True
    )  # (N, 1) signed: >0 tailwind, <0 headwind
    wind_perp = wind - w_par * intended_dir  # (N, 3) cross-track drift component

    headwind = np.maximum(-w_par[:, 0], 0.0)  # (N,) magnitude of the headwind component only
    saturation = np.clip(
        headwind / v_max, 0.0, 1.0
    )  # saturation approaches 1 as the headwind nears the bird's ceiling

    # crab opposes only the drift, headwind push fades to 0 as the headwind saturates
    f_crab = -(mass / tau_wind) * wind_perp  # (N, 3)
    f_head = (
        (mass / tau_wind) * (headwind * (1.0 - saturation))[:, np.newaxis] * intended_dir
    )  # (N, 3)
    f_comp = f_crab + f_head  # (N, 3)

    return state_gain * f_comp


def compute_field_speed_modulation(
    field_values, field_responses, v_target, state_gain, v_min, v_max
):
    """
    Berdahl orthokinesis (i.e. speed-modulation) controls response to environmental fields
    - each bird modulates its speed by the local scalar field value it senses
    - faster where an aversive field is high (leave bad regions), slower where an appetitive field is high (linger)
    - no explicit individual gradient sensing, but the flock's directional response can emerge from this speed modulation plus the existing cohesion coupling

    Args:
        field_values: dict {name: (N,) scalar values, normalized to 0-1}
        field_responses: dict {name: {'sign': +1 aversive / -1 appetitive, 'gain': float}}
        v_target: (N, 1) array, base target speed per bird
        state_gain: (N, 1) array, per-state gain (e.g. full during TRANSIT, low during MURMURATION, 0 during ROOST)
        v_min: float, minimum sustained airspeed (m/s), floor for kinesis target-setting
        v_max: float, maximum airspeed (m/s)

    Returns:
        (N, 1) array, modulated target speed
    """
    modulation = np.zeros((v_target.shape[0], 1))  # fractional speed change per bird
    for name, resp in field_responses.items():
        if name not in field_values:
            continue
        c = np.clip(field_values[name], 0.0, 1.0).reshape(-1, 1)  # (N,1) normalized field
        modulation += (
            resp["sign"] * resp["gain"] * (2.0 * c - 1.0)
        )  # Berdahl: s = s_min + L*(s_max - s_min), i.e. slow in good regions (c ~= 0) and fast in bad (c ~= 1)

    factor = 1.0 + state_gain * modulation
    min_factor = v_min / np.maximum(v_target, 1e-6)  # per-bird floor: never below v_min airspeed
    max_factor = v_max / np.maximum(v_target, 1e-6)  # same, but for max
    factor = np.clip(factor, min_factor, max_factor)
    factor = np.clip(factor, min_factor, 2.0)  # keep speed sane TODO: tweak based off empirical
    return v_target * factor
