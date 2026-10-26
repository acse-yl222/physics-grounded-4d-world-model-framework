"""Tracks, stations, scheduled train patterns/trips and status from the scene inputs.

Inputs: ``project/<scene>/input/underground/osm/osm_rail.json.gz`` (``osm.py``) and
``project/<scene>/input/underground/gtfs/`` (``gtfs.py``). Everything is computed in
scene ENU metres (``tfl.Enu``); see ``README.md`` for the rules and assumptions.
"""

from __future__ import annotations

import bisect
import gzip
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

from traffic.corridor_sumo.gtfs_bus import fmt_time, parse_time

from . import geometry as geo
from .config import COLOUR_SOURCE, LINES, line_id, log

DAY_START_S = 4 * 3600  # first/last train: calls from 04:00 (later than 24:00 allowed)
ENTRANCES = {"subway_entrance", "train_station_entrance"}
TRAIN_PROVENANCE = (
    "scheduled positions interpolated between timetabled station calls; not real-time"
)


def r2(v: float) -> float:
    return round(float(v), 2)


def xyz(points) -> list:
    return [[r2(p[0]), r2(p[1]), r2(p[2])] for p in points]


def inside(p, half: float) -> bool:
    return abs(p[0]) <= half and abs(p[1]) <= half


def norm_name(name: str | None) -> str:
    text = (name or "").lower().replace("&", "and").replace("'", "").replace("’", "")
    text = re.sub(
        r"\b(underground|tube|rail|railway|station|london|dlr|elizabeth line)\b", "", text
    )
    text = re.sub(r"\(.*?\)", "", text) if "olympia" not in text else text
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


# ---------------------------------------------------------------- OSM network


