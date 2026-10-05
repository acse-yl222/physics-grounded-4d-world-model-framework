"""img2city/scene/traffic_sim.py -- deterministic traffic ANIMATION on the directed road graph.

The 07-28 meeting asked for road semantics "so vehicles can then be simulated
on it" -- road_graph.py built the directed arcs, one-ways and turn restrictions;
this module finally drives on them. Zero-LLM, fully deterministic (seeded by
vehicle index), cached to traffic_anim.json; the assembly keyframes the moving
cars in Blender so the .blend plays as an animation.

Mechanics per moving vehicle:
  * runs along its arc's polyline at the arc's speed (maxspeed capped at
    30 mph, urban), offset to the KEEP-LEFT lane centre (w/4 left of the
    centreline in travel direction -- the same rule the arrow marks use);
  * at the end node, picks the next arc among the node's outgoing arcs,
    excluding the immediate U-turn (unless dead end) and any turn banned by a
    `no_*` restriction (or forced by an `only_*` one) via the from/to way ids;
    the pick cycles deterministically by (vehicle, junction) hash;
  * PARKED cars stay parked: a detected car whose lateral offset from its arc
    centreline is beyond ~w/4 + 1 m sits at the kerb, not in the running lane.

  python -m img2city.scene.traffic_sim --out data/city_cw --seconds 60
"""
from __future__ import annotations
import argparse
import json
import math
import os

STEP = 0.5          # s between samples
MPH = 0.44704


def _load(out):
    t = json.load(open(os.path.join(out, "traffic.json")))
    v = json.load(open(os.path.join(out, "vehicles.json")))
    arcs = {a["id"]: a for a in t["arcs"]}
    out_arcs = {}
    for a in t["arcs"]:
        out_arcs.setdefault(a["a"], []).append(a["id"])
    # restrictions by (from_way, via node): banned/forced to_ways
    ban, only = {}, {}
    for r in t["restrictions"]:
        if not r.get("in_graph") or r.get("via_type") != "node":
            continue
        key = (r["from_way"], r["via"])
        if r["type"].startswith("no_"):
            ban.setdefault(key, set()).add(r["to_way"])
        elif r["type"].startswith("only_"):
            only.setdefault(key, set()).add(r["to_way"])
    return arcs, out_arcs, ban, only, v


def _arc_geom(a):
    pts = a["pts"]
    segs, L = [], 0.0
    for i in range(len(pts) - 1):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append((pts[i], pts[i + 1], d))
        L += d
    return segs, L


def _pos_at(segs, s):
    """Point + heading at distance s along the polyline, keep-left offset."""
    run = 0.0
    for p1, p2, d in segs:
        if run + d >= s or (p1, p2, d) == segs[-1]:
            t = 0.0 if d == 0 else min(1.0, (s - run) / d)
            ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            x = p1[0] + (p2[0] - p1[0]) * t
            y = p1[1] + (p2[1] - p1[1]) * t
            return x, y, ang
        run += d
    p1, p2, _ = segs[-1]
    return p2[0], p2[1], math.atan2(p2[1] - p1[1], p2[0] - p1[0])


def lane_offsets(arc, sgn=1.0):
    """Lane centre offsets along the LEFT normal, per lane index -- the SAME
    rule road_graph.traffic_marks paints the arrows with: a two-way arc runs
    w/4 to the driving side; a one-way carriageway centres its rows on the
    lanes (a single-lane one-way runs on the centreline)."""
    w = arc["width"]
    if arc["oneway"]:
        return [((k + 0.5) / arc["lanes"] - 0.5) * w * 0.8
                for k in range(arc["lanes"])]
    return [sgn * w / 4.0]


MIN_OFF = 1.2       # m closest a squeezed two-way lane may run to the centreline
MIN_GAP = 7.0       # m centre-to-centre minimum between two 4.4 m cars
SLOW_GAP = 16.0     # start easing off inside this headway
JUNC_ZONE = 8.0     # m before a node that counts as "in the junction"


