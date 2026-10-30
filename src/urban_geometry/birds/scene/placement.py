"""Roost and forage sites chosen from the scene's own land cover (heuristic placement, not a survey).

Forage, in order of preference (the first tier with enough sites is used, shortfalls are filled
from the next tier):
  1. park       - low vegetation (grass, lawns, low planting) on open ground
  2. waterside  - open, non-road ground within WATERSIDE_M of water
  3. rooftop    - flat roofs (only when the scene offers neither parks nor waterside ground)
Roosts: flat, unobstructed rooftops from the bird model's own roost finder (world_gen), chosen to
sit within ROOST_FORAGE_M of the best forage. Everything stays inside the area the scene's
published fields cover, so the birds always sample real wind / pollution / temperature.

Site dicts follow config.world (center, size, forward, normal, quality) and add "kind".
"""

import numpy as np
from scipy.ndimage import binary_opening, distance_transform_edt, label, maximum_filter

WATERSIDE_M = 40.0
ROOST_FORAGE_M = (150.0, 1200.0)  # allowed horizontal roost -> forage distance band
PREFERRED_COMMUTE_M = (500.0, 400.0)  # (centre, width) of the preferred roost -> forage distance
SITE_SEPARATION_M = 80.0  # minimum spacing between forage site centres
FIELD_MARGIN_M = 150.0  # keep sites this far inside the field coverage
MAX_FORAGE_SIDE_M = 60.0  # same cap as world_gen forage sites
MAX_ROOST_SIDE_M = 30.0  # same cap as world_gen roosts
TALL_CLEAR_M = (
    16.0,
    8.0,
)  # ground forage sites keep this far from any structure reaching this height


def _inside(g, box, margin):
    x, y = g.xy(*np.indices((g.ny, g.nx)))
    return (
        (x > box[0] + margin)
        & (x < box[2] - margin)
        & (y > box[1] + margin)
        & (y < box[3] - margin)
    )


def _disk(radius_cells):
    r = int(radius_cells)
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return xx * xx + yy * yy <= r * r


def _patch_candidates(g, mask, kind, min_area, z_of):
    """Local maxima of the distance-to-edge inside mask = centres of the roomiest open squares."""
    mask = binary_opening(mask, structure=_disk(2))  # drop verges and slivers (< ~4 m wide)
    labels, n = label(mask)
    if n == 0:
        return []
    areas = np.bincount(labels.ravel()) * g.cell * g.cell
    edt = distance_transform_edt(mask) * g.cell  # metres to the patch edge
    r_min = np.sqrt(min_area) / 2
    peaks = (edt >= r_min) & (edt == maximum_filter(edt, size=5))
    rows, cols = np.nonzero(peaks)
    out = []
    for r, c in zip(rows, cols):
        x, y = g.xy(r, c)
        side = float(np.clip(1.4 * edt[r, c], 10.0, MAX_FORAGE_SIDE_M))
        out.append(
            {
                "center": [float(x), float(y), float(z_of(r, c))],
                "size": [side, side],
                "forward": [1.0, 0.0, 0.0],
                "normal": [0.0, 0.0, 1.0],
                "kind": kind,
                "_area": float(areas[labels[r, c]]),
                "_patch": f"{kind}:{labels[r, c]}",
                "_room": float(edt[r, c]),
            }
        )
    # big open patches first, then the roomiest spot within them
    out.sort(key=lambda s: (s["_area"], s["_room"]), reverse=True)
    return out


def _solid_columns(g, rows=256):
    """(ny, nx) columns of the voxel grid with any solid voxel (read in row blocks, solid is memory-mapped)."""
    out = np.empty((g.ny, g.nx), dtype=bool)
    for r in range(0, g.ny, rows):
        out[r : r + rows] = np.asarray(g.solid[:, r : r + rows]).any(axis=0)
    return out


def _tall_clearance(g, rows=256):
    """
    (ny, nx) metres to the nearest column with solid at or above TALL_CLEAR_M[1]. The bird model plans
    routes on a coarse grid; a forage site right next to a tall building can sit where its route guidance
    stops short of the site, and birds then circle there all day.
    """
    k = int(np.ceil((TALL_CLEAR_M[1] - g.origin[2]) / g.cell))
    tall = np.empty((g.ny, g.nx), dtype=bool)
    for r in range(0, g.ny, rows):
        tall[r : r + rows] = np.asarray(g.solid[k:, r : r + rows]).any(axis=0)
    return distance_transform_edt(~tall) * g.cell


