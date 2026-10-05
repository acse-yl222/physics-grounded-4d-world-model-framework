"""img2city/city/render_regress.py -- the NO-REGRESSION GATE for library growth.

"Extending the library must not change what existing regions render" is a
property to be MEASURED, not promised. The frozen specs on disk are the fixture:
assemble the scene, fingerprint every object (vertex count, dimensions,
material bindings -- stabler than pixels, no render noise), and compare against
the snapshot taken before the library changed. Any drift is listed object by
object; an empty diff is the licence to merge a new part.

Run it around every library change:

  python -m img2city.city.generate --out data/city_sk --assemble-only --min-area 0
  python -m img2city.city.render_regress --snapshot --out data/city_sk     # before merging
  ... extend components.py / SPEC_LINES ...
  python -m img2city.city.generate --out data/city_sk --assemble-only --min-area 0
  python -m img2city.city.render_regress --check --out data/city_sk        # must be clean

Scene-layer objects (trees, roads, vehicles, shops, furniture) are included:
they are deterministic from their cached JSON, so they too must not drift.
Needs the live Blender + BlenderMCP socket (:9876) with the scene assembled.
"""
from __future__ import annotations
import argparse
import json
import os

from img2city import config
import socket

FP_CODE = r"""
import bpy, json
fp = {}
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    d = o.dimensions
    fp[o.name] = [len(o.data.vertices), len(o.data.polygons),
                  round(d.x, 3), round(d.y, 3), round(d.z, 3),
                  [m.name if m else "" for m in o.data.materials]]
print("FP" + json.dumps(fp, sort_keys=True))
"""


def _send(code, timeout=1800):
    payload = json.dumps({"type": "execute_code",
                          "params": {"code": code}}).encode()
    buf, resp = b"", None
    with socket.create_connection((config.MCP_HOST, config.MCP_PORT), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(payload)
        while True:
            ch = s.recv(65536)
            if not ch:
                break
            buf += ch
            try:
                resp = json.loads(buf.decode())
                break
            except Exception:
                continue
    if resp is None or resp.get("status") != "success":
        raise RuntimeError((resp or {}).get("message", "no reply"))
    return resp["result"]


def fingerprint():
    txt = _send(FP_CODE).get("result", "")
    i = txt.index("FP")
    return json.loads(txt[i + 2:].splitlines()[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    path = os.path.join(os.path.abspath(a.out), "regress_baseline.json")
    fp = fingerprint()
    if not a.snapshot and not os.path.exists(path):
        raise SystemExit('Regression baseline is missing; explicitly snapshot the unchanged scene first')
    if a.snapshot:
        json.dump(fp, open(path, "w"))
        print(f"[regress] baseline: {len(fp)} mesh objects -> {path}")
        return
    base = json.load(open(path))
    gone = sorted(set(base) - set(fp))
    new = sorted(set(fp) - set(base))
    changed = sorted(k for k in set(base) & set(fp) if base[k] != fp[k])
    if not (gone or new or changed):
        print(f"[regress] CLEAN: {len(fp)} objects match the baseline exactly")
        return
    print(f"[regress] DRIFT: {len(gone)} gone, {len(new)} new, "
          f"{len(changed)} changed (baseline {len(base)} objects)")
    for k in gone[:10]:
        print(f"  - {k}")
    for k in new[:10]:
        print(f"  + {k}")
    for k in changed[:10]:
        print(f"  ~ {k}: {base[k]} -> {fp[k]}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
