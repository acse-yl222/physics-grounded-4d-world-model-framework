"""
world_gen.py - programmatic placement of world features from voxel geometry

When merging with projects that don't specify world features manually,
this module analyzes voxel geometry to place roosts and forage sites.

Roosts are placed on flat elevated surfaces (building rooftops).
Forage sites are placed on large open ground areas (no buildings).

If not enough candidates are found at the initial minimum area,
the area threshold is progressively halved until enough are found
or a hard floor is reached.

Modes:
  "off"        - use config.world as provided, no auto-generation
  "naive"      - auto-generate all world features from geometry, replacing manual entries
  "supplement" - keep manual entries, auto-generate only enough to fill the remaining quota

Future placeholders:
  - pollution sources on building tops (HVAC/chimney analogy)
  - roads from street-level canyon detection
  - "data" mode using real-world sources (OSM, land-use maps)

No citation: this is heuristic placement, not a behavioral model.
The geometry analysis is straightforward connected-component labeling
on a voxel heightmap. Site quality scores are assigned by relative area rank.
"""

import numpy as np
from scipy.ndimage import label, distance_transform_edt


# ── public entry point ────────────────────────────────────────────────


def generate_world(config, geo_data):
    """
    Auto-generate world features (roosts, forage sites) based on voxel geometry.
    Modifies config.world in place.

    Args:
        config: SimConfig with world_generation mode and gen parameters
        geo_data: dict from _load_geometry with 'geometry', 'grid_spacing', 'grid_spacing_z',
                  or None if no wind/geometry file is available
    """
    mode = config.world_generation
    if mode == "off":
        return

    # ensure the world dict exists with all expected keys
    if config.world is None:
        config.world = {}
    for key in ("roosts", "forage_sites", "roads", "point_sources"):
        config.world.setdefault(key, [])

    # determine how many sites we still need to generate
    if mode == "naive":
        # ignore any manual entries, auto-generate everything
        manual_roosts = []
        manual_forage = []
        needed_roosts = config.world_gen_n_roosts
        needed_forage = config.world_gen_n_forage
    elif mode == "supplement":
        # keep manual entries, generate only the shortfall
        manual_roosts = list(config.world.get("roosts", []))
        manual_forage = list(config.world.get("forage_sites", []))
        needed_roosts = max(0, config.world_gen_n_roosts - len(manual_roosts))
        needed_forage = max(0, config.world_gen_n_forage - len(manual_forage))
    else:
        raise ValueError(
            f"Unknown world_generation mode: '{mode}'. Options: 'off', 'naive', 'supplement'"
        )

    if needed_roosts == 0 and needed_forage == 0:
        print("[world_gen] manual entries already meet quota, nothing to generate")
        return

    # dispatch to geometry-based or open-field fallback
    if geo_data is not None:
        generated_roosts, generated_forage = _generate_from_geometry(
            config, geo_data, needed_roosts, needed_forage
        )
    else:
        generated_roosts, generated_forage = _generate_open_field_fallback(
            config, needed_roosts, needed_forage
        )

    # assemble final world dict
    if mode == "naive":
        config.world["roosts"] = generated_roosts
        config.world["forage_sites"] = generated_forage
        # clear manual pollution/roads too in naive mode (placeholder for future auto-gen)
        config.world["roads"] = []
        config.world["point_sources"] = []
    elif mode == "supplement":
        config.world["roosts"] = manual_roosts + generated_roosts
        config.world["forage_sites"] = manual_forage + generated_forage

    print(
        f"[world_gen] mode='{mode}': "
        f"{len(config.world['roosts'])} roosts, "
        f"{len(config.world['forage_sites'])} forage sites"
    )
    for i, roost in enumerate(config.world["roosts"]):
        tag = "(manual)" if mode == "supplement" and i < len(manual_roosts) else "(auto)"
        print(f"  roost {i} {tag}: center={roost['center']}, size={roost['size']}")
    for i, site in enumerate(config.world["forage_sites"]):
        tag = "(manual)" if mode == "supplement" and i < len(manual_forage) else "(auto)"
        print(f"  forage {i} {tag}: center={site['center']}, size={site['size']}")