def simulate(out, seconds=60.0, max_moving=None):
    """Global time-stepped sim (08-11 v2, lanes + clearance 08-19): vehicles
    interact deterministically -- CAR-FOLLOWING per (arc, lane) incl. the car
    just past the next junction, length-aware (buses); JUNCTION RESERVATION
    (one vehicle in a node's zone at a time); LANE CLEARANCE (every lane is
    swept against the built outlines and the parked bodies; an obstructed lane
    is squeezed towards the centreline on two-way arcs or dropped on one-way
    carriageways; an arc with no clear lane is blocked and never entered).
    Opposing flows never meet head-on: each direction has its own lane."""
    arcs, out_arcs, ban, only, vehicles = _load(out)
    geoms = {aid: _arc_geom(a) for aid, a in arcs.items()}
    from img2city.scene.road_graph import drive_side
    sgn = 1.0 if drive_side(out) == "left" else -1.0
    from img2city.scene.vehicles import (BODY, LANE_CLEAR, _arc_frame, _rect, _bbox,
                                _bb_touch, _poly_hit)
    from img2city.scene.shops import built_outlines

    # ---- static obstacles: built outlines (OBB / polygon actually raised)
    bd = json.load(open(os.path.join(out, "buildings.json")))
    outl = built_outlines(out, bd["buildings"])
    polys = [p for p, _m in outl.values()] + \
            [[tuple(q) for q in b["pts"]] for b in bd["buildings"]
             if b["id"] not in outl]
    obst = [(p, _bbox(p)) for p in polys]

    # ---- candidate movers (photo lateral offset inside the carriageway's
    # running lanes) with their initial s and nearest lane index
    def _snap(v, a):
        segs, L = geoms[a["id"]]
        best, run = None, 0.0
        for p1, p2, d in segs:
            if d < 1e-6:
                continue
            t = max(0.0, min(1.0, ((v["x"] - p1[0]) * (p2[0] - p1[0])
                                   + (v["y"] - p1[1]) * (p2[1] - p1[1])) / (d * d)))
            px, py = p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t
            dist = math.hypot(v["x"] - px, v["y"] - py)
            if best is None or dist < best[0]:
                best = (dist, run + t * d)
            run += d
        return best[1]

    cand = {}                      # vi -> (arc, s, lane)
    for vi, v in enumerate(vehicles):
        aid = v.get("arc")
        if aid not in arcs:
            continue
        a = arcs[aid]
        lat, _n = _arc_frame(v, a)
        if abs(lat) > a["width"] / 4.0 + 1.0:
            continue                                      # kerbside: parked
        offs = lane_offsets(a, sgn)
        lane = min(range(len(offs)), key=lambda k: abs(offs[k] - lat))
        cand[vi] = (aid, _snap(v, a), lane)
    if max_moving:
        for vi in sorted(cand)[max_moving:]:
            del cand[vi]

    # ---- lane clearance: sweep a car body along every lane; buses (wider,
    # longer) additionally get their own clear-lane set -- a mews that fits a
    # car does not fit a bus, and a bus never routes onto such an arc
    lane_off = {}                  # (arc, lane) -> offset actually driven
    bus_ok = set()                 # (arc, lane) a bus body clears too
    no_go = set()

    def _sweep_ok(aid, off, obstacles, kind="car"):
        SL, SW = BODY[kind]
        segs, L = geoms[aid]
        s = 0.0
        while s <= L:
            x, y, ang = _pos_at(segs, s)
            nx, ny = -math.sin(ang), math.cos(ang)
            r = _rect(x + nx * off, y + ny * off, ang, SL, SW, pad=LANE_CLEAR / 2)
            rb = _bbox(r)
            if any(_bb_touch(rb, ob) and _poly_hit(r, p) for p, ob in obstacles):
                return False
            s += 1.0
        return True

    def _lane_room(park_set):
        pbod = [(r, _bbox(r)) for r in (
            _rect(vehicles[i]["x"], vehicles[i]["y"], vehicles[i]["ang"],
                  *BODY.get(vehicles[i].get("kind", "car"), BODY["car"]))
            for i in park_set)]
        obstacles = obst + pbod
        lane_off.clear(); no_go.clear(); bus_ok.clear()
        for aid, a in arcs.items():
            any_ok = False
            # single-track: a two-way carriageway too narrow for two bodies
            # side by side (4 m service roads / mews) carries one direction
            # of movement at a time -- the reverse arc is blocked
            if (not a["oneway"] and a["width"] < 2 * (BODY["car"][1] + LANE_CLEAR)
                    and aid.endswith(":r")):
                no_go.add(aid)
                continue
            for k, nominal in enumerate(lane_offsets(a, sgn)):
                off = nominal
                if a["oneway"] and a["lanes"] > 1:
                    ok = _sweep_ok(aid, off, obstacles)      # fixed painted lanes
                else:                                        # squeeze to centre
                    # ...but never closer than MIN_OFF: the opposite direction
                    # runs its own squeezed lane, and two lanes hugging the
                    # centreline meet head-on
                    floor = min(MIN_OFF, abs(nominal))
                    step = 0.25 * (1 if off >= 0 else -1) if abs(off) > 1e-6 else 0.0
                    while abs(off) >= floor - 1e-9 and not _sweep_ok(aid, off, obstacles):
                        off -= step
                        if step == 0.0:
                            break
                    ok = abs(off) >= floor - 1e-9 and _sweep_ok(aid, off, obstacles)
                if ok:
                    any_ok = True
                    lane_off[(aid, k)] = off
                    if _sweep_ok(aid, off, obstacles, "bus"):
                        bus_ok.add((aid, k))
            if not any_ok:
                no_go.add(aid)

    park = {vi for vi in range(len(vehicles)) if vi not in cand}
    _lane_room(park)
    for _ in range(5):             # movers stranded on blocked arcs/lanes park
        stranded = {vi for vi, (aid, s, k) in cand.items()
                    if aid in no_go or (aid, k) not in lane_off or
                    (vehicles[vi].get("kind") == "bus" and (aid, k) not in bus_ok)}
        if not stranded:
            break
        for vi in stranded:
            del cand[vi]
        park |= stranded
        _lane_room(park)
    n_sq = sum(1 for (aid, k), off in lane_off.items()
               if abs(off - lane_offsets(arcs[aid], sgn)[k]) > 1e-6)
    n_dropped_lanes = sum(len(lane_offsets(a, sgn)) for a in arcs.values()) \
        - len(lane_off) - sum(len(lane_offsets(arcs[a], sgn)) for a in no_go)
    print(f"[traffic-sim] lanes: {n_sq} squeezed, {n_dropped_lanes} obstructed "
          f"on multi-lane carriageways, {len(no_go)} arcs blocked for cars, "
          f"{len(lane_off) - len(bus_ok)} lanes too tight for a bus")

    movers = []
    for vi in sorted(cand):
        aid, s0, k = cand[vi]
        movers.append({"vi": vi, "arc": aid, "s": s0, "lane": k,
                       "vmax": min(30, arcs[aid].get("maxspeed_mph") or 20) * MPH,
                       "kind": vehicles[vi].get("kind", "car"),
                       "color": vehicles[vi].get("color"), "samples": [],
                       "arcs": []})
    def _blen(mv):
        return BODY.get(mv["kind"] if mv else "car", BODY["car"])[0]

    def _need(m1, m2):
        return MIN_GAP + (_blen(m1) + _blen(m2)) / 2 - _blen(None)

    # spawn headway: two photo positions that land on the same lane closer
    # than a body apart (side-by-side in the photo, or a queue) start as a
    # queue -- the rear one is set back to the following distance (clamped at
    # the arc start; a same-spot duplicate that cannot be set back parks)
    by_lane = {}
    for mv in movers:
        by_lane.setdefault((mv["arc"], mv["lane"]), []).append(mv)
    keep = []
    for group in by_lane.values():
        group.sort(key=lambda m: -m["s"])
        front = None
        for mv in group:
            if front is not None and front["s"] - mv["s"] < _need(front, mv):
                mv["s"] = front["s"] - _need(front, mv)
                if mv["s"] < 0.0:
                    if front["s"] - 0.0 < (_blen(front) + _blen(mv)) / 2 + 0.3:
                        park.add(mv["vi"])
                        continue
                    mv["s"] = 0.0
            keep.append(mv)
            front = mv
    movers = keep
    parked = len(vehicles) - len(movers)

    def _lane_on(aid, k, kind="car"):
        """Lane index to use on arc `aid` coming from lane k: same index if it
        exists and is clear, else the nearest clear lane (None = none)."""
        ks = [j for j in range(len(lane_offsets(arcs[aid], sgn)))
              if (aid, j) in lane_off and (kind != "bus" or (aid, j) in bus_ok)]
        if not ks:
            return None
        return min(ks, key=lambda j: abs(j - k))

    def _next_arc(mv, a):
        """Deterministic successor (same rule as v1): no U-turn unless dead
        end, turn restrictions honoured, blocked arcs never entered."""
        node = a["b"]
        outs = [o for o in out_arcs.get(node, []) if o != mv["arc"]
                and o not in no_go and _lane_on(o, mv["lane"], mv["kind"]) is not None]
        rev = [o for o in outs if arcs[o]["b"] == a["a"]
               and arcs[o]["way"] == a["way"]]
        fwd = [o for o in outs if o not in rev]
        key = (a["way"], node)
        if key in only:
            forced = [o for o in fwd if arcs[o]["way"] in only[key]]
            fwd = forced or fwd
        elif key in ban:
            fwd = [o for o in fwd if arcs[o]["way"] not in ban[key]] or fwd
        pool = fwd or rev
        if not pool:
            return None
        return pool[(mv["vi"] * 7 + hash(node)) % len(pool)]

    # junction zone per node: the stop line must sit clear of the crossing
    # carriageway (JUNC_ZONE was a flat 8 m from the node centre -- on a 10 m
    # primary a car holding there still stood in the cross traffic's lane)
    node_w = {}
    for a in arcs.values():
        for n in (a["a"], a["b"]):
            node_w[n] = max(node_w.get(n, 0.0), a["width"])
    zone = {n: max(JUNC_ZONE, w / 2 + BODY["car"][0] / 2 + 2.0)
            for n, w in node_w.items()}

    # a mover photographed inside a junction zone (rem < zone) would hold
    # there forever once another car claims the node -- standing in the cross
    # traffic's lane. Spawn it at the stop line instead (clamped to the arc).
    for mv in movers:
        segs, L = geoms[mv["arc"]]
        jz = zone[arcs[mv["arc"]]["b"]]
        if L - mv["s"] < jz:
            mv["s"] = max(0.0, L - jz)

    # ---- global clock
    t_now = 0.0
    while t_now <= seconds:
        occ = {}
        for mv in movers:
            occ.setdefault((mv["arc"], mv["lane"]), []).append(mv)
        # sample current poses
        for mv in movers:
            segs, L = geoms[mv["arc"]]
            x, y, ang = _pos_at(segs, mv["s"])
            off = lane_off[(mv["arc"], mv["lane"])]
            x, y = x - math.sin(ang) * off, y + math.cos(ang) * off
            mv["samples"].append([round(t_now, 2), round(x, 2), round(y, 2),
                                  round(ang, 4)])
            mv["arcs"].append(mv["arc"])
        # junction reservations: nearest claimant per node this step; a car
        # that has just crossed the node (s < JUNC_ZONE on the next arc) is
        # still inside the junction and keeps the claim (08-19: crossing
        # traffic used to enter on top of it)
        claims = {}
        for mv in movers:
            a = arcs[mv["arc"]]
            _segs, L = geoms[mv["arc"]]
            rem = L - mv["s"]
            if rem < zone[a["b"]]:
                node = a["b"]
                if node not in claims or rem < claims[node][0]:
                    claims[node] = (rem, id(mv))
            if mv["s"] < zone[a["a"]]:
                node = a["a"]
                if node not in claims or claims[node][0] >= 0:
                    claims[node] = (-1.0, id(mv))
        # advance
        for mv in movers:
            a = arcs[mv["arc"]]
            segs, L = geoms[mv["arc"]]
            ds = mv["vmax"] * STEP
            # car-following on this lane, plus the car just past the node on
            # the lane we will take (a queue across a junction)
            nxt = _next_arc(mv, a)
            ahead = [(o["s"] - mv["s"], o) for o in occ.get((mv["arc"], mv["lane"]), [])
                     if o is not mv and o["s"] > mv["s"] + 1e-6]
            if nxt is not None:
                nk = _lane_on(nxt, mv["lane"], mv["kind"])
                if nk is not None:
                    ahead += [(L - mv["s"] + o["s"], o) for o in occ.get((nxt, nk), [])
                              if o["s"] < SLOW_GAP]
            if ahead:
                gap, o = min(ahead, key=lambda c: c[0])
                need = _need(mv, o)
                if gap < need:
                    ds = 0.0
                elif gap - ds < need:
                    ds = max(0.0, gap - need)
                elif gap < SLOW_GAP:
                    ds *= 0.5
            # junction reservation: hold at the stop line unless we own the node
            rem = L - mv["s"]
            jz = zone[a["b"]]
            nodes = [a["b"]]
            if nxt is not None:
                _s2, L2 = geoms[nxt]
                b2 = arcs[nxt]["b"]
                if L2 < zone[b2]:          # stub = part of the next junction
                    jz = max(jz, zone[b2] - L2)
                    nodes.append(b2)
            if rem - ds < jz:
                if any(claims.get(n, (None, id(mv)))[1] != id(mv) for n in nodes):
                    ds = min(ds, max(0.0, rem - jz))
            mv["s"] += ds
            # arc hand-over
            while mv["s"] > L:
                pick = _next_arc(mv, a)
                nk = _lane_on(pick, mv["lane"], mv["kind"]) if pick is not None else None
                if pick is None or nk is None:
                    mv["s"] = L                # dead end / all exits blocked: sit
                    break
                enter_s = mv["s"] - L
                # a stub shorter than the next junction's zone is PART of that
                # junction: do not enter it unless that node is free too (else
                # we would hold on the stub, standing in the cross traffic)
                _s2, L2 = geoms[pick]
                b2 = arcs[pick]["b"]
                if L2 < zone[b2] and claims.get(b2, (None, id(mv)))[1] != id(mv):
                    mv["s"] = L
                    break
                # never enter on top of (or just behind) a car on the target lane
                if any(o["arc"] == pick and o["lane"] == nk and
                       abs(o["s"] - enter_s) < _need(o, mv)
                       for o in movers if o is not mv):
                    mv["s"] = L
                    break
                mv["s"], mv["arc"], mv["lane"] = enter_s, pick, nk
                a = arcs[pick]
                segs, L = geoms[pick]
                mv["vmax"] = min(30, a.get("maxspeed_mph") or 20) * MPH
        t_now += STEP

    routes = [{"i": mv["vi"], "kind": mv["kind"], "color": mv["color"],
               "samples": mv["samples"], "arcs": mv["arcs"]} for mv in movers]
    data = {"step": STEP, "seconds": seconds, "routes": routes}
    with open(os.path.join(out, "traffic_anim.json"), "w") as f:
        json.dump(data, f)
    print(f"[traffic-sim] {len(movers)} moving, {parked} parked "
          f"({seconds:.0f}s, lanes + car-following + junction reservation)")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--max-moving", type=int, default=0)
    a = ap.parse_args()
    simulate(os.path.abspath(a.out), a.seconds, a.max_moving or None)


if __name__ == "__main__":
    main()
