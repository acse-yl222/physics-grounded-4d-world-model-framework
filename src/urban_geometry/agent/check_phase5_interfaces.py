"""Plan-only raised-stair adjacency preflight, before master vertical/ray tests."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import json
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union

R = authoring_path()
g = json.loads((R / "geometry.json").read_text())
contract = json.loads((R / "references/phase5_va/interface_contract.json").read_text())
e = contract["interfaces_from_final_check"]["entrances"][0]
p = Polygon([v[:2] for v in e["stairs_extent_xyz"]])
collisions = []
for b in g["buildings"]:
    if b["id"] == contract["feature_id"]:
        continue
    ps = [Polygon(v["outer"], v.get("holes", [])) for v in b["geometry"]]
    if not ps:
        continue
    area = p.intersection(unary_union(ps)).area
    if area > 0.001:
        collisions.append({"id": b["id"], "area_m2": area})
r = {
    "check": "VA raised stair footprint against all other new building footprints",
    "stairs_area_m2": p.area,
    "collisions": collisions,
    "passed": not collisions,
    "limitations": [
        "Plan-only; existing Imperial geometry and ground/riser/entrance rays must be checked in integrated master.",
        "Contract stairs_extent_xyz is authoring frame; diagnostic threshold_xyz is already campus frame and not used here.",
    ],
}
(R / "docs/phase5_interface_plan_check.json").write_text(json.dumps(r, indent=2) + "\n")
print(json.dumps(r, indent=2))
assert not collisions