# ── geometry analysis ─────────────────────────────────────────────────


def _build_column_height_map(geo_data, grid_origin):
    """
    Build a 2D map of the highest solid surface height at each (y, x) column.

    Args:
        geo_data: dict with 'geometry' (nz, ny, nx) bool, 'grid_spacing', 'grid_spacing_z'
        grid_origin: (3,) array, world position of voxel grid cell (0, 0, 0)

    Returns:
        column_height: (ny, nx) array of surface heights in sim coordinates (meters)
        ground_mask: (ny, nx) bool, True where the column has no elevated structure
    """
    geometry = geo_data["geometry"]  # (nz, ny, nx) bool
    spacing_z = geo_data["grid_spacing_z"]
    nz, ny, nx = geometry.shape

    # for each column, find the highest z index containing a solid voxel
    # broadcast z indices across the volume and mask by solidity
    z_indices = np.arange(nz).reshape(nz, 1, 1)  # (nz, 1, 1)
    solid_z = np.where(geometry, z_indices, -1)
    max_z_index = solid_z.max(axis=0)  # (ny, nx), -1 where no solid exists

    # a column is only usable if scanning down actually hits solid geometry;
    # an empty column is void -- a site there would float over nothing
    has_geometry = max_z_index >= 0

    # convert voxel index to height in sim coordinates (top of the highest solid voxel)
    column_height = np.where(
        has_geometry,
        grid_origin[2] + (max_z_index + 1) * spacing_z,
        grid_origin[2],  # placeholder only; these columns are excluded via has_geometry below
    )

    # "ground" = a column that HAS geometry and whose surface sits near the ACTUAL floor.
    # The floor is not necessarily at grid_origin[2], so measure against the lowest real
    # surface, not the grid origin. 3 m above the floor still counts (kerbs/bumps, not buildings).
    if has_geometry.any():
        floor_z = float(column_height[has_geometry].min())
    else:
        floor_z = float(grid_origin[2])
    ground_tolerance = 3.0
    ground_mask = has_geometry & (column_height <= floor_z + ground_tolerance)

    return column_height, ground_mask


def _footprint_has_obstruction(center, size, column_height, geo_data, grid_origin, clearance=5.0):
    """
    Check whether a rectangular footprint has any solid geometry above the site's z level.

    Scans every column within the rectangle [center ± size/2] and returns True if
    any column's height exceeds (site_z + clearance).

    Args:
        center: [x, y, z] in sim coordinates
        size: [width_x, width_y] in meters
        column_height: (ny, nx) height map in sim coordinates
        geo_data: dict with grid spacing info
        grid_origin: (3,) array
        clearance: meters above site z to tolerate (catches overhangs, parapets)

    Returns:
        True if there is solid geometry within the footprint, False if clear
    """
    spacing_xy = geo_data["grid_spacing"]
    ny, nx = column_height.shape
    half_x = size[0] / 2.0
    half_y = size[1] / 2.0
    site_z = center[2]

    # convert footprint bounds to grid indices
    col_min = max(0, int((center[0] - half_x - grid_origin[0]) / spacing_xy))
    col_max = min(nx - 1, int((center[0] + half_x - grid_origin[0]) / spacing_xy))
    row_min = max(0, int((center[1] - half_y - grid_origin[1]) / spacing_xy))
    row_max = min(ny - 1, int((center[1] + half_y - grid_origin[1]) / spacing_xy))

    if col_min > col_max or row_min > row_max:
        return True  # footprint is outside the domain, treat as obstructed

    footprint_heights = column_height[row_min : row_max + 1, col_min : col_max + 1]
    return bool(np.any(footprint_heights > site_z + clearance))