def forage_candidates(g, box, min_area):
    """All forage candidates, tier by tier."""
    inside = _inside(g, box, FIELD_MARGIN_M)
    # no solid voxel anywhere in the column: a low object on the grass (bench, kerb, wall) fills a whole
    # voxel, and birds that hop onto it end up inside solid
    open_ground = ~g.building & ~g.water & ~g.tree & ~_solid_columns(g) & inside
    ground_z = lambda r, c: g.ground[r, c]
    tiers = {
        "park": _patch_candidates(g, g.low_vegetation & open_ground, "park", min_area, ground_z),
    }
    near_water = distance_transform_edt(~g.water) * g.cell <= WATERSIDE_M
    if g.water.any():
        waterside = open_ground & near_water & ~g.low_vegetation & ~g.asphalt
        tiers["waterside"] = _patch_candidates(g, waterside, "waterside", min_area, ground_z)
    else:
        tiers["waterside"] = []
    roof_z = lambda r, c: g.height[r, c]
    clear = _tall_clearance(g)
    for kind in ("park", "waterside"):
        tiers[kind] = [
            s
            for s in tiers[kind]
            if clear[tuple(int(v) for v in g.index(*s["center"][:2]))] >= TALL_CLEAR_M[0]
        ]
    tiers["rooftop"] = [
        s | {"kind": "rooftop", "_area": s["size"][0] * s["size"][1], "_patch": f"roof:{i}"}
        for i, s in enumerate(roof_candidates(g, box, min_area, roof_z))
    ]
    return tiers