class Network:
    """Active rail ways of the buffered area as a graph with assumed vertical profile."""

    def __init__(self, osm: dict, enu, half: float, buffer_m: float, cfg: dict):
        self.enu, self.half, self.cfg = enu, half, cfg
        dcfg = cfg["depth"]
        self.nodes = osm["nodes"]
        reach = half + buffer_m
        self.way_lines: dict[int, set] = defaultdict(set)
        self.route_lines = {}
        for r in osm["routes"]:
            lid = geo.relation_line(r["tags"])
            if lid is None:
                continue
            self.route_lines[r["id"]] = lid
            for m in r["members"]:
                role = m.get("role") or ""
                if m["type"] == "way" and not role.startswith("platform"):
                    self.way_lines[int(m["ref"])].add(lid)
        self.graph = geo.Graph()
        self.targets: dict[int, float] = {}
        self.kind: dict[int, str] = {}
        self.source: dict[int, str] = {}
        self.tags: dict[int, dict] = {}
        self.node_seq: dict[int, list] = {}
        step = cfg.get("graph_step_m", 20.0)
        kept = []
        for wid_s, w in osm["ways"].items():
            tags = w["tags"]
            if tags.get("railway") not in geo.ACTIVE_RAILWAYS or tags.get("area") == "yes":
                continue
            refs = [n for n in w["nds"] if str(n) in self.nodes]
            if len(refs) < 2:
                continue
            coords = [self.xy(n) for n in refs]
            if not any(abs(x) <= reach and abs(y) <= reach for x, y in coords):
                continue
            wid = int(wid_s)
            kept.append((wid, tags, refs, coords, sorted(self.way_lines.get(wid, ()))))
        self.ref_layers = geo.reference_layers(
            [(t, ls, geo.polyline_length(c)) for _, t, _, c, ls in kept], dcfg
        )
        for wid, tags, refs, coords, lines in kept:
            self.graph.add_way(wid, coords, refs, step, lines)
            self.targets[wid], self.kind[wid], self.source[wid] = geo.depth_target(
                tags, lines, dcfg, self.ref_layers
            )
            self.tags[wid] = tags
            self.node_seq[wid] = refs
        self.z = geo.vertex_z(self.graph, self.targets, dcfg)
        self.grid = geo.Grid(self.graph.xy, 100.0)
        log(f"  track graph: {len(self.graph.ways)} ways, {len(self.graph.xy)} vertices")

    def xy(self, node_id) -> tuple[float, float]:
        lat, lon, _ = self.nodes[str(node_id)]
        return self.enu(float(lon), float(lat))

    def vxyz(self, v) -> tuple[float, float, float]:
        x, y = self.graph.xy[v]
        return x, y, self.z.get(v, 0.0)

    def line_ok(self, lid):
        if not any(lid in s for s in self.graph.way_lines.values()):
            return None
        return lambda w: lid in self.graph.way_lines.get(w, ())

    # ------------------------------------------------------------ tracks

    def chains(self) -> list[list[int]]:
        """Ways merged at degree-2 endpoints with equal lines/tunnel/kind/railway."""

        def sig(w):
            t = self.tags[w]
            return (
                tuple(sorted(self.graph.way_lines[w])),
                self.kind[w],
                round(self.targets[w], 2),
                t.get("railway"),
                t.get("service"),
            )

        ends = defaultdict(list)
        degree = Counter()
        for w, refs in self.node_seq.items():
            for n in refs:
                degree[n] += 1
            degree[refs[0]] += 0
            ends[refs[0]].append(w)
            ends[refs[-1]].append(w)
        for w, refs in self.node_seq.items():
            if refs[0] == refs[-1]:
                degree[refs[0]] -= 1  # closed way counts once at its join
        used, out = set(), []
        for w in sorted(self.node_seq):
            if w in used:
                continue
            used.add(w)
            chain = [(w, False)]
            for forward in (True, False):
                while True:
                    tw, rev = chain[-1] if forward else chain[0]
                    refs = self.node_seq[tw]
                    if forward:
                        end = refs[0] if rev else refs[-1]
                    else:
                        end = refs[-1] if rev else refs[0]
                    nxt = [o for o in ends[end] if o != tw and o not in used]
                    if degree[end] != 2 or len(nxt) != 1 or sig(nxt[0]) != sig(w):
                        break
                    o = nxt[0]
                    orefs = self.node_seq[o]
                    if orefs[0] == orefs[-1]:
                        break
                    used.add(o)
                    if forward:
                        chain.append((o, orefs[-1] == end))
                    else:
                        chain.insert(0, (o, orefs[0] == end))
            out.append(chain)
        return out

    def chain_points(self, chain) -> list:
        pts = []
        for w, rev in chain:
            verts = self.graph.ways[w][::-1] if rev else self.graph.ways[w]
            seg = [self.vxyz(v) for v in verts]
            pts += seg if not pts else seg[1:]
        return pts

    def tracks(self) -> list[dict]:
        tol = self.cfg.get("simplify_m", 1.0)
        out = []
        for chain in self.chains():
            pts = self.chain_points(chain)
            w0 = chain[0][0]
            for k, piece in enumerate(geo.clip_polyline(pts, self.half, min_len=1.0)):
                shape = geo.simplify3d(piece, tol)
                ways = [w for w, _ in chain]
                tags = self.tags[w0]
                out.append(
                    {
                        "id": f"w{w0}" + (f"_{k}" if k else ""),
                        "lines": sorted(self.graph.way_lines[w0]),
                        "osm_way_ids": ways,
                        "railway": tags.get("railway"),
                        "service": tags.get("service"),
                        "tunnel": self.kind[w0] == "tunnel",
                        "bridge": self.kind[w0] == "bridge",
                        "layer": geo.parse_layer(tags.get("layer")),
                        "target_z_m": r2(self.targets[w0]),
                        "depth_source": self.source[w0],
                        "length_m": round(geo.polyline_length(shape), 1),
                        "shape": xyz(shape),
                    }
                )
        return out

    def crossing_conflicts(self, tracks: list[dict], clearance: float = 3.0) -> dict:
        """Crossings of tunnel tracks (2D) whose assumed levels differ by < clearance."""
        tun = [t for t in tracks if t["tunnel"]]
        segs = []
        for i, t in enumerate(tun):
            for a, b in pairwise(t["shape"]):
                segs.append((i, a, b))
        cells = defaultdict(list)
        for k, (_, a, b) in enumerate(segs):
            for cx in range(int(min(a[0], b[0]) // 200), int(max(a[0], b[0]) // 200) + 1):
                for cy in range(int(min(a[1], b[1]) // 200), int(max(a[1], b[1]) // 200) + 1):
                    cells[(cx, cy)].append(k)
        seen, crossings, conflicts = set(), 0, []
        for ks in cells.values():
            for x in range(len(ks)):
                for y in range(x + 1, len(ks)):
                    i, a, b = segs[ks[x]]
                    j, c, d = segs[ks[y]]
                    if i == j or (ks[x], ks[y]) in seen:
                        continue
                    seen.add((ks[x], ks[y]))
                    hit = _intersect(a, b, c, d)
                    if hit is None:
                        continue
                    ta, tc = hit
                    za = a[2] + (b[2] - a[2]) * ta
                    zc = c[2] + (d[2] - c[2]) * tc
                    if set(tun[i]["lines"]) & set(tun[j]["lines"]):
                        continue  # junction / shared line, not a crossing
                    if za > -clearance or zc > -clearance:
                        continue  # at/near a portal: not a buried crossing
                    crossings += 1
                    if abs(za - zc) < clearance:
                        conflicts.append(
                            {
                                "tracks": [tun[i]["id"], tun[j]["id"]],
                                "lines": [tun[i]["lines"], tun[j]["lines"]],
                                "z": [r2(za), r2(zc)],
                                "layers": [tun[i]["layer"], tun[j]["layer"]],
                            }
                        )
        return {
            "tunnel_crossings": crossings,
            "conflicts": conflicts[:50],
            "n_conflicts": len(conflicts),
        }


def _intersect(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    q = (c[0] - a[0], c[1] - a[1])
    t = (q[0] * s[1] - q[1] * s[0]) / den
    u = (q[0] * r[1] - q[1] * r[0]) / den
    if 0 < t < 1 and 0 < u < 1:
        return t, u
    return None


# ---------------------------------------------------------------- GTFS


class Timetable:
    """Underground trips of the service day with parent-station sequences."""

    def __init__(self, sub: dict, enu):
        self.enu = enu
        self.index = sub["index"]
        self.stops = sub["stops"]
        for s in self.stops.values():
            s["x"], s["y"] = enu(float(s["stop_lon"]), float(s["stop_lat"]))
        self.derived_parents = self._derive_parents()
        self.routes = sub["routes"]
        self.trips = []
        for tid, meta in sub["trips"].items():
            rows = sub["times"].get(tid)
            if not rows:
                continue
            lid = line_id(self.routes[meta["route_id"]]["route_short_name"])
            calls = []
            for r in rows:
                arr = parse_time(r["arrival_time"] or r["departure_time"])
                dep = parse_time(r["departure_time"] or r["arrival_time"])
                calls.append(
                    {
                        "stop": r["stop_id"],
                        "station": self.parent(r["stop_id"]),
                        "arr": arr,
                        "dep": dep,
                    }
                )
            self.trips.append(
                {
                    "id": tid,
                    "line": lid,
                    "route_id": meta["route_id"],
                    "direction": meta.get("direction_id") or "0",
                    "calls": calls,
                }
            )

    def _derive_parents(self) -> list[str]:
        """Platform stops without ``parent_station`` get the NaPTAN station code
        (``9400ZZLUxxxN`` -> ``940GZZLUxxx``); a parent missing from the feed is added at
        the mean of its platforms (recorded as derived)."""
        derived, groups = [], defaultdict(list)
        for sid, s in self.stops.items():
            if s.get("parent_station") or (s.get("location_type") or "0") != "0":
                continue
            m = re.fullmatch(r"9400(ZZ[A-Z]{2}[A-Z0-9]{3})\d*", sid)
            if m:
                groups["940G" + m.group(1)].append(sid)
        for pid, kids in groups.items():
            for k in kids:
                self.stops[k]["parent_station"] = pid
            if pid not in self.stops:
                rows = [self.stops[k] for k in kids]
                self.stops[pid] = {
                    "stop_id": pid,
                    "stop_name": rows[0]["stop_name"],
                    "x": statistics.fmean(r["x"] for r in rows),
                    "y": statistics.fmean(r["y"] for r in rows),
                    "location_type": "1",
                    "derived": True,
                }
                derived.append(pid)
        return sorted(derived)

    def parent(self, stop_id: str) -> str:
        s = self.stops.get(stop_id, {})
        return s.get("parent_station") or stop_id

    def station_name(self, sid: str) -> str:
        name = self.stops.get(sid, {}).get("stop_name", sid)
        return re.sub(r"\s*(-?Underground Station|Station|-Underground)$", "", name).strip()


# ---------------------------------------------------------------- stations


def osm_features(osm: dict, enu) -> list[dict]:
    out = []
    for nid, (lat, lon, tags) in osm["features"].items():
        x, y = enu(float(lon), float(lat))
        out.append({"osm_id": f"n{nid}", "id": int(nid), "x": x, "y": y, "tags": tags})
    return out


def platform_ways(osm: dict, net: Network) -> list[dict]:
    out = []
    for wid, w in osm["ways"].items():
        t = w["tags"]
        if not (t.get("railway") == "platform" or t.get("public_transport") == "platform"):
            continue
        if t.get("bus") == "yes" or t.get("highway") == "bus_stop":
            continue
        pts = [net.xy(n) for n in w["nds"] if str(n) in net.nodes]
        if len(pts) >= 2:
            out.append({"osm_id": f"w{wid}", "pts": pts, "tags": t})
    return out


def _track_segment(net: Network, p, lid, radius: float, half_len: float):
    """``half_len`` either side of the nearest point of line ``lid``'s track to ``p``."""
    ok = net.line_ok(lid)
    cand = geo.nearest_vertices(net.graph, p, radius, ok, grid=net.grid)
    if not cand:
        return None
    v = min(cand, key=cand.get)
    ways = [w for _, _, w in net.graph.adj[v] if ok is None or ok(w)]
    chain = net.chain_of.get(ways[0]) if ways else None
    pts = net.chain_points(chain) if chain else [net.vxyz(v)]
    if len(pts) < 2:
        return None
    s, d, _ = geo.project(pts, p)
    return geo.sub_polyline(pts, s - half_len, s + half_len), d


def build_stations(net: Network, tt: Timetable, osm: dict, cfg: dict) -> tuple[list, dict]:
    half = net.half
    radius = cfg.get("station_match_m", 250.0)
    plat_len = cfg.get("platform_length_m", 120.0)
    net.chain_of = {w: c for c in net.chains() for w, _ in c}
    # line -> station -> child platform stops used
    used = defaultdict(lambda: defaultdict(set))
    for trip in tt.trips:
        for c in trip["calls"]:
            used[c["station"]][trip["line"]].add(c["stop"])
    feats = osm_features(osm, net.enu)
    entrances = [f for f in feats if f["tags"].get("railway") in ENTRANCES]
    plats = platform_ways(osm, net)
    areas = osm.get("stop_areas", [])
    feat_by_id = {f["id"]: f for f in feats}
    stations, report = [], Counter()

    def make_platforms(sid, lid, p_station, child_pts):
        found = []
        for pl in plats:
            cx = sum(p[0] for p in pl["pts"]) / len(pl["pts"])
            cy = sum(p[1] for p in pl["pts"]) / len(pl["pts"])
            if geo.seg_len((cx, cy), p_station) > radius:
                continue
            seg = _track_segment(net, (cx, cy), lid, 25.0, 1e6)
            if seg is None:
                continue
            track = seg[0]
            ss = [geo.project(track, p)[0] for p in pl["pts"]]
            s0, s1 = min(ss), max(ss)
            if s1 - s0 < 20:
                continue
            found.append(
                {
                    "line": lid,
                    "shape": xyz(geo.simplify3d(geo.sub_polyline(track, s0, s1), 0.5)),
                    "source": f"osm_platform:{pl['osm_id']}",
                    "osm_id": pl["osm_id"],
                }
            )
        if found:
            report["platforms_osm"] += len(found)
            return found
        p = (
            sum(q[0] for q in child_pts) / len(child_pts),
            sum(q[1] for q in child_pts) / len(child_pts),
        )
        seg = _track_segment(net, p, lid, radius, plat_len / 2)
        if seg is None:
            report["platforms_missing_track"] += 1
            return []
        report["platforms_assumed"] += 1
        return [
            {
                "line": lid,
                "shape": xyz(geo.simplify3d(seg[0], 0.5)),
                "source": f"assumed_{plat_len:g}m_along_track",
            }
        ]

    names = {}
    for sid in sorted(used):
        s = tt.stops.get(sid)
        if s is None:
            continue
        p = (s["x"], s["y"])
        if not inside(p, half):
            continue
        platforms = []
        for lid in sorted(used[sid]):
            child_pts = [
                (tt.stops[c]["x"], tt.stops[c]["y"]) for c in used[sid][lid] if c in tt.stops
            ] or [p]
            platforms += make_platforms(sid, lid, p, child_pts)
        zs = [pl["shape"][len(pl["shape"]) // 2][2] for pl in platforms if pl["shape"]]
        names[sid] = norm_name(tt.station_name(sid))
        stations.append(
            {
                "id": sid,
                "name": tt.station_name(sid),
                "x": r2(p[0]),
                "y": r2(p[1]),
                "z": max(zs) if zs else 0.0,
                "z_note": "shallowest platform level (per-line levels in platforms)",
                "lines": sorted(used[sid]),
                "timetable": True,
                "source": "gtfs_bods",
                "platforms": platforms,
                "entrances": [],
            }
        )
    # Rail-only (no timetable) stations: OSM railway=station on Elizabeth/Overground
    rail_lines = {lid for lid in ("elizabeth", "overground")}
    stop_line = defaultdict(set)
    for r in osm["routes"]:
        lid = geo.relation_line(r["tags"])
        if lid in rail_lines:
            for m in r["members"]:
                if m["type"] == "node" and (m.get("role") or "").startswith("stop"):
                    stop_line[int(m["ref"])].add(lid)
    stop_pts = []
    for nid, lids in stop_line.items():
        f = feat_by_id.get(nid)
        if f is not None:
            stop_pts.append(((f["x"], f["y"]), lids))
        elif str(nid) in net.nodes:
            stop_pts.append((net.xy(nid), lids))
    for f in feats:
        t = f["tags"]
        if t.get("railway") not in ("station", "halt") or t.get("station") == "subway":
            continue
        if not inside((f["x"], f["y"]), half):
            continue
        lids = set()
        for q, ls in stop_pts:
            if geo.seg_len(q, (f["x"], f["y"])) < 300:
                lids |= ls
        text = " ".join(str(t.get(k, "")) for k in ("network", "line", "operator", "name")).lower()
        if "elizabeth" in text:
            lids.add("elizabeth")
        if "overground" in text:
            lids.add("overground")
        lids &= rail_lines
        if not lids:
            continue
        sid = t.get("naptan:AtcoCode") or f"osm:{f['osm_id']}"
        platforms = []
        for lid in sorted(lids):
            seg = _track_segment(net, (f["x"], f["y"]), lid, radius, plat_len / 2)
            if seg:
                platforms.append(
                    {
                        "line": lid,
                        "shape": xyz(geo.simplify3d(seg[0], 0.5)),
                        "source": f"assumed_{plat_len:g}m_along_track",
                    }
                )
        zs = [pl["shape"][len(pl["shape"]) // 2][2] for pl in platforms]
        names[sid] = norm_name(t.get("name"))
        stations.append(
            {
                "id": sid,
                "name": t.get("name"),
                "x": r2(f["x"]),
                "y": r2(f["y"]),
                "z": max(zs) if zs else 0.0,
                "z_note": "shallowest platform level (per-line levels in platforms)",
                "lines": sorted(lids),
                "timetable": False,
                "source": f"osm:{f['osm_id']}",
                "platforms": platforms,
                "entrances": [],
            }
        )
        report["rail_only_stations"] += 1
    # Entrances: stop_area membership (by station name), else nearest station <= 350 m.
    area_station = {}
    for a in areas:
        aname = norm_name(a["tags"].get("name"))
        for m in a["members"]:
            if m["type"] == "node":
                area_station.setdefault(int(m["ref"]), set()).add(aname)
    by_id = {s["id"]: s for s in stations}
    for e in entrances:
        if not inside((e["x"], e["y"]), half):
            continue
        cands = sorted(stations, key=lambda s: geo.seg_len((s["x"], s["y"]), (e["x"], e["y"])))
        chosen, how = None, None
        anames = area_station.get(e["id"], set())
        for s in cands[:6]:
            if names.get(s["id"]) and names[s["id"]] in anames:
                chosen, how = s, "stop_area"
                break
        if chosen is None and cands:
            d = geo.seg_len((cands[0]["x"], cands[0]["y"]), (e["x"], e["y"]))
            if d <= 350:
                chosen, how = cands[0], "nearest_350m"
        if chosen is None:
            report["entrances_unassigned"] += 1
            continue
        t = e["tags"]
        rec = {"x": r2(e["x"]), "y": r2(e["y"]), "z": 0.0, "osm_id": e["osm_id"], "assigned": how}
        if t.get("name") or t.get("ref"):
            rec["name"] = t.get("name") or t.get("ref")
        by_id[chosen["id"]]["entrances"].append(rec)
        report[f"entrances_{how}"] += 1
    report["osm_platform_ways"] = len(plats)
    report["osm_entrance_nodes_in_bbox"] = len(entrances)
    return stations, dict(report)


# ---------------------------------------------------------------- patterns


class PathSampler:
    def __init__(self, pts: list):
        self.pts = pts
        self.cum = [0.0]
        for a, b in pairwise(pts):
            self.cum.append(self.cum[-1] + geo.seg_len(a, b))
        self.length = self.cum[-1]

    def at(self, s: float):
        if s <= 0:
            return self.pts[0]
        if s >= self.length:
            return self.pts[-1]
        i = bisect.bisect_right(self.cum, s) - 1
        d = self.cum[i + 1] - self.cum[i]
        t = 0.0 if d == 0 else (s - self.cum[i]) / d
        a, b = self.pts[i], self.pts[i + 1]
        return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def position(offsets: list, times: list, t: float) -> float | None:
    """Distance along the path at time ``t`` (linear between departure and arrival,
    stationary while dwelling), None outside the trip."""
    if t < times[0][0] or t > times[-1][1]:
        return None
    for i, (arr, dep) in enumerate(times):
        if arr <= t <= dep:
            return offsets[i]
        if i + 1 < len(times) and dep < t < times[i + 1][0]:
            span = times[i + 1][0] - dep
            return offsets[i] + (offsets[i + 1] - offsets[i]) * (t - dep) / span
    return None


def time_at(offsets: list, times: list, s: float) -> float | None:
    """Inverse of ``position``: first time the train reaches distance ``s``."""
    if s < offsets[0] or s > offsets[-1]:
        return None
    for i in range(len(offsets) - 1):
        a, b = offsets[i], offsets[i + 1]
        if a <= s <= b:
            if b - a < 1e-9:
                return times[i][1]
            dep, arr = times[i][1], times[i + 1][0]
            return dep + (arr - dep) * (s - a) / (b - a)
    return times[-1][0]


def domain_runs(calls: list, half: float, stops: dict, max_outside: int = 1) -> list:
    """Spans ``(i0, i1)`` of calls inside the domain plus one outside neighbour each side.

    A trip that leaves the domain for more than ``max_outside`` consecutive outside
    calls (the Circle line loop) is split into separate runs.
    """

    def ins(c):
        s = stops.get(c["station"])
        return s is not None and inside((s["x"], s["y"]), half)

    idx = [i for i, c in enumerate(calls) if ins(c)]
    if not idx:
        return []
    runs, start = [], idx[0]
    for a, b in pairwise(idx):
        if b - a - 1 > max_outside:
            runs.append((start, a))
            start = b
    runs.append((start, idx[-1]))
    return [(max(0, a - 1), min(len(calls) - 1, b + 1)) for a, b in runs]


def domain_span(calls: list, half: float, stops: dict) -> tuple[int, int] | None:
    """Indices [first-1, last+1] around the calls whose station lies inside the domain."""
    runs = domain_runs(calls, half, stops, max_outside=len(calls))
    return runs[0] if runs else None


def build_patterns(net: Network, tt: Timetable, cfg: dict) -> tuple[dict, dict]:
    """Stop patterns (line, direction, extended station sequence) map-matched once."""
    half = net.half
    radius = cfg.get("station_match_m", 250.0)
    tol = cfg.get("simplify_m", 1.0)
    groups = defaultdict(list)
    for trip in tt.trips:
        runs = domain_runs(trip["calls"], half, tt.stops)
        for k, (i0, i1) in enumerate(runs):
            calls = trip["calls"][i0 : i1 + 1]
            key = (trip["line"], trip["direction"], tuple(c["station"] for c in calls))
            seg = trip["id"] if len(runs) == 1 else f"{trip['id']}#{k + 1}"
            groups[key].append((trip, calls, seg))
    patterns, assign, pair_cache = {}, {}, {}
    for n, key in enumerate(sorted(groups, key=lambda k: (k[0], k[1], -len(groups[k]), k[2]))):
        lid, direction, stations = key
        first_calls = groups[key][0][1]
        pts = [
            (tt.stops[c["stop"]]["x"], tt.stops[c["stop"]]["y"])
            if c["stop"] in tt.stops
            else (tt.stops[c["station"]]["x"], tt.stops[c["station"]]["y"])
            for c in first_calls
        ]
        allowed = [("line", net.line_ok(lid)), ("any_rail", None)]
        m = match_with_fallback(net, pts, radius, allowed, pair_cache, lid)
        full = [(x, y, net.z.get(v, None) if v is not None else None) for x, y, v in m["path"]]
        full = fill_z(full)
        # simplify between station vertices so station offsets stay exact
        idx = m["station_index"]
        simp, sidx = [full[0]], [0]
        for a, b in pairwise(idx):
            part = geo.simplify3d(full[a : b + 1], tol) if b > a else [full[a]]
            simp += part[1:]
            sidx.append(len(simp) - 1)
        sampler = PathSampler(simp)
        offsets = [sampler.cum[i] for i in sidx]
        s_in, s_out = inside_range(simp, half)
        if s_in is None:
            continue
        path = geo.sub_polyline(simp, s_in, s_out)
        straight = sum(geo.seg_len(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        pid = f"{lid}_{direction}_{n:03d}"
        patterns[pid] = {
            "id": pid,
            "line": lid,
            "direction": direction,
            "towards": tt.station_name(stations[-1]),
            "stations": list(stations),
            "stations_inside": [
                inside((tt.stops[s]["x"], tt.stops[s]["y"]), half) for s in stations
            ],
            "path": xyz(geo.simplify3d(path, tol)),
            "station_offsets_m": [round(o - s_in, 1) for o in offsets],
            "inside_length_m": round(s_out - s_in, 1),
            "match": {
                "path_over_straight": round(sampler.length / straight, 3) if straight else None,
                "pairs": m["pairs"],
                "methods": dict(Counter(p["method"] for p in m["pairs"])),
            },
            "_full_offsets": offsets,
            "_s_in": s_in,
            "_s_out": s_out,
            "_sampler": sampler,
            "trips": len(groups[key]),
        }
        for trip, calls, seg in groups[key]:
            assign.setdefault(trip["id"], []).append((pid, calls, seg))
    return patterns, assign


def match_with_fallback(
    net, pts: list, radius: float, allowed: list, cache: dict | None = None, key=None
) -> dict:
    """``geo.match_sequence`` pair by pair with a list of edge filters tried in order
    (``cache``: pair results keyed by ``(key, point a, point b)``)."""
    path, idx, pairs = [], [0], []
    cache = {} if cache is None else cache
    for k in range(1, len(pts)):
        ck = (key, tuple(pts[k - 1]), tuple(pts[k]))
        res = cache.get(ck)
        if res is None:
            for name, ok in allowed:
                r = geo.match_sequence(net.graph, [pts[k - 1], pts[k]], radius, ok, grid=net.grid)
                if r["pairs"][0]["method"] == "track":
                    res = r
                    r["pairs"][0]["method"] = "track" if name == "line" else f"track_{name}"
                    break
            if res is None:
                res = r
            cache[ck] = res
        seg = res["path"]
        if not path:
            path = list(seg)
        else:
            if geo.seg_len(path[-1], seg[0]) > 1e-6:
                path.append(seg[0])  # cross-over between parallel tracks at a station
            path += seg[1:]
        idx.append(len(path) - 1)
        pairs.append(res["pairs"][0])
    if not path:
        path = [(pts[0][0], pts[0][1], None)]
    return {"path": path, "station_index": idx, "pairs": pairs}


def fill_z(points: list) -> list:
    """Fill missing z (straight fallbacks) linearly between known neighbours (else 0)."""
    known = [i for i, p in enumerate(points) if p[2] is not None]
    out = []
    for i, p in enumerate(points):
        if p[2] is not None:
            out.append(p)
            continue
        lo = max((k for k in known if k < i), default=None)
        hi = min((k for k in known if k > i), default=None)
        if lo is None and hi is None:
            z = 0.0
        elif lo is None:
            z = points[hi][2]
        elif hi is None:
            z = points[lo][2]
        else:
            z = points[lo][2] + (points[hi][2] - points[lo][2]) * (i - lo) / (hi - lo)
        out.append((p[0], p[1], z))
    return out


def inside_range(points: list, half: float) -> tuple[float | None, float | None]:
    """Distances along the polyline of its first entry into / last exit from the domain."""
    pieces = []
    acc = 0.0
    for a, b in pairwise(points):
        c = geo._clip_segment(a, b, half)
        d = geo.seg_len(a, b)
        if c is not None:
            pieces.append((acc + c[0] * d, acc + c[1] * d))
        acc += d
    if not pieces:
        return None, None
    return pieces[0][0], pieces[-1][1]


# ---------------------------------------------------------------- periods


def period_trains(patterns: dict, assign: dict, tt: Timetable, window: tuple, half: float) -> dict:
    """Trips of the patterns inside the domain during ``window`` (seconds)."""
    t0, t1 = window
    trips = []
    for trip in tt.trips:
        for pid, calls, seg in assign.get(trip["id"], ()):
            pat = patterns[pid]
            times = [[c["arr"], c["dep"]] for c in calls]
            offs = pat["_full_offsets"]
            enter = time_at(offs, times, max(pat["_s_in"], offs[0]))
            leave = time_at(offs, times, min(pat["_s_out"], offs[-1]))
            if enter is None or leave is None or leave < t0 or enter > t1:
                continue
            rec = {
                "id": seg,
                "pattern": pid,
                "times": times,
                "domain_enter_s": round(enter, 1),
                "domain_exit_s": round(leave, 1),
            }
            if seg != trip["id"]:
                rec["gtfs_trip_id"] = trip["id"]
            trips.append(rec)
    trips.sort(key=lambda t: (t["domain_enter_s"], t["id"]))
    return {"trips": trips, "t0": t0, "t1": t1}


def sample_frames(patterns: dict, trips: list, t0: int, t1: int, dt: int, half: float) -> list:
    """Scheduled positions every ``dt`` s (protocol trajectory_frames)."""
    frames = []
    for t in range(t0, t1 + 1, dt):
        ids, pos = [], []
        for trip in trips:
            pat = patterns[trip["pattern"]]
            if not (trip["times"][0][0] <= t <= trip["times"][-1][1]):
                continue
            s = position(pat["_full_offsets"], trip["times"], t)
            if s is None or s < pat["_s_in"] or s > pat["_s_out"]:
                continue
            p = pat["_sampler"].at(s)
            if not inside(p, half + 1e-6):
                continue
            ids.append(trip["id"])
            pos.append([r2(p[0]), r2(p[1]), r2(p[2])])
        frames.append({"ids": ids, "positions": pos})
    return frames


# ---------------------------------------------------------------- status


def headway_stats(deps: list[float]) -> dict:
    deps = sorted(deps)
    gaps = [(b - a) / 60 for a, b in pairwise(deps)]
    return {
        "trains_per_hour": len(deps),
        "mean_headway_min": round(statistics.fmean(gaps), 2) if gaps else None,
        "headway_from_tph_min": round(60 / len(deps), 2) if deps else None,
        "max_gap_min": round(max(gaps), 2) if gaps else None,
    }


def status(
    patterns: dict, assign: dict, tt: Timetable, periods: dict, half: float, stations: list
) -> dict:
    inside_st = {s["id"] for s in stations if s["timetable"]}
    by_ld = defaultdict(list)
    for trip in tt.trips:
        if trip["id"] in assign:
            by_ld[(trip["line"], trip["direction"])].append(trip)
    lines_out = {}
    for (lid, direction), trips in sorted(by_ld.items()):
        towards = Counter(tt.station_name(t["calls"][-1]["station"]) for t in trips).most_common(3)
        per = {}
        for pid_name, (h0, h1) in periods.items():
            a, b = h0 * 3600, h1 * 3600
            deps = defaultdict(list)
            for trip in trips:
                for c in trip["calls"]:
                    if c["station"] in inside_st and a <= c["dep"] < b:
                        deps[c["station"]].append(c["dep"])
            if not deps:
                per[pid_name] = {"trains_per_hour": 0, "status": "no service"}
                continue
            busiest = max(deps, key=lambda s: (len(deps[s]), s))
            runs, speeds = [], []
            for trip in trips:
                for pid, calls, _seg in assign[trip["id"]]:
                    pat = patterns[pid]
                    offs = pat["_full_offsets"]
                    times = [[c["arr"], c["dep"]] for c in calls]
                    if offs[0] > pat["_s_in"] + 1 or offs[-1] < pat["_s_out"] - 1:
                        continue  # starts/ends inside the domain: not a full crossing
                    enter = time_at(offs, times, pat["_s_in"])
                    leave = time_at(offs, times, pat["_s_out"])
                    if enter is None or leave is None or not (a <= enter < b) or leave <= enter:
                        continue
                    runs.append(leave - enter)
                    speeds.append((pat["_s_out"] - pat["_s_in"]) / (leave - enter))
            per[pid_name] = {
                "busiest_station": busiest,
                "busiest_station_name": tt.station_name(busiest),
                **headway_stats(deps[busiest]),
                "domain_run_time_min": round(statistics.median(runs) / 60, 2) if runs else None,
                "domain_avg_speed_kmh": round(statistics.median(speeds) * 3.6, 1)
                if speeds
                else None,
                "full_crossings": len(runs),
                "status": "scheduled",
            }
        lines_out[f"{lid}|{direction}"] = {
            "line": lid,
            "direction_id": direction,
            "towards": [n for n, _ in towards],
            "periods": per,
        }
    calls_at = defaultdict(list)
    for trip in tt.trips:
        for c in trip["calls"]:
            calls_at[c["station"]].append((trip["line"], c["arr"], c["dep"]))
    st_out = {}
    for s in stations:
        if not s["timetable"]:
            st_out[s["id"]] = {"name": s["name"], "status": "no timetable (static)"}
            continue
        per_line = defaultdict(lambda: {"deps": [], "first": None, "last": None, "early": 0})
        for lid, arr, dep in calls_at.get(s["id"], ()):
            rec = per_line[lid]
            rec["deps"].append(dep)
            if dep < DAY_START_S:
                rec["early"] += 1  # 00:00-04:00 calls of the service day (not first trains)
                continue
            rec["first"] = dep if rec["first"] is None else min(rec["first"], dep)
            rec["last"] = arr if rec["last"] is None else max(rec["last"], arr)
        lines = {}
        for lid, rec in sorted(per_line.items()):
            lines[lid] = {
                "trains_per_hour": {
                    p: sum(1 for d in rec["deps"] if h0 * 3600 <= d < h1 * 3600)
                    for p, (h0, h1) in periods.items()
                },
                "first_train": None if rec["first"] is None else fmt_time(rec["first"]),
                "last_train": None if rec["last"] is None else fmt_time(rec["last"]),
                "calls_before_04h": rec["early"],
                "calls_per_day": len(rec["deps"]),
            }
        st_out[s["id"]] = {"name": s["name"], "lines": lines, "status": "scheduled"}
    return {"lines": lines_out, "stations": st_out}


def load_osm(path: Path) -> dict:
    with gzip.open(path, "rt") as f:
        return json.load(f)


def line_table(tt: Timetable, tracks: list, stations: list, gtfs_index: dict) -> list:
    seen = set()
    for t in tracks:
        seen |= set(t["lines"])
    for s in stations:
        seen |= set(s["lines"])
    timetabled = {t["line"] for t in tt.trips}
    out = []
    for lid in LINES:
        if lid not in seen:
            continue
        meta = LINES[lid]
        out.append(
            {
                "id": lid,
                "name": meta["name"],
                "colour": meta["colour"],
                "kind": meta["kind"],
                "timetable": lid in timetabled,
                "note": None
                if lid in timetabled
                else "absent from the BODS GTFS feed: track and stations only (static, no trains)",
            }
        )
    return out


def colour_reference() -> dict:
    return {"source": COLOUR_SOURCE, "colours": {k: v["colour"] for k, v in LINES.items()}}


def gtfs_routes_summary(tt: Timetable) -> dict:
    c = Counter((t["line"], t["route_id"]) for t in tt.trips)
    return {f"{lid}|{rid}": n for (lid, rid), n in sorted(c.items())}


def mean(values):
    values = [v for v in values if v is not None and not math.isnan(v)]
    return statistics.fmean(values) if values else None