def _fit_flat_squares(level_mask, column_height, geo_data, grid_origin, cw):
    """
    Every cw x cw (cells) square footprint lying entirely inside level_mask.

    level_mask is True for columns whose surface is at the level we want and which have
    nothing above them, so a window fully inside the mask is both flat (all columns share
    the level) and unobstructed (no voxel above any part) -- exactly "no occupied voxel
    directly above any part of the site". A summed-area table tests all placements at once;
    a second one gives each window's mean surface height; a distance transform ranks
    placements by how deep in the open area they sit (bigger clearings score higher).

    Returns candidate dicts ranked best-first (not yet separated).
    """
    spacing_xy = geo_data["grid_spacing"]
    ny, nx = level_mask.shape
    if cw > nx or cw > ny or not level_mask.any():
        return []

    blocked = (~level_mask).astype(np.int64)
    sat = np.pad(blocked, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    win_blocked = sat[cw:, cw:] - sat[:-cw, cw:] - sat[cw:, :-cw] + sat[:-cw, :-cw]

    hsat = np.pad(column_height.astype(np.float64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    win_hsum = hsat[cw:, cw:] - hsat[:-cw, cw:] - hsat[cw:, :-cw] + hsat[:-cw, :-cw]
    win_hmean = win_hsum / float(cw * cw)

    openness = distance_transform_edt(level_mask)

    candidates = []
    for r0, c0 in np.argwhere(win_blocked == 0):
        cy = r0 + cw / 2.0
        cx = c0 + cw / 2.0
        candidates.append(
            {
                "center": [
                    float(grid_origin[0] + cx * spacing_xy),
                    float(grid_origin[1] + cy * spacing_xy),
                    float(win_hmean[r0, c0]),
                ],
                "size": [float(cw * spacing_xy), float(cw * spacing_xy)],
                "forward": [1.0, 0.0, 0.0],
                "normal": [0.0, 0.0, 1.0],
                "quality": 1.0,
                "_area": float(openness[int(cy), int(cx)]),  # rank key, stripped downstream
            }
        )
    candidates.sort(key=lambda c: c["_area"], reverse=True)
    return candidates


def _greedy_separate(candidates, min_separation):
    """Keep candidates (already ranked best-first) that are >= min_separation apart in xy."""
    kept = []
    for c in candidates:
        cx, cy = c["center"][0], c["center"][1]
        if all(
            (cx - k["center"][0]) ** 2 + (cy - k["center"][1]) ** 2 >= min_separation**2
            for k in kept
        ):
            kept.append(c)
    return kept


def _find_roost_candidates(
    column_height, ground_mask, geo_data, grid_origin, min_area, min_separation=40.0
):
    """
    Flat, unobstructed rectangles for roosting, on ANY surface level.

    Same predicate as forage (a square with nothing above it), but a roost may sit on a
    rooftop as well as the ground, so the search runs once per surface height level.
    Rooftops are preferred (birds roost high); ground is a fallback used only when no
    rooftop qualifies. Roost footprints stay compact (<= 30 m).

    Args mirror _find_forage_candidates; min_area side is capped at 30 m.
    """
    spacing_xy = geo_data["grid_spacing"]
    spacing_z = geo_data["grid_spacing_z"]
    side_m = min(float(np.sqrt(min_area)), 30.0)
    cw = max(1, int(round(side_m / spacing_xy)))

    # quantize surface heights to voxel levels so each rooftop reads as one flat level
    quantized = np.round(column_height / spacing_z) * spacing_z
    # a roost also needs real geometry beneath it. Void columns fall back to exactly
    # grid_origin[2]; any solid voxel puts the surface at least one z-cell above that,
    # so this cleanly separates real surfaces from empty air.
    has_geometry = column_height > grid_origin[2] + 0.5 * spacing_z
    elevated = has_geometry & ~ground_mask

    elevated_candidates = []
    levels = np.unique(quantized[elevated]) if elevated.any() else np.array([])
    for level in levels:
        level_mask = (quantized == level) & elevated
        elevated_candidates += _fit_flat_squares(
            level_mask, column_height, geo_data, grid_origin, cw
        )
    elevated_candidates.sort(key=lambda c: c["_area"], reverse=True)

    ground_candidates = _fit_flat_squares(ground_mask, column_height, geo_data, grid_origin, cw)
    ground_candidates.sort(key=lambda c: c["_area"], reverse=True)

    # rooftops first, ground as fallback; greedy separation keeps the earlier (higher) ones
    return _greedy_separate(elevated_candidates + ground_candidates, min_separation)


def _find_forage_candidates(
    column_height, ground_mask, geo_data, grid_origin, min_area, min_separation=40.0
):
    """
    Open-ground rectangles for foraging: flat, unobstructed squares on the ground level.

    Searches all placements of a square sized from min_area, keeps only fully-unobstructed
    ones, and separates them here so the downstream top-N cut can't collapse a cluster of
    adjacent windows into a single site.

    Args:
        column_height: (ny, nx) surface height map (sim coords)
        ground_mask: (ny, nx) bool, True = ground (nothing above the column)
        geo_data, grid_origin: grid info
        min_area: target site area in m^2 (side = sqrt(min_area), capped at 60 m)
        min_separation: minimum spacing between returned sites (m)
    """
    spacing_xy = geo_data["grid_spacing"]
    side_m = min(float(np.sqrt(min_area)), 60.0)
    cw = max(1, int(round(side_m / spacing_xy)))
    candidates = _fit_flat_squares(ground_mask, column_height, geo_data, grid_origin, cw)
    return _greedy_separate(candidates, min_separation)


# ── progressive relaxation + assembly ─────────────────────────────────
def _select_with_relaxation(find_func, needed, initial_min_area, min_area_floor, **kwargs):
    """
    Try to find enough site candidates, progressively halving the minimum area
    requirement until enough are found or the floor is reached.

    Args:
        find_func: callable(min_area=..., **kwargs) -> list of candidate dicts
        needed: int, how many sites we want
        initial_min_area: float, starting minimum area in m²
        min_area_floor: float, smallest area we'll accept (stop relaxing below this)
        **kwargs: passed through to find_func

    Returns:
        list of up to `needed` site dicts (may be fewer if geometry is sparse)
    """
    current_min_area = initial_min_area
    candidates = []

    while current_min_area >= min_area_floor:
        candidates = find_func(min_area=current_min_area, **kwargs)
        if len(candidates) >= needed:
            break
        # not enough at this threshold, try smaller
        current_min_area *= 0.5

    if current_min_area < min_area_floor and len(candidates) < needed:
        # one final attempt at the floor
        candidates = find_func(min_area=min_area_floor, **kwargs)

    selected = candidates[:needed]

    # assign quality scores by rank (best = 1.0, worst = 0.5)
    for rank, site in enumerate(selected):
        site["quality"] = 1.0 - 0.5 * (rank / max(len(selected), 1))
        site.pop("_area", None)  # remove internal bookkeeping key

    return selected


def _generate_from_geometry(config, geo_data, needed_roosts, needed_forage):
    """
    Analyze voxel geometry to find roost and forage locations.

    Args:
        config: SimConfig
        geo_data: dict with 'geometry', 'grid_spacing', 'grid_spacing_z'
        needed_roosts: int, how many roosts to auto-generate
        needed_forage: int, how many forage sites to auto-generate

    Returns:
        (roost_list, forage_list) of site dicts ready for config.world
    """
    grid_origin = np.array(config.scaled_grid_origin)
    column_height, ground_mask = _build_column_height_map(geo_data, grid_origin)

    # absolute minimum areas below which a site is too small to be useful
    roost_area_floor = 16.0  # m², ~4x4m
    forage_area_floor = 50.0  # m², ~7x7m

    # find roosts on flat rooftops, relaxing area if needed
    roost_sites = _select_with_relaxation(
        find_func=_find_roost_candidates,
        needed=needed_roosts,
        initial_min_area=config.world_gen_min_roost_area,
        min_area_floor=roost_area_floor,
        column_height=column_height,
        ground_mask=ground_mask,
        geo_data=geo_data,
        grid_origin=grid_origin,
    )

    if len(roost_sites) < needed_roosts:
        # fallback: not enough flat rooftops, place remaining roosts on the ground
        shortfall = needed_roosts - len(roost_sites)
        print(
            f"[world_gen] warning: only found {len(roost_sites)} rooftop roosts, "
            f"placing {shortfall} on open ground"
        )
        ground_roosts = _place_ground_roosts(
            column_height, ground_mask, geo_data, grid_origin, shortfall, existing_sites=roost_sites
        )
        roost_sites.extend(ground_roosts)

    # find forage sites on open ground, relaxing area if needed
    forage_sites = _select_with_relaxation(
        find_func=_find_forage_candidates,
        needed=needed_forage,
        initial_min_area=config.world_gen_min_forage_area,
        min_area_floor=forage_area_floor,
        column_height=column_height,
        ground_mask=ground_mask,
        geo_data=geo_data,
        grid_origin=grid_origin,
    )

    # filter out forage candidates that overlap with roost sites
    min_separation = 40.0  # meters, minimum distance between any two auto-generated sites
    roost_centers = [np.array(r["center"][:2]) for r in roost_sites]
    separated_forage = []
    for site in forage_sites:
        site_center = np.array(site["center"][:2])
        too_close_to_roost = any(
            np.linalg.norm(site_center - rc) < min_separation for rc in roost_centers
        )
        too_close_to_other = any(
            np.linalg.norm(site_center - np.array(s["center"][:2])) < min_separation
            for s in separated_forage
        )
        if not too_close_to_roost and not too_close_to_other:
            separated_forage.append(site)
    forage_sites = separated_forage

    if len(forage_sites) < needed_forage:
        shortfall = needed_forage - len(forage_sites)
        print(
            f"[world_gen] warning: only found {len(forage_sites)} open-ground forage sites, "
            f"need {shortfall} more — placing at domain edges"
        )
        edge_sites = _place_edge_forage(
            column_height,
            geo_data,
            grid_origin,
            shortfall,
            existing_sites=forage_sites + roost_sites,
        )
        forage_sites.extend(edge_sites)

    return roost_sites, forage_sites


def _place_ground_roosts(column_height, ground_mask, geo_data, grid_origin, count, existing_sites):
    """
    Fallback: place roosts on the largest open ground patches when no flat rooftops exist.
    Used when geometry has no suitable elevated surfaces.
    """
    spacing_xy = geo_data["grid_spacing"]

    # reuse the forage candidate finder for open ground, but with smaller minimum
    candidates = _find_forage_candidates(
        column_height,
        ground_mask,
        geo_data,
        grid_origin,
        min_area=16.0,  # very permissive
    )

    # filter out candidates too close to existing sites (within 30m)
    existing_centers = [np.array(s["center"][:2]) for s in existing_sites]
    filtered = []
    for candidate in candidates:
        center_2d = np.array(candidate["center"][:2])
        too_close = any(np.linalg.norm(center_2d - ec) < 30.0 for ec in existing_centers)
        if not too_close:
            filtered.append(candidate)

    # take the best ones, cap roost size to 30m (roosts are smaller than forage fields)
    selected = filtered[:count]
    for site in selected:
        site["size"] = [min(site["size"][0], 30.0), min(site["size"][1], 30.0)]
        site.pop("_area", None)

    return selected


def _place_edge_forage(column_height, geo_data, grid_origin, count, existing_sites):
    """
    Last-resort fallback: place forage sites near domain edges when open ground is scarce.
    Distributes sites evenly around the domain perimeter.
    """
    spacing_xy = geo_data["grid_spacing"]
    ny, nx = geo_data["geometry"].shape[1], geo_data["geometry"].shape[2]

    domain_width = nx * spacing_xy
    domain_height = ny * spacing_xy
    domain_center_x = grid_origin[0] + domain_width / 2.0
    domain_center_y = grid_origin[1] + domain_height / 2.0

    # distribute around a circle at 80% of the half-domain size
    radius = min(domain_width, domain_height) * 0.4
    default_size = 40.0

    sites = []
    for i in range(count):
        angle = 2.0 * np.pi * i / max(count, 1)

        # walk inward along this spoke until the footprint is clear of buildings;
        # if nothing on the spoke is clear, skip the slot (fewer sites is better
        # than a forage site sitting on a rooftop).
        placed = False
        for r_frac in (1.0, 0.75, 0.5, 0.25):
            center_x = domain_center_x + radius * r_frac * np.cos(angle)
            center_y = domain_center_y + radius * r_frac * np.sin(angle)
            candidate_center = [float(center_x), float(center_y), float(grid_origin[2])]
            candidate_size = [default_size, default_size]
            if _footprint_has_obstruction(
                candidate_center,
                candidate_size,
                column_height,
                geo_data,
                grid_origin,
                clearance=3.0,
            ):
                continue
            sites.append(
                {
                    "center": candidate_center,
                    "size": candidate_size,
                    "forward": [1.0, 0.0, 0.0],
                    "normal": [0.0, 0.0, 1.0],
                    "quality": 0.5,
                }
            )
            placed = True
            break
        if not placed:
            print(f"[world_gen] edge-forage slot {i}: no building-free spot, skipping")

    return sites


# ── open-field fallback (no geometry at all) ──────────────────────────


def _generate_open_field_fallback(config, needed_roosts, needed_forage):
    """
    When no voxel geometry is available (open field simulation),
    place roosts near the spawn point and forage sites in a ring around it.

    This is a simple functional layout so the sim doesn't break,
    not an ecologically grounded placement.
    """
    spawn = np.array(config.spawn_point)
    ground_z = config.floor_z

    # place roosts near spawn, slightly offset so birds have somewhere to transit to
    roost_sites = []
    for i in range(needed_roosts):
        offset_angle = 2.0 * np.pi * i / max(needed_roosts, 1)
        offset_distance = 50.0  # meters from spawn
        roost_center = [
            float(spawn[0] + offset_distance * np.cos(offset_angle)),
            float(spawn[1] + offset_distance * np.sin(offset_angle)),
            float(ground_z),
        ]
        roost_sites.append(
            {
                "center": roost_center,
                "size": [20.0, 20.0],
                "forward": [1.0, 0.0, 0.0],
                "normal": [0.0, 0.0, 1.0],
                "quality": 1.0 - 0.3 * (i / max(needed_roosts, 1)),
            }
        )

    # place forage sites in a ring further out from the roost(s)
    forage_sites = []
    forage_radius = 200.0  # meters from spawn
    for i in range(needed_forage):
        angle = 2.0 * np.pi * i / max(needed_forage, 1) + 0.3  # offset from roost angles
        forage_center = [
            float(spawn[0] + forage_radius * np.cos(angle)),
            float(spawn[1] + forage_radius * np.sin(angle)),
            float(ground_z),
        ]
        forage_sites.append(
            {
                "center": forage_center,
                "size": [60.0, 60.0],
                "forward": [1.0, 0.0, 0.0],
                "normal": [0.0, 0.0, 1.0],
                "quality": 1.0 - 0.3 * (i / max(needed_forage, 1)),
            }
        )

    return roost_sites, forage_sites
