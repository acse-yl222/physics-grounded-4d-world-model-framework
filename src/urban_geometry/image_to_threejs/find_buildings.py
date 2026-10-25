"""Look up prepared scene buildings by name or location (for landmark authoring).

Examples:
  python3 find_buildings.py --name "albert hall"
  python3 find_buildings.py --near 1500 -1000 --radius 80
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

DEFAULT = (
    Path(__file__).resolve().parents[3] / "cache/imperial_corridor/image_to_threejs/scene.json"
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--scene", type=Path, default=DEFAULT)
    p.add_argument("--name", help="case-insensitive substring of the building name")
    p.add_argument("--near", nargs=2, type=float, metavar=("X", "Y"), help="ENU metres")
    p.add_argument("--radius", type=float, default=60.0)
    p.add_argument("--min-area", type=float, default=0.0)
    p.add_argument("--json", action="store_true", help="print full records including footprints")
    args = p.parse_args()
    buildings = json.loads(args.scene.read_text())["buildings"]
    out = []
    for b in buildings:
        if args.name and args.name.lower() not in (b.get("name") or "").lower():
            continue
        if args.near and math.dist(b["c"], args.near) > args.radius:
            continue
        ring = b["polys"][0][0]
        area = (
            abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2
        )
        if area < args.min_area:
            continue
        out.append((area, b))
    out.sort(key=lambda t: -t[0])
    for area, b in out:
        if args.json:
            print(json.dumps(b))
        else:
            print(
                f"{b['id']}  area={area:7.0f}  c=({b['c'][0]:.0f},{b['c'][1]:.0f})  h={b['h']:.1f} "
                f"floors={b['floors']} roof={b['roof']} cls={b.get('cls')} parts={len(b.get('parts', []))} "
                f"name={b.get('name', '')!r}{'  CLAIMED:' + b['landmark'] if b.get('landmark') else ''}"
            )


if __name__ == "__main__":
    main()
