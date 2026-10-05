"""img2city/scene/traffic_audit.py -- collision audit for the vehicle layer (08-19).

Checks, on the rendered bodies (vehicle_assets.BODY), that
  * no parked body touches a built outline (OBB/polygon actually raised);
  * no two static bodies overlap;
  * no animated body (traffic_anim.json) touches a building, a parked body,
    or another animated body at the same time step.
Exit code 1 if any count is non-zero -- run after vehicle_assets + traffic_sim.

    python -m img2city.scene.traffic_audit --out data/city_sk
"""
import argparse
import json
import os
import sys
from img2city.scene import vehicles as va
from img2city.scene.shops import built_outlines


def audit(out, verbose=True):
    cars = json.load(open(os.path.join(out, "vehicles.json")))
    af = os.path.join(out, "traffic_anim.json")
    anim = json.load(open(af)) if os.path.exists(af) else {"routes": []}
    d = json.load(open(os.path.join(out, "buildings.json")))
    ol = built_outlines(out, d["buildings"])
    polys = [p for p, _ in ol.values()] + \
            [[tuple(q) for q in b["pts"]] for b in d["buildings"] if b["id"] not in ol]
    obst = [(p, va._bbox(p)) for p in polys]
    movers = {r["i"] for r in anim["routes"]}
    def body(v):
        return va._rect(v["x"], v["y"], v["ang"], *va.BODY.get(v["kind"], va.BODY["car"]))
    stat = [(body(v), i) for i, v in enumerate(cars) if i not in movers]
    stat = [(r, va._bbox(r), i) for r, i in stat]
    def hit(r, rb, obs):
        return any(va._bb_touch(rb, ob) and va._poly_hit(r, p) for p, ob in obs)
    res = {"static_in_building": sum(1 for r, rb, _ in stat if hit(r, rb, obst)),
           "static_overlap": sum(1 for k, (r, rb, _) in enumerate(stat)
                                 if hit(r, rb, [(q, qb) for q, qb, _ in stat[k + 1:]])),
           "moving_in_building": 0, "moving_hits_parked": 0, "moving_hits_moving": 0,
           "moving_samples": 0}
    bytime = {}
    for r in anim["routes"]:
        L, W = va.BODY.get(r["kind"], va.BODY["car"])
        for t, x, y, ang in r["samples"]:
            b = va._rect(x, y, ang, L, W); bb = va._bbox(b)
            res["moving_samples"] += 1
            res["moving_in_building"] += hit(b, bb, obst)
            res["moving_hits_parked"] += hit(b, bb, [(q, qb) for q, qb, _ in stat])
            bytime.setdefault(t, []).append((b, bb))
    for rs in bytime.values():
        for k, (b, bb) in enumerate(rs):
            res["moving_hits_moving"] += hit(b, bb, rs[k + 1:])
    if verbose:
        print("[traffic-audit]", json.dumps(res))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    r = audit(ap.parse_args().out)
    return 1 if any(v for k, v in r.items() if k != "moving_samples") else 0


if __name__ == "__main__":
    sys.exit(main())
