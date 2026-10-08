"""
sites.py = compute and sample landing-site surface heightmaps

a "site" is any place birds descend to and land on e.g. a roost, or a forage site
- each site is a dict with 'center' [x,y,z], 'size' [len,wid], 'forward', 'normal', and 'quality'
- drapes each site's rectangle onto the voxel geometry below it
- heightmaps are computed once at init and cached for the lifetime of the simulation

TODO: make this work based on roost quality score
"""

import numpy as np

# module-level cache = maps a tuple of site centers to a list of heightmaps
# if site centers change (different config), the cache invalidates
_heightmap_cache = {}


def compute_site_heightmap(site_def, geo_data, grid_origin, resolution=50):
    """
    Produces a heightmap that follows the building/ground surface
    - sample a grid of points across the site rectangle
    - scan down through voxel geometry to find the highest solid voxel below each point
        - for a flat rooftop, all points return roughly the same z
        - for a sloped surface, they return a gradient
        - for a half-overhanging site, the building half returns roof z and the overhang half returns ground level

    Args:
        site_def: dict with 'center' [x,y,z], 'size' [length, width], 'forward' [x,y,z], 'normal' [x,y,z]
        geo_data: dict with 'geometry' (3D bool array [z,y,x]), grid_spacing', 'grid_spacing_z', or None for open field
        grid_origin: (3,) array, origin of the voxel grid in sim coords
        resolution: int, number of sample points per axis (resolution x resolution)

    Returns:
        heightmap dict with heights array and coordinate system info
    """
    center = np.array(site_def["center"])
    size = site_def.get("size", [30.0, 30.0])

    # build orthonormal basis for the site rectangle
    forward = np.array(site_def.get("forward", [1, 0, 0]), dtype=float)
    normal = np.array(site_def.get("normal", [0, 0, 1]), dtype=float)
    forward = forward / np.maximum(np.linalg.norm(forward), 1e-6)
    normal = normal / np.maximum(np.linalg.norm(normal), 1e-6)
    side = np.cross(normal, forward)
    side = side / np.maximum(np.linalg.norm(side), 1e-6)
    forward = np.cross(side, normal)  # re-orthogonalize

    half_len = size[0] / 2.0
    half_wid = size[1] / 2.0

    # sample grid in site-local coordinates
    u_vals = np.linspace(-half_len, half_len, resolution)
    v_vals = np.linspace(-half_wid, half_wid, resolution)

    # default height = ground level (no geometry below)
    heights = np.full(
        (resolution, resolution), 0.5
    )  # TODO: this 0.5 is a fallback but should not trigger

    if geo_data is not None:
        geo = geo_data["geometry"]  # (nz, ny, nx) bool array
        sp = geo_data["grid_spacing"]  # xy grid spacing in meters
        sp_z = geo_data["grid_spacing_z"]  # z grid spacing in meters
        origin = np.array(grid_origin)

        # vectorized: compute world positions for all sample points at once
        uu, vv = np.meshgrid(u_vals, v_vals, indexing="ij")  # (res, res)
        world_x = center[0] + uu * forward[0] + vv * side[0]
        world_y = center[1] + uu * forward[1] + vv * side[1]

        # convert to voxel grid indices
        gi = ((world_x - origin[0]) / sp).astype(int)
        gj = ((world_y - origin[1]) / sp).astype(int)

        # which sample points fall within the voxel grid bounds
        valid = (gi >= 0) & (gi < geo.shape[2]) & (gj >= 0) & (gj < geo.shape[1])

        # scan top-down from site z level to find highest solid voxel per column
        site_gk = min(int((center[2] - origin[2]) / sp_z), geo.shape[0] - 1)
        gi_safe = np.clip(gi, 0, geo.shape[2] - 1)
        gj_safe = np.clip(gj, 0, geo.shape[1] - 1)

        for gk in range(site_gk, -1, -1):
            # only update columns that are valid and haven't found a surface yet
            unfound = valid & (heights == 0.5)
            if not unfound.any():
                break
            is_solid = geo[gk, gj_safe, gi_safe] & unfound
            # top of this solid voxel = surface height
            heights[is_solid] = origin[2] + (gk + 1) * sp_z

    return {
        "heights": heights,
        "u_vals": u_vals,
        "v_vals": v_vals,
        "forward": forward,
        "side": side,
        "center": center,
        "normal": normal,
        "size": size,
    }


