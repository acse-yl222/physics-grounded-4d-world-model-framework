"""Select reproducible demonstration ground sites from prepared scene rasters.

These are model-derived sites, not surveyed or approved landing facilities.
Prepared rasters must share the 2m ENU grid; semantic exclusion masks use 8m.
"""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt, minimum_filter, maximum_filter
from common.storage import Storage


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--geometry", type=Path, required=True)
    ap.add_argument("--version", default="stations_ground_20261007")
    ap.add_argument("--count", type=int, default=30)
    args = ap.parse_args()
    geo = args.geometry
    meta = json.loads((geo / "metadata.json").read_text())
    origin = np.array(meta["source_region_origin_xyz_m"])
    height = np.load(geo / "height_m.npy")
    support = np.load(geo / "ground_mesh_m_yx.npy")
    supported = np.load(geo / "ground_mesh_valid_yx.npy").astype(bool)
    ny, nx = height.shape
    coarse = maximum_filter(height.reshape(ny // 4, 4, nx // 4, 4).max(axis=(1, 3)), size=3) > 0
    expand = lambda a: np.repeat(np.repeat(a, 4, axis=0), 4, axis=1)
    roads = expand(np.load(geo / "asphalt_8m_yx.npy") > 0)
    canopy = expand(np.load(geo / "canopy_8m_yx.npy") > 0)
    clearance = distance_transform_edt(~(roads | canopy)) * 2
    valid = (
        (
            minimum_filter(
                (supported & np.isfinite(support) & (abs(support) < 0.5)).astype("u1"), size=3
            )
            > 0
        )
        & ~expand(coarse)
        & (clearance >= 8)
    )
    # Keep sites away from the numerical sponge and the edge of measured geometry.
    yy, xx = np.indices(height.shape)
    bounds = np.array(meta["bounds_local_xyz_m"])
    wx = origin[0] + (xx + 0.5) * 2
    wy = origin[1] + (yy + 0.5) * 2
    valid &= (
        (wx > bounds[0, 0] + 100)
        & (wx < bounds[1, 0] - 100)
        & (wy > bounds[0, 1] + 100)
        & (wy < bounds[1, 1] - 100)
    )
    ys, xs = np.nonzero(valid)
    coords = np.c_[origin[0] + (xs + 0.5) * 2, origin[1] + (ys + 0.5) * 2]
    if len(coords) < args.count:
        raise ValueError("Insufficient supported ground")
    # First site near the scene origin (White City campus); spread remaining sites.
    k = int(np.linalg.norm(coords, axis=1).argmin())
    selected = []
    nearest = np.full(len(coords), np.inf)
    for i in range(args.count):
        selected.append(k)
        nearest = np.minimum(nearest, np.linalg.norm(coords - coords[k], axis=1))
        k = int(nearest.argmax())
    stations = []
    for i, k in enumerate(selected):
        role = "hub" if i < 3 else "collection" if i < 12 else "dropoff"
        label = (
            ("H" + str(i + 1)) if i < 3 else ("C" + str(i - 2)) if i < 12 else ("D" + str(i - 11))
        )
        x, y = coords[k]
        surface = float(support[ys[k], xs[k]])
        stations.append(
            dict(
                id=i + 1,
                station_id=label,
                label=label,
                role=role,
                name=f"White City {label} (model ground site)",
                xyz=[float(x), surface + 0.15, float(-y)],
                ground_surface_enu_z_m=surface,
                marker_offset_m=0.15,
                full_coarse_column_free=True,
                road_canopy_clearance_sampled_m=float(clearance[ys[k], xs[k]]),
                candidate_status="MODEL_GROUND_SITE; NOT_SURVEYED",
                source_geometry_sha256=meta["source_sha256"],
            )
        )
    target = Storage.load().assets(args.scene, "input") / args.version
    target.mkdir(parents=True, exist_ok=False)
    (target / "stations.json").write_text(json.dumps(stations, indent=2) + "\n")
    audit = dict(
        method="Farthest-point spread on supported 6x6m ground patches; free padded 8m columns; 8m road/canopy clearance",
        geometry=meta,
        rasters={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                geo / n
                for n in [
                    "height_m.npy",
                    "ground_mesh_m_yx.npy",
                    "ground_mesh_valid_yx.npy",
                    "asphalt_8m_yx.npy",
                    "canopy_8m_yx.npy",
                ]
            ]
        },
        candidate_count=len(coords),
    )
    (target / "selection.json").write_text(json.dumps(audit, indent=2) + "\n")
    np.savez_compressed(target / "ground_site_audit.npz", valid=valid, origin_enu=origin)
    print(target, "\n", json.dumps(stations))


if __name__ == "__main__":
    main()
