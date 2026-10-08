"""Prepare this elevated wind-farm GLB for the workstation's scene pipeline.

Run inside UrbanWorldModel with the holoscene Python. Original GLB is retained.
Static geometry only: no rotor motion, actuator disk, power or wake calibration.
"""

import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from pipelines.geometry.voxelization.prepare_glb import read_primitive, raster
from pipelines.geometry.voxelization.glb_plan import read_glb_header, local_bounds, plan_grid


def main():
    folder = ROOT / "input/region"
    source = folder / "region.glb"
    normalized = folder / "region_local.glb"
    out = ROOT / "output/region/geometry/voxel_8m"
    if (out / "metadata.json").exists():
        raise SystemExit("Geometry already exists; retained without overwriting.")
    doc, base = read_glb_header(source)
    original_bounds = local_bounds(doc)
    offset = math.floor(original_bounds[0, 2] / 8) * 8 - 8
    blob = bytearray(source.read_bytes()[base:])
    touched = set()
    for mesh in doc["meshes"]:
        for primitive in mesh["primitives"]:
            idx = primitive["attributes"]["POSITION"]
            if idx in touched:
                continue
            touched.add(idx)
            acc = doc["accessors"][idx]
            assert acc["componentType"] == 5126 and acc["type"] == "VEC3"
            bv = doc["bufferViews"][acc["bufferView"]]
            arr = np.ndarray(
                (acc["count"], 3),
                dtype="<f4",
                buffer=blob,
                offset=bv.get("byteOffset", 0) + acc.get("byteOffset", 0),
                strides=(bv.get("byteStride", 12), 4),
            )
            arr[:, 1] -= offset
            acc["min"] = arr.min(axis=0).tolist()
            acc["max"] = arr.max(axis=0).tolist()
    doc.setdefault("extras", {})["physics_vertical_datum"] = {
        "original_y_equals_local_y_plus_m": offset,
        "original_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    header = json.dumps(doc, separators=(",", ":")).encode()
    header += b" " * (-len(header) % 4)
    normalized.write_bytes(
        struct.pack("<4sII", b"glTF", 2, 28 + len(header) + len(blob))
        + struct.pack("<II", len(header), 0x4E4F534A)
        + header
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )
    doc, base = read_glb_header(normalized)
    plan = plan_grid(local_bounds(doc), 8)
    nx, ny = plan["nx"], plan["ny"]
    ox, oy = plan["origin_xy"]
    shape = (ny, nx)
    ground = np.full(shape, -np.inf, np.float32)
    roof = np.zeros(shape, np.float32)
    foot = np.zeros(shape, bool)
    roads = np.zeros(shape, bool)
    solid_objects = np.zeros((64, ny, nx), bool)
    centres = (np.arange(64)[:, None, None] + 0.5) * 8
    counts = {"terrain": 0, "road": 0, "decoration_excluded": 0, "static_object": 0}
    with normalized.open("rb") as handle:
        for node in doc["nodes"]:
            if "mesh" not in node:
                continue
            name = node.get("name", "")
            terrain = name.startswith("Terrain |")
            tags = json.loads(node.get("extras", {}).get("source_tags", "{}"))
            road = "highway" in tags
            decoration = name.startswith("Surface study |")
            cls = (
                "terrain"
                if terrain
                else "road"
                if road
                else "decoration_excluded"
                if decoration
                else "static_object"
            )
            counts[cls] += 1
            if decoration:
                continue
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                points, faces = read_primitive(doc, handle, base, primitive)
                vertices = points[:, [0, 2, 1]].copy()
                vertices[:, 1] *= -1
                hi = np.full(shape, -np.inf, np.float32)
                raster(vertices, faces, hi, ox, oy, 8.0)
                valid = np.isfinite(hi)
                if terrain:
                    ground = np.maximum(ground, hi)
                elif road:
                    roads |= valid
                else:
                    # Keep vertical gaps beneath nacelles and blades. Raster min/max
                    # separately per mesh; never extrude a rotor down to the ground.
                    lo_neg = np.full(shape, -np.inf, np.float32)
                    vertices[:, 2] *= -1
                    raster(vertices, faces, lo_neg, ox, oy, 8.0)
                    if not valid.any():
                        # Resolve subcell towers conservatively using their AABB.
                        low, high = points.min(axis=0), points.max(axis=0)
                        x0 = max(0, int(math.floor((low[0] - ox) / 8)))
                        x1 = min(nx, int(math.floor((high[0] - ox) / 8)) + 1)
                        y0 = max(0, int(math.floor((-high[2] - oy) / 8)))
                        y1 = min(ny, int(math.floor((-low[2] - oy) / 8)) + 1)
                        hi[y0:y1, x0:x1] = high[1]
                        lo_neg[y0:y1, x0:x1] = -low[1]
                        valid = np.isfinite(hi)
                    solid_objects |= (
                        valid[None] & (centres + 4 >= -lo_neg[None]) & (centres - 4 <= hi[None])
                    )
                    roof = np.maximum(roof, np.where(valid, hi, 0))
                    # Hydraulic footprints exclude suspended machinery.
                    if not any(k in name for k in ("blade", "rotor", "nacelle", "yaw")):
                        foot |= valid
    valid_ground = np.isfinite(ground)
    assert valid_ground.any(), "No terrain identified"
    nearest = distance_transform_edt(~valid_ground, return_distances=False, return_indices=True)
    ground = ground[tuple(nearest)]
    solid = solid_objects | (centres - 4 <= ground[None])
    assert local_bounds(doc)[1, 2] < 512, "Geometry exceeds wind domain"
    assert not solid[-1].any(), "No clearance above geometry"
    out.mkdir(parents=True, exist_ok=True)

    def save(name, value):
        np.save(out / name, value)

    def coarse(a):
        return a.reshape(ny // 4, 4, nx // 4, 4).max(axis=(1, 3))

    save("solid.npy", solid)
    save("height_m.npy", np.maximum(roof, ground))
    save("ground_mesh_m_yx.npy", ground)
    save("ground_mesh_valid_yx.npy", valid_ground)
    save("study_area_8m_yx.npy", valid_ground)
    save("footprint_8m_yx.npy", foot)
    save("footprint_32m_yx.npy", coarse(foot))
    save("height_32m_yx.npy", coarse(np.maximum(roof, ground)))
    for key, mask in {
        "grass": valid_ground & ~foot & ~roads,
        "paving": roads,
        "asphalt": np.zeros(shape, bool),
        "canopy": np.zeros(shape, bool),
    }.items():
        save(f"{key}_32m_yx.npy", coarse(mask))
    limits = [
        "Experimental SCALED urban surrogate applied to mountainous terrain; no CFD or observed validation.",
        "8 m fine / 32 m coupled grid; small objects enlarged or missed, conservative static raster occupancy.",
        "Turbines are stationary obstacles; no rotor dynamics, actuator disk, power generation or validated turbine wakes.",
        "Copernicus DSM is labelled native ~30 m, interpolated to a 10 m mesh; resampling does not add measured detail.",
        "Terrain extended by nearest edge only in computational padding; not additional surveyed terrain.",
        "Grass outside roads/structures is assumed landcover, not a measured classification.",
        "Solar and flood await location / north alignment and terrain assumptions.",
    ]
    metadata = {
        "source": str(normalized.resolve()),
        "source_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
        "original_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "original_vertical_offset_m": offset,
        "bounds_local_xyz_m": local_bounds(doc).tolist(),
        "source_region_origin_xyz_m": [float(ox), float(oy), 0.0],
        "shape_zyx": [64, ny, nx],
        "spacing_xyz_m": [8, 8, 8],
        "axis_order": "zyx",
        "gltf_to_local_xyz": "(x,-z,y)",
        "max_building_z_m": float(roof.max()),
        "footprint_fraction": float(foot.mean()),
        "classification_counts": counts,
        "ground_mesh_range_m": [float(ground.min()), float(ground.max())],
        "terrain_valid_fraction": float(valid_ground.mean()),
        "primitives_above_wind_domain": 0,
        "georeferenced": False,
        "method": "Terrain occupancy plus per-object vertical spans; subcell AABB fallback.",
        "limits": limits,
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (out / "above_wind_domain.json").write_text("[]")
    (folder / "preparation.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
