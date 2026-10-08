"""Plan and voxelize a crop containing all 23 turbines; remove static blades for actuator forces."""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from common.runtime import source_path, trial_root
import argparse, json, math, sys, hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt

from urban_geometry.voxelization.prepare_glb import read_primitive, raster
from urban_geometry.voxelization.glb_plan import read_glb_header


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args()
    source = source_path("region_input", "region_local.glb")
    doc, base = read_glb_header(source)
    objects = []
    turbines = {}
    with source.open("rb") as f:
        for node in doc["nodes"]:
            if "mesh" not in node:
                continue
            name = node.get("name", "")
            bid = node.get("extras", {}).get("building_id", "")
            for prim in doc["meshes"][node["mesh"]]["primitives"]:
                points, faces = read_primitive(doc, f, base, prim)
                v = points[:, [0, 2, 1]].copy()
                v[:, 1] *= -1
                objects.append((name, v, faces))
                if "rotor hub and spinner" in name:
                    turbines.setdefault(bid, {})["hub_xyz_m"] = ((v.min(0) + v.max(0)) / 2).tolist()
                if "blade" in name:
                    turbines.setdefault(bid, {}).setdefault("blade_vertices", []).append(v)
    disk = []
    for bid, d in sorted(turbines.items()):
        hub = np.array(d["hub_xyz_m"])
        r = float(np.linalg.norm(np.concatenate(d["blade_vertices"]) - hub, axis=1).max())
        disk.append(
            dict(id=bid, hub_xyz_m=hub.tolist(), radius_m=r, diameter_m=2 * r, normal_xyz=[1, 0, 0])
        )
    assert len(disk) == 23
    hubs = np.array([t["hub_xyz_m"] for t in disk])
    R = max(t["radius_m"] for t in disk)
    D = 2 * R
    # Same original x-directed wind; all rotors are assumed yawed into it.
    low = hubs.min(0) - [R + 5 * D, R + 3 * D, 0]
    high = hubs.max(0) + [R + 8 * D, R + 3 * D, 0]
    cell = 2.0
    block = 256
    nx = int(math.ceil((high[0] - low[0]) / (cell * block)) * block)
    ny = int(math.ceil((high[1] - low[1]) / (cell * block)) * block)
    nz = 256
    ox = math.floor(low[0] / cell) * cell
    oy = math.floor(((low[1] + high[1]) - ny * cell) / 2 / cell) * cell
    ox, oy = -1776.0, -992.0
    meta = dict(
        cell_m=cell,
        shape_zyx=[nz, ny, nx],
        origin_xyz_m=[ox, oy, 0],
        size_xyz_m=[nx * cell, ny * cell, nz * cell],
        turbines=disk,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source="region_local.glb; geometry dimensions visually approximated, not manufacturer data",
        crop_margins={"upstream_D_min": 5, "downstream_D_min": 8, "lateral_D_min": 3},
        assumptions=[
            "All 23 disks yawed to +x; U0 and Ct are assumed, not measured.",
            "Static blades and rotor hub/spinner removed; towers and nacelles retained.",
            "2 m terrain re-rasterized from original mesh; DSM native ~30 m, no new measured detail.",
            "Any terrain outside source coverage uses nearest-edge extension.",
        ],
    )
    meta["cell_count"] = nx * ny * nz
    meta["estimated_original_solver_peak_gib"] = meta["cell_count"] / 25165824 * 4.62
    out = trial_root("windfarm", "region_crop_2m_geometry")
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "turbines"}, indent=2), flush=True)
    print(
        "rotor diameter range",
        min(t["diameter_m"] for t in disk),
        D,
        "hub bounds",
        hubs.min(0),
        hubs.max(0),
        flush=True,
    )
    if a.plan_only:
        return
    ground = np.full((ny, nx), -np.inf, np.float32)
    solid = np.zeros((nz, ny, nx), bool)
    centres = (np.arange(nz) + 0.5) * cell
    removed = 0
    retained = 0
    for name, v, faces in objects:
        if name.startswith("Surface study |"):
            continue
        if "blade" in name or "rotor hub and spinner" in name:
            removed += 1
            continue
        lo = v.min(0)
        hi = v.max(0)
        x0 = max(0, int(np.floor((lo[0] - ox) / cell)))
        x1 = min(nx, int(np.floor((hi[0] - ox) / cell)) + 1)
        y0 = max(0, int(np.floor((lo[1] - oy) / cell)))
        y1 = min(ny, int(np.floor((hi[1] - oy) / cell)) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        upper = np.full((y1 - y0, x1 - x0), -np.inf, np.float32)
        raster(v, faces, upper, ox + x0 * cell, oy + y0 * cell, cell)
        if name.startswith("Terrain |"):
            ground[y0:y1, x0:x1] = np.maximum(ground[y0:y1, x0:x1], upper)
            continue
        # Roads are already represented by the terrain surface; retain other geometry.
        if "road" in name.lower():
            continue
        lower = np.full_like(upper, -np.inf)
        v = v.copy()
        v[:, 2] *= -1
        raster(v, faces, lower, ox + x0 * cell, oy + y0 * cell, cell)
        valid = np.isfinite(upper) & np.isfinite(lower)
        if not valid.any():
            upper.fill(hi[2])
            lower.fill(-lo[2])
            valid[:] = True
        z0 = max(0, int(np.floor(lo[2] / cell)))
        z1 = min(nz, int(np.floor(hi[2] / cell)) + 1)
        solid[z0:z1, y0:y1, x0:x1] |= (
            valid[None]
            & (centres[z0:z1, None, None] + cell / 2 >= -lower[None])
            & (centres[z0:z1, None, None] - cell / 2 <= upper[None])
        )
        retained += 1
    valid = np.isfinite(ground)
    assert valid.any()
    idx = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    ground = ground[tuple(idx)]
    del idx
    solid |= np.arange(nz)[:, None, None] * cell <= ground[None]
    assert not solid[-1].any()
    for t in disk:
        hx, hy, hz = t["hub_xyz_m"]
        r = t["radius_m"]
        assert (
            ox < hx < ox + nx * cell
            and oy < hy - r < hy + r < oy + ny * cell
            and hz + r < nz * cell
        )
    np.save(out / "solid.npy", solid)
    np.save(out / "ground.npy", ground)
    np.save(out / "terrain_valid.npy", valid)
    meta.update(
        ground_range_m=[float(ground.min()), float(ground.max())],
        terrain_coverage_fraction=float(valid.mean()),
        removed_rotor_meshes=removed,
        retained_static_meshes=retained,
        solid_fraction=float(solid.mean()),
        all_23_rotors_inside=True,
    )
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    print("GEOMETRY COMPLETE", flush=True)


if __name__ == "__main__":
    main()