def roof_candidates(g, box, min_area, z_of=None):
    """
    Flat unobstructed rooftops with world_gen's roost predicate: a square of side sqrt(min_area)
    (capped at MAX_ROOST_SIDE_M) lying entirely on one roof level (heights quantised to the cell),
    ranked by how deep it sits in that level. world_gen enumerates every such window and separates
    them greedily, which is too slow on a whole city at 2 m; here only each roof's roomiest windows
    (local maxima of the depth) are kept, so the predicate is the same and the list stays short.
    """
    inside = _inside(g, box, FIELD_MARGIN_M)
    side_m = min(float(np.sqrt(min_area)), MAX_ROOST_SIDE_M)
    cw = max(1, round(side_m / g.cell))
    quantised = np.round(g.height / g.cell) * g.cell
    elevated = g.building & inside
    roofs = []
    for level in np.unique(quantised[elevated]):
        level_mask = elevated & (quantised == level)
        if level_mask.sum() < cw * cw:
            continue
        blocked = (~level_mask).astype(np.int64)
        sat = np.pad(blocked, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        win = sat[cw:, cw:] - sat[:-cw, cw:] - sat[cw:, :-cw] + sat[:-cw, :-cw]
        depth = distance_transform_edt(level_mask)
        # window (r0, c0) covers rows r0..r0+cw-1; its centre cell is r0 + cw // 2
        centre_depth = depth[cw // 2 : cw // 2 + win.shape[0], cw // 2 : cw // 2 + win.shape[1]]
        score = np.where(win == 0, centre_depth, 0.0)
        peaks = (score > 0) & (score == maximum_filter(score, size=max(3, cw)))
        for r0, c0 in zip(*np.nonzero(peaks)):
            r, c = r0 + cw // 2, c0 + cw // 2
            x, y = g.xy(r0 + cw / 2 - 0.5, c0 + cw / 2 - 0.5)
            roofs.append(
                {
                    "center": [float(x), float(y), float(z_of(r, c) if z_of else level)],
                    "size": [cw * g.cell, cw * g.cell],
                    "forward": [1.0, 0.0, 0.0],
                    "normal": [0.0, 0.0, 1.0],
                    "_room": float(score[r0, c0]) * g.cell,
                }
            )
    roofs.sort(key=lambda s: s["_room"], reverse=True)
    kept = []
    for s in roofs:  # same 40 m spacing as world_gen's greedy separation
        if all(np.hypot(*(np.array(s["center"][:2]) - k["center"][:2])) >= 40.0 for k in kept):
            kept.append(s)
        if len(kept) >= 2000:
            break
    return kept


def _xy(site):
    return np.array(site["center"][:2])


FLOCK_SEPARATION_M = (
    1000.0,
    300.0,
)  # wanted / smallest distance between the roosts of different flocks


def _clean(site):
    return {k: v for k, v in site.items() if not k.startswith("_")}


def choose_flocks(
    g,
    field_box,
    n_flocks=4,
    n_forage=3,
    min_roost_area=200.0,
    min_forage_area=400.0,
):
    """
    Independent flocks, each with its own rooftop roost and n_forage forage sites of its own (no
    sharing). Flocks are placed one at a time: the best-scoring roof (rich forage at a comfortable
    commute, not yet taken) that is at least FLOCK_SEPARATION_M from every earlier roost, relaxing the
    separation if the scene cannot fit them all. Returns a list of (world, report), one per flock.
    """
    tiers = forage_candidates(g, field_box, min_forage_area)
    ground = tiers["park"] + tiers["waterside"]
    roofs = roof_candidates(g, field_box, min_roost_area, lambda r, c: g.height[r, c])
    if not roofs:
        raise ValueError("no flat rooftop roost candidates inside the field coverage")
    lo, hi = ROOST_FORAGE_M
    mid, width = PREFERRED_COMMUTE_M

    def commute(d):
        return ((d >= lo) & (d <= hi)) * np.exp(-(((d - mid) / width) ** 2))

    taken = []  # forage sites of earlier flocks

    def free(site):
        return all(np.linalg.norm(_xy(site) - _xy(k)) >= SITE_SEPARATION_M for k in taken)

    def pick_forage(home):
        def rank(s):
            return float(np.sqrt(s["_area"]) * commute(np.linalg.norm(_xy(s) - home)))

        # parks first; waterside and rooftops only make up a shortfall. Within a tier, one site per
        # patch first (distinct parks), then further sites in patches already used by this flock.
        forage = []
        for kind in ("park", "waterside", "rooftop"):
            ranked = [s for s in sorted(tiers[kind], key=rank, reverse=True) if rank(s) > 0]
            for distinct in (True, False):
                for s in ranked:
                    if len(forage) == n_forage:
                        break
                    if distinct and any(s["_patch"] == k["_patch"] for k in forage):
                        continue
                    if free(s) and all(
                        np.linalg.norm(_xy(s) - _xy(k)) >= SITE_SEPARATION_M for k in forage
                    ):
                        forage.append(s)
        return forage

    flocks, roosts = [], []
    separation = FLOCK_SEPARATION_M[0]
    while len(flocks) < n_flocks:
        pool = [s for s in (ground or tiers["rooftop"]) if free(s)]
        if not pool:
            break
        pool_xy = np.array([_xy(s) for s in pool])
        pool_w = np.array([np.sqrt(s["_area"]) for s in pool])  # bigger patches matter more

        def score(roof, pool_xy=pool_xy, pool_w=pool_w):
            d = np.linalg.norm(pool_xy - _xy(roof), axis=1)
            return float((pool_w * commute(d)).sum())

        placed = False
        for roof in sorted(roofs[:400], key=score, reverse=True):
            if any(np.linalg.norm(_xy(roof) - _xy(r)) < separation for r in roosts):
                continue
            forage = pick_forage(_xy(roof))
            if not forage:
                continue
            roosts.append(roof)
            taken.extend(forage)
            flocks.append((roof, forage))
            placed = True
            break
        if not placed:
            if separation <= FLOCK_SEPARATION_M[1]:
                break
            separation = max(FLOCK_SEPARATION_M[1], separation * 0.75)
    if not flocks:
        raise ValueError("no roost with forage within the commute band inside the field coverage")

    out = []
    for roof, forage in flocks:
        home = _xy(roof)
        for rank, s in enumerate(forage):
            s["quality"] = 1.0 - 0.5 * rank / max(len(forage), 1)
        roof["quality"], roof["kind"] = 1.0, "rooftop"
        report = {
            "rule": "forage: parks, then waterside ground, then flat roofs; roosts: flat rooftops near forage",
            "candidates": {k: len(v) for k, v in tiers.items()},
            "roof_candidates": len(roofs),
            "roost_forage_band_m": list(ROOST_FORAGE_M),
            "roost_separation_m": separation,
            "forage": [
                {
                    "kind": s["kind"],
                    "center": s["center"],
                    "size": s["size"],
                    "patch_area_m2": round(s["_area"]),
                    "distance_to_roost_m": round(float(np.linalg.norm(_xy(s) - home))),
                }
                for s in forage
            ],
            "roosts": [{"center": roof["center"], "size": roof["size"]}],
        }
        world = {
            "roosts": [_clean(roof)],
            "forage_sites": [_clean(s) for s in forage],
            "roads": [],
            "point_sources": [],
        }
        out.append((world, report))
    return out


def choose_sites(g, field_box, n_roosts=1, n_forage=3, min_roost_area=200.0, min_forage_area=400.0):
    """One flock (kept for single-flock use): returns (world dict, report)."""
    return choose_flocks(g, field_box, 1, n_forage, min_roost_area, min_forage_area)[0]
