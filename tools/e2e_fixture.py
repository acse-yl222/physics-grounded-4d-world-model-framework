"""Small, self-contained GLB input for the real geometry pipeline."""

import json
import struct
import numpy as np


def create_workspace(base):
    workspace = base / "workspace"
    workspace.mkdir()
    data = base / "data"
    source = data / "project/south_ken/input/fixture.glb"
    source.parent.mkdir(parents=True)
    (workspace / "storage.local.json").write_text(
        json.dumps({"data_root": str(data), "cache_root": str(base / "scratch")})
    )
    # An 8 x 8 m roof at 3 m height, in glTF's x-east/y-up/z-south frame.
    vertices = np.array([[0, 3, 0], [8, 3, 0], [8, 3, -8], [0, 3, -8]], dtype="<f4")
    indices = np.array([0, 1, 2, 0, 2, 3], dtype="<u2")
    binary = vertices.tobytes() + indices.tobytes()
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "building_fixture"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": vertices.nbytes, "target": 34962},
            {
                "buffer": 0,
                "byteOffset": vertices.nbytes,
                "byteLength": indices.nbytes,
                "target": 34963,
            },
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 4,
                "type": "VEC3",
                "min": vertices.min(axis=0).tolist(),
                "max": vertices.max(axis=0).tolist(),
            },
            {"bufferView": 1, "componentType": 5123, "count": 6, "type": "SCALAR"},
        ],
    }
    payload = json.dumps(document).encode()
    payload += b" " * (-len(payload) % 4)
    source.write_bytes(
        struct.pack("<4sII", b"glTF", 2, 28 + len(payload) + len(binary))
        + struct.pack("<I4s", len(payload), b"JSON")
        + payload
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )
    config = {
        "scene": "south_ken",
        "source": "fixture.glb",
        "stages": ["geometry", "visualize"],
        "domain": {"cell_m": 1, "wind_layers": 4},
        "georeference": {"latitude_deg": 0, "longitude_deg": 0, "terrain": "synthetic"},
        "visualize": {"title": "E2E synthetic fixture"},
    }
    (workspace / "pipeline.json").write_text(json.dumps(config))
    return workspace