def get_site_heightmaps(config, sites, geo_data=None, grid_origin=None):
    """
    Heightmaps for an arbitrary list of sites (roosts, forage sites)
    - computed once on first call, then cached until site positions change

    Args:
        config: SimConfig
        geo_data: dict from _load_geometry, or None (open field)
        grid_origin: (3,) array, or None (uses config.scaled_grid_origin)

    Returns:
        list of heightmap dicts (one per site), or empty list if no sites
    """
    if not sites:
        return []

    # cache key = tuple of site centers, invalidates if sites move
    centers = tuple(tuple(s["center"]) for s in sites)
    if centers not in _heightmap_cache:
        origin = (
            np.array(grid_origin)
            if grid_origin is not None
            else np.array(config.scaled_grid_origin)
        )
        _heightmap_cache[centers] = [compute_site_heightmap(s, geo_data, origin) for s in sites]
    return _heightmap_cache[centers]


def sample_surface_height(heightmaps, positions):
    """
    For each bird, find the closest site and interpolate its heightmap to get the actual surface z height below that bird
    - if a bird lies outside the site footprint, sample the nearest edge value

    Args:
        heightmaps: list of heightmap dicts from get_all_site_heightmaps
        positions: (N, 3) array of bird positions

    Returns:
        surface_z: (N,) array, height of the closest site surface below each bird
        closest_site: (N,) int array, index of closest site per bird
    """
    N = positions.shape[0]

    if not heightmaps:
        return np.full(N, 0.5), np.zeros(N, dtype=int)

    # find closest site per bird by 3D distance to site centers
    site_centers = np.array([h["center"] for h in heightmaps])  # (R, 3)
    diffs = site_centers[np.newaxis, :, :] - positions[:, np.newaxis, :]  # (N, R, 3)
    dists = np.linalg.norm(diffs, axis=-1)  # (N, R)
    closest_site = np.argmin(dists, axis=1)  # (N,)

    surface_z = np.full(
        N, 0.5
    )  # default ground level TODO: this should not trigger maybe change later

    # interpolate each bird from its closest site's heightmap
    for ri in range(len(heightmaps)):
        hmap = heightmaps[ri]
        bird_mask = closest_site == ri
        if not bird_mask.any():
            continue

        bird_pos = positions[bird_mask]
        center = hmap["center"]
        forward = hmap["forward"]
        side = hmap["side"]
        u_vals = hmap["u_vals"]
        v_vals = hmap["v_vals"]
        heights = hmap["heights"]
        res = heights.shape[0]

        # project bird positions into site-local uv coordinates
        rel = bird_pos - center  # (M, 3)
        u_pos = rel @ forward  # (M,) position along site length
        v_pos = rel @ side  # (M,) position along site width

        # convert to fractional grid indices for bilinear interpolation
        u_frac = (u_pos - u_vals[0]) / (u_vals[-1] - u_vals[0]) * (res - 1)
        v_frac = (v_pos - v_vals[0]) / (v_vals[-1] - v_vals[0]) * (res - 1)

        # clamp to valid range (birds outside site footprint get edge values)
        u_frac = np.clip(u_frac, 0, res - 1.001)
        v_frac = np.clip(v_frac, 0, res - 1.001)

        # bilinear interpolation = four corners of the cell
        u0 = np.floor(u_frac).astype(int)
        v0 = np.floor(v_frac).astype(int)
        u1 = np.minimum(u0 + 1, res - 1)
        v1 = np.minimum(v0 + 1, res - 1)
        du = u_frac - u0  # fractional position within cell
        dv = v_frac - v0

        h00 = heights[u0, v0]
        h10 = heights[u1, v0]
        h01 = heights[u0, v1]
        h11 = heights[u1, v1]

        # weighted average of four corners
        surface_z[bird_mask] = (
            h00 * (1 - du) * (1 - dv) + h10 * du * (1 - dv) + h01 * (1 - du) * dv + h11 * du * dv
        )

    return surface_z, closest_site
