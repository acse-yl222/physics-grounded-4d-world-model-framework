"""SUMO vehicle routes -> lane paths with entry times (``traffic_routes_<period>.json``).

Mesoscopic SUMO moves vehicles between edge segments, so its FCD x/y jump between lanes
and across junctions. The viewer instead moves each vehicle along a lane path of the
exported road network (``road_network``) by the edge times SUMO recorded:

* **Edge times**: ``--vehroute-output`` with ``exit-times`` (and ``write-unfinished`` for
  vehicles still driving at the end). The entry time of an edge is the departure or the
  exit time of the previous edge; mesoscopic SUMO has no internal (junction) edges, so a
  junction is crossed at the exit time of the edge before it.
* **Lane choice** (``LanePlanner``): per vehicle a dynamic programme over the lanes
  permitted to its vClass on each route edge, minimising lane changes: a transition is
  free when a SUMO connection joins the two lanes (its via chain of internal lanes is
  inserted), costs 1 when the vehicle must change lane at the start of the next edge
  (``changes``) and 2 when it also changes on the previous edge. Ties are broken by a
  per-vehicle hash of the lane ids, so traffic spreads over equivalent lanes
  deterministically. A bus uses its stop lane (the kerbside lane of the ``busStop``) on
  every edge where it stops.
* **Timing** (``element_times``): of the time between entering an edge and entering the
  next one, the internal lanes of the connection get ``length / speed`` at the internal
  lanes' (junction) speed limit, but never more than their share at constant speed
  (``length`` proportion of edge + internal lanes); the normal lane gets the rest. Within
  a lane a vehicle moves at constant speed, except that a bus holds at its stop position
  between the stop's ``started`` and ``ended`` times (``stops``).
* **Teleports** (``jam`` teleports in the SUMO warning log) and gaps outside the exported
  domain are ``jumps``: ``[i, t]`` means the vehicle left element ``i - 1`` at ``t`` and is
  not drawn until it enters element ``i``; viewers cut instead of animating there.
* **Unfinished**: ``leave`` is null when a vehicle is still on its last element at the end
  of the simulation; ``end_pos`` is then its FCD position projected onto that lane at
  ``t1`` (when recorded), reached at constant speed from the lane entry.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import export

SCHEMA = "corridor-traffic-routes-v1"
INDEX_SCHEMA = "corridor-traffic-routes-index-v1"
MAX_BYTES = 12_000_000
SPEED_CAP = 1.3  # x lane speed limit: fastest plausible traversal (speed factor spread)
VCLASS = {"bus": "bus", "taxi": "taxi"}  # other kinds use passenger permissions
TELEPORT = re.compile(
    r"Teleporting vehicle '(.+?)'; .*?from edge '(.+?)'.*?time=([0-9]+(?:\.[0-9]+)?)"
)
LANE_CHOICE = (
    "Per vehicle, a dynamic programme over the lanes of each route edge that permit its "
    "vClass minimises lane changes: consecutive lanes joined by a SUMO connection cost 0 "
    "(the connection's via chain of internal lanes is inserted), a lane change at the start "
    "of the next edge costs 1 (listed in changes), one on the previous edge as well 2; "
    "ties are broken by a per-vehicle SHA-1 hash of the lane ids, spreading traffic over "
    "equivalent lanes. A bus uses its stop lane on edges with a stop. Elements outside the "
    "exported road network are dropped (jumps)."
)
TIMING = (
    "Edge entry times are SUMO's (vehroute-output exit times: departure, then the exit "
    "time of the previous edge); mesoscopic SUMO has no internal edges, so the internal "
    "lanes of a connection get min(length / internal lane speed, the time at the edge's "
    "mean speed over edge + internal lengths) taken from the end of the edge before it; "
    "the normal lane gets the rest. Mesoscopic exit times are whole seconds: where an "
    "element would be passed faster than 1.3 x its speed limit (often in 0 s), its entry "
    "is moved earlier, taking the time from the elements before it (entries_moved and "
    "max_entry_shift_s in provenance). Constant speed within each element; buses hold at "
    "their stop position from started to ended (stops). jumps [i, t]: element i-1 was left "
    "at t (jam teleport or leaving the exported domain) and element i is entered at "
    "enter[i] without motion in between. leave is null for vehicles still on their last "
    "element at the end of the simulation; end_pos (m along that lane, from FCD at t1) "
    "is reached at constant speed from its entry."
)


# ---------------------------------------------------------------- SUMO outputs


def _open(path: Path):
    return gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")


def read_vehroutes(path: Path, t0: float, t1: float):
    """Vehicles of a vehroute output (with exit times) that can be on the road in
    ``[t0, t1]``: ``{id, type, depart, arrival, edges, exits, stops}``; ``exits`` are
    None for edges not left (unfinished vehicles)."""
    with _open(path) as f:
        for _, el in ET.iterparse(f):
            if el.tag != "vehicle":
                continue
            routes = [r for r in el.iter("route") if r.get("exitTimes")]
            if not routes:
                el.clear()
                continue
            route = routes[-1]
            try:
                depart = float(el.get("depart"))
            except (TypeError, ValueError):
                el.clear()
                continue
            arrival = el.get("arrival")
            arrival = float(arrival) if arrival not in (None, "-1") else None
            if depart > t1 or (arrival is not None and arrival < t0):
                el.clear()
                continue
            exits = [None if v == "-1" else float(v) for v in route.get("exitTimes").split()]
            stops = []
            for st in el.iter("stop"):
                if st.get("started") is None:
                    continue
                stops.append(
                    {
                        "busStop": st.get("busStop"),
                        "lane": st.get("lane"),
                        "endPos": float(st.get("endPos")) if st.get("endPos") else None,
                        "started": float(st.get("started")),
                        "ended": float(st.get("ended")) if st.get("ended") else None,
                    }
                )
            yield {
                "id": el.get("id"),
                "type": el.get("type"),
                "depart": depart,
                "arrival": arrival,
                "edges": route.get("edges").split(),
                "exits": exits,
                "stops": stops,
            }
            el.clear()


def read_bus_stops(paths) -> dict[str, tuple[str, float]]:
    """``{busStop id: (lane id, endPos)}`` from additional files."""
    out = {}
    for path in paths:
        for _, el in ET.iterparse(path):
            if el.tag in ("busStop", "trainStop"):
                out[el.get("id")] = (el.get("lane"), float(el.get("endPos") or 0.0))
            el.clear()
    return out


def read_teleports(path: Path | None) -> dict[str, list[tuple[str, float]]]:
    """``{vehicle: [(from edge, time)]}`` from SUMO warnings ("Teleporting vehicle ...")."""
    out: dict[str, list[tuple[str, float]]] = defaultdict(list)
    if path is None or not Path(path).is_file():
        return out
    with open(path, errors="replace") as f:
        for line in f:
            m = TELEPORT.search(line)
            if m:
                out[m.group(1)].append((m.group(2), float(m.group(3))))
    return out


# ---------------------------------------------------------------- lane choice


def _weight(vid: str, lane: str) -> float:
    return int(hashlib.sha1(f"{vid}|{lane}".encode()).hexdigest()[:6], 16) / 16**6 * 1e-3


class LanePlanner:
    """Lane paths over a sumolib net (read with ``withInternal=True``)."""

    def __init__(self, net):
        self.net = net
        self._links: dict[tuple[str, str], list] = {}
        self._lanes: dict[tuple[str, str], list[str]] = {}

    def lanes(self, edge: str, vclass: str) -> list[str]:
        key = (edge, vclass)
        if key not in self._lanes:
            lanes = self.net.getEdge(edge).getLanes()
            ok = [ln.getID() for ln in lanes if ln.allows(vclass)]
            self._lanes[key] = ok or [ln.getID() for ln in lanes]
        return self._lanes[key]

    def links(self, a: str, b: str) -> list[tuple[str, str, list[str]]]:
        """Connections from edge ``a`` to edge ``b``: (from lane, to lane, via chain)."""
        key = (a, b)
        if key not in self._links:
            out = []
            for ln in self.net.getEdge(a).getLanes():
                for c in ln.getOutgoing():
                    if c.getTo().getID() != b:
                        continue
                    to = c.getToLane().getID()
                    chain, via = [], c.getViaLaneID()
                    while via:
                        chain.append(via)
                        nxt = [
                            c2
                            for c2 in self.net.getLane(via).getOutgoing()
                            if c2.getToLane().getID() == to
                        ]
                        via = nxt[0].getViaLaneID() if nxt else ""
                    out.append((ln.getID(), to, chain))
            self._links[key] = out
        return self._links[key]

    def plan(self, vid: str, vclass: str, edges: list[str], forced: dict[int, str] | None = None):
        """Lanes of ``edges`` and the transitions between them.

        Returns ``(lanes, steps)``: ``steps[i]`` (between edge i and i + 1) is
        ``(chain, change_at_chain, change_at_next, connected)``.
        """
        forced = forced or {}
        n = len(edges)
        cands = [[forced[i]] if i in forced else self.lanes(e, vclass) for i, e in enumerate(edges)]
        cost = [{ln: _weight(vid, ln) for ln in cands[0]}]
        back: list[dict] = [{}]
        for i in range(1, n):
            links = self.links(edges[i - 1], edges[i])
            index = {ln: self.net.getLane(ln).getIndex() for ln in cands[i - 1] + cands[i]}
            for f, t, _ in links:
                index.setdefault(f, self.net.getLane(f).getIndex())
                index.setdefault(t, self.net.getLane(t).getIndex())
            cur, bk = {}, {}
            for b in cands[i]:
                best = None
                for a, ca in cost[i - 1].items():
                    step = self._step(a, b, links, index)
                    total = ca + step[0] + _weight(vid, b)
                    if best is None or total < best[0]:
                        best = (total, a, step[1:])
                cur[b], bk[b] = best[0], (best[1], best[2])
            cost.append(cur)
            back.append(bk)
        lane = min(cost[-1], key=cost[-1].get)
        lanes, steps = [lane], []
        for i in range(n - 1, 0, -1):
            a, step = back[i][lane]
            steps.append(step)
            lanes.append(a)
            lane = a
        return lanes[::-1], steps[::-1]

    @staticmethod
    def _step(a: str, b: str, links: list, index: dict):
        """(cost, chain, change at chain start, change at next lane, connected)."""
        if not links:
            return (5.0, [], False, False, False)
        direct = [lk for lk in links if lk[0] == a and lk[1] == b]
        if direct:
            return (0.0, direct[0][2], False, False, True)
        own = [lk for lk in links if lk[0] == a]
        if own:
            lk = min(own, key=lambda k: (abs(index[k[1]] - index[b]), k[1]))
            return (1.0, lk[2], False, True, True)
        lk = min(
            links,
            key=lambda k: (abs(index[k[0]] - index[a]) + abs(index[k[1]] - index[b]), k[0], k[1]),
        )
        return (2.0, lk[2], True, lk[1] != b, True)


# ---------------------------------------------------------------- timing


def element_times(
    entry: float,
    exit_: float | None,
    lane_len: float,
    chain: list[tuple[float, float]],
    teleport: bool = False,
) -> list[float]:
    """Entry times of a normal lane and its following internal lanes.

    ``chain``: (length, speed) of the internal lanes. The internal lanes get
    ``min(sum length / min speed, T * L_int / (L_lane + L_int))`` (``T`` = time from the
    edge entry to the next edge entry), split by length, at the end of the interval;
    none after a teleport or when the edge is not left (``exit_`` None).
    """
    times = [entry]
    if not chain:
        return times
    if exit_ is None:
        return times + [None] * len(chain)
    total = max(0.0, exit_ - entry)
    lengths = [max(c[0], 0.0) for c in chain]
    l_int = sum(lengths)
    if teleport or l_int <= 0:
        t_int = 0.0
    else:
        v = max(min(c[1] for c in chain), 0.1)
        t_int = min(l_int / v, total * l_int / (lane_len + l_int))
    t = exit_ - t_int
    for length in lengths:
        times.append(t)
        t += t_int * length / l_int if l_int > 0 else 0.0
    return times


# ---------------------------------------------------------------- vehicles


class Network:
    """Exported lanes (``road_network`` document) for path lookup and reconstruction."""

    def __init__(self, doc: dict):
        self.lanes = doc["lanes"]
        self.index = {ln["id"]: k for k, ln in enumerate(self.lanes)}
        self._geom: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def geom(self, k: int) -> tuple[np.ndarray, np.ndarray]:
        """(xy points, cumulative 2D length) of lane ``k``'s exported shape."""
        if k not in self._geom:
            p = np.asarray(self.lanes[k]["shape"], dtype=np.float64)[:, :2]
            s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
            self._geom[k] = (p, s)
        return self._geom[k]

    def length(self, k: int) -> float:
        return float(self.geom(k)[1][-1])

    def at(self, k: int, d: np.ndarray | float) -> np.ndarray:
        """Points at 2D distance ``d`` along lane ``k`` (clamped to the lane)."""
        p, s = self.geom(k)
        d = np.clip(np.asarray(d, dtype=np.float64), 0.0, s[-1])
        if len(p) == 1 or s[-1] <= 0:
            return np.broadcast_to(p[0], (*np.shape(d), 2)).copy()
        x = np.interp(d, s, p[:, 0])
        y = np.interp(d, s, p[:, 1])
        return np.stack([x, y], axis=-1)

    def project(self, k: int, x: float, y: float) -> float:
        """Distance along lane ``k`` of the point of its centre line nearest (x, y)."""
        p, s = self.geom(k)
        if len(p) < 2:
            return 0.0
        a, b = p[:-1], p[1:]
        d = b - a
        dd = np.maximum((d * d).sum(1), 1e-12)
        t = np.clip(((np.array([x, y]) - a) * d).sum(1) / dd, 0, 1)
        near = a + t[:, None] * d
        k2 = int(np.hypot(*(near - [x, y]).T).argmin())
        return float(s[k2] + t[k2] * math.sqrt(dd[k2]))


def build_vehicle(
    veh: dict,
    kind: str,
    planner: LanePlanner,
    net_lanes: Network,
    sumo_net,
    window: tuple[float, float],
    bus_stops: dict,
    teleports: list[tuple[str, float]],
    end_xy: tuple[float, float] | None = None,
    stats: dict | None = None,
) -> dict | None:
    """One ``vehicles[]`` entry, or None when not on an exported lane in the window."""
    t0, t1 = window
    edges, exits = veh["edges"], veh["exits"]
    n = len(edges)
    entries = [veh["depart"]] + exits[:-1]
    # Route indices that can overlap the window (plus one for the last transition).
    first = next((i for i in range(n) if exits[i] is None or exits[i] >= t0), None)
    if first is None:
        return None
    last = first
    while last + 1 < n and entries[last + 1] is not None and entries[last + 1] <= t1:
        last += 1
    hi = min(n - 1, last + 1)
    if entries[hi] is None:
        hi = last
    sub = list(range(first, hi + 1))
    # Stops: route index of each reached stop, in order.
    forced, stops = {}, []
    k0 = 0
    for st in veh["stops"]:
        lane, pos = st["lane"], st["endPos"]
        if st["busStop"] and st["busStop"] in bus_stops:
            lane, pos0 = bus_stops[st["busStop"]]
            pos = pos if pos is not None else pos0
        if not lane:
            continue
        edge = lane.rsplit("_", 1)[0]
        idx = next((i for i in range(k0, n) if edges[i] == edge), None)
        if idx is None:
            continue
        k0 = idx
        if first <= idx <= hi:
            forced[idx - first] = lane
            stops.append((idx, pos, st["started"], st["ended"]))
    vclass = VCLASS.get(kind, "passenger")
    lanes, steps = planner.plan(veh["id"], vclass, [edges[i] for i in sub], forced)
    tele = set()
    for edge, t in teleports:
        cands = [i for i in sub if edges[i] == edge and exits[i] is not None]
        if cands:
            tele.add(min(cands, key=lambda i: abs(exits[i] - t)))
    # Elements in driving order: normal lane of each route edge, then the internal
    # lanes of the connection to the next edge.
    elems: list[dict] = []
    change = jump = False
    for j, i in enumerate(sub):
        elems.append({"lane": lanes[j], "enter": entries[i], "change": change, "jump": jump})
        elems[-1]["route"] = i
        change = jump = False
        if j == len(steps):
            break
        chain, ch_chain, ch_next, connected = steps[j]
        spec = [(sumo_net.getLane(v).getLength(), sumo_net.getLane(v).getSpeed()) for v in chain]
        lane_len = sumo_net.getLane(lanes[j]).getLength()
        times = element_times(entries[i], exits[i], lane_len, spec, teleport=i in tele)
        for k, v in enumerate(chain):
            first_via = k == 0
            elems.append(
                {
                    "lane": v,
                    "enter": times[k + 1],
                    "change": ch_chain and first_via,
                    "jump": (i in tele or not connected) and first_via,
                }
            )
        change = ch_next or (ch_chain and not chain)
        jump = not connected or (i in tele and not chain)
    leave = exits[sub[-1]]  # arrival on the last route edge; None while still driving
    dwell = {idx: (ended or started) - started for idx, _, started, ended in stops}
    smooth_entries(elems, leave, sumo_net, dwell, stats)
    return finish(veh, kind, elems, leave, stops, net_lanes, sumo_net, window, end_xy)


def smooth_entries(elems, leave, sumo_net, dwell, stats=None) -> None:
    """Mesoscopic exit times are whole seconds, so a short lane can be entered and left
    in the same second. Where an element is shorter in time than its length at
    ``SPEED_CAP`` x its speed limit, its entry is moved earlier (taking the time from the
    elements before it, never before the first entry of a jump-free run); jumps are
    barriers and the times after them are unchanged."""
    m = len(elems)
    if m < 2:
        return
    mins = []
    for el in elems:
        lane = sumo_net.getLane(el["lane"])
        v = max(SPEED_CAP * lane.getSpeed(), 5.0)
        mins.append(lane.getLength() / v + dwell.get(el.get("route"), 0.0))
    starts = [0] + [k for k in range(1, m) if elems[k]["jump"]]
    for a, b in zip(starts, [*starts[1:], m], strict=True):
        last = b - 1
        end = elems[b]["enter"] if b < m else leave
        floor = elems[a]["enter"]
        k = last
        while k >= a:
            if end is None:
                end = elems[k]["enter"]
                k -= 1
                continue
            el = elems[k]
            if k > a and end - el["enter"] < mins[k] - 1e-9:
                new = max(floor, end - mins[k])
                if new < el["enter"]:
                    if stats is not None:
                        stats["entries_moved"] = stats.get("entries_moved", 0) + 1
                        shift = el["enter"] - new
                        stats["max_entry_shift_s"] = max(stats.get("max_entry_shift_s", 0), shift)
                    el["enter"] = new
            end = el["enter"]
            k -= 1


def _t(v: float) -> float:
    return round(float(v), 1)


def finish(veh, kind, elems, leave, stops, net_lanes, sumo_net, window, end_xy) -> dict | None:
    """Trim elements to the window and the exported lanes; build the output entry."""
    t0, t1 = window
    m = len(elems)
    ends = [elems[k + 1]["enter"] for k in range(m - 1)] + [leave]
    keep = [
        k
        for k in range(m)
        if elems[k]["enter"] is not None
        and elems[k]["enter"] <= t1
        and (ends[k] is None or ends[k] > t0 or (ends[k] == t0 and k == m - 1))
    ]
    if not keep:
        return None
    ka, kb = keep[0], keep[-1]
    out_leave = ends[kb]
    path, enter, jumps, changes, route_at = [], [], [], [], {}
    gap = None
    for k in range(ka, kb + 1):
        el = elems[k]
        idx = net_lanes.index.get(el["lane"])
        if idx is None:
            if gap is None:
                gap = el["enter"]
            continue
        if path and (gap is not None or el["jump"]):
            jumps.append([len(path), _t(gap if gap is not None else el["enter"])])
        elif path and el["change"]:
            changes.append(len(path))
        gap = None
        if "route" in el:
            route_at[el["route"]] = len(path)
        path.append(idx)
        enter.append(_t(el["enter"]))
    if not path:
        return None
    if gap is not None:  # trailing elements outside the exported network
        out_leave = gap
    entry = {
        "id": veh["id"],
        "type": kind,
        "path": path,
        "enter": enter,
        "leave": None if out_leave is None else _t(out_leave),
    }
    if jumps:
        entry["jumps"] = jumps
    if changes:
        entry["changes"] = changes
    out_stops = []
    for idx, pos, started, ended in stops:
        k = route_at.get(idx)
        if k is None:
            continue
        lane = net_lanes.lanes[path[k]]
        scale = net_lanes.length(path[k]) / max(lane["length"], 1e-6)
        lo = enter[k]
        hi = enter[k + 1] if k + 1 < len(path) else entry["leave"]
        arrive = max(started, lo)
        depart = ended if ended is not None else (hi if hi is not None else t1)
        if hi is not None:
            arrive, depart = min(arrive, hi), min(depart, hi)
        out_stops.append(
            {
                "path_index": k,
                "pos_m": round(min(pos, lane["length"]) * scale, 1),
                "arrive": _t(arrive),
                "depart": _t(max(depart, arrive)),
            }
        )
    if out_stops:
        entry["stops"] = out_stops
    if entry["leave"] is None and end_xy is not None:
        k = path[-1]
        entry["end_pos"] = round(net_lanes.project(k, *end_xy), 1)
    return entry


# ---------------------------------------------------------------- documents


def _dump(doc) -> bytes:
    return (json.dumps(doc, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write(vehicles: list[dict], path: Path, header: dict, max_bytes: int = MAX_BYTES) -> list[str]:
    """Write ``traffic_routes_<period>.json``; when it exceeds ``max_bytes`` it becomes an
    index of ``<stem>_<k>.json`` chunks (contiguous slices of ``vehicles``). Returns the
    file names written (index or whole document first)."""
    doc = {"schema": SCHEMA, **header, "vehicles": vehicles}
    whole = _dump(doc)
    if len(whole) <= max_bytes:
        path.write_bytes(whole)
        return [path.name]
    parts = math.ceil(len(whole) / (0.9 * max_bytes))
    while True:
        chunks = []
        for k in range(parts):
            lo, hi = len(vehicles) * k // parts, len(vehicles) * (k + 1) // parts
            chunks.append(
                _dump(
                    {
                        "schema": SCHEMA,
                        "period": header["period"],
                        "part": k,
                        "parts": parts,
                        "offset": lo,
                        "vehicles": vehicles[lo:hi],
                    }
                )
            )
        if max(map(len, chunks)) <= max_bytes:
            break
        parts += 1
    names, entries = [path.name], []
    for k, raw in enumerate(chunks):
        name = f"{path.stem}_{k}.json"
        (path.parent / name).write_bytes(raw)
        names.append(name)
        entries.append(
            {"asset": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    index = {
        "schema": INDEX_SCHEMA,
        "chunk_schema": SCHEMA,
        **header,
        "vehicles_total": len(vehicles),
        "chunks": entries,
    }
    path.write_bytes(_dump(index))
    return names


def load(path: Path) -> dict:
    """Read a routes document (whole or chunked) as one document."""
    doc = json.loads(path.read_text())
    if doc.get("schema") == SCHEMA:
        return doc
    if doc.get("schema") != INDEX_SCHEMA:
        raise ValueError(f"unknown routes schema {doc.get('schema')!r}")
    out = {k: v for k, v in doc.items() if k not in ("chunks", "vehicles_total", "chunk_schema")}
    out["schema"], out["vehicles"] = SCHEMA, []
    for entry in doc["chunks"]:
        out["vehicles"] += json.loads((path.parent / entry["asset"]).read_text())["vehicles"]
    return out


# ---------------------------------------------------------------- playback


def element_ends(veh: dict, t1: float) -> np.ndarray:
    """End time of each path element (next entry, the jump time, or leave / t1)."""
    enter = np.asarray(veh["enter"], dtype=np.float64)
    ends = np.empty_like(enter)
    ends[:-1] = enter[1:]
    ends[-1] = veh["leave"] if veh["leave"] is not None else math.inf
    for i, left in veh.get("jumps", []):
        ends[i - 1] = min(ends[i - 1], left)
    return ends


def positions(veh: dict, net: Network, times: np.ndarray, t1: float) -> dict:
    """Reconstructed playback at ``times``: element index (-1 = not drawn), distance
    along the element, distance along the whole path and x/y."""
    enter = np.asarray(veh["enter"], dtype=np.float64)
    ends = element_ends(veh, t1)
    lengths = np.array([net.length(k) for k in veh["path"]])
    cum = np.concatenate([[0.0], np.cumsum(lengths)])
    k = np.searchsorted(enter, times, side="right") - 1
    valid = k >= 0
    kk = np.clip(k, 0, len(enter) - 1)
    last = kk == len(enter) - 1
    open_end = veh["leave"] is None
    valid &= (times < ends[kk]) | (last & open_end & (times <= t1))
    dur = ends[kk] - enter[kk]
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(dur > 0, (times - enter[kk]) / dur, 1.0)
    d = np.clip(frac, 0, 1) * lengths[kk]
    if open_end:
        m = last & valid
        e0 = enter[-1]
        if veh.get("end_pos") is not None and t1 > e0:
            d[m] = np.clip(veh["end_pos"] * (times[m] - e0) / (t1 - e0), 0, lengths[-1])
        else:
            speed = net.lanes[veh["path"][-1]]["speed"]
            d[m] = np.minimum(lengths[-1], speed * (times[m] - e0))
    for st in veh.get("stops", []):
        i, pos, a, b = st["path_index"], st["pos_m"], st["arrive"], st["depart"]
        m = valid & (kk == i)
        if not m.any():
            continue
        e, end = enter[i], ends[i] if math.isfinite(ends[i]) else t1
        t = times[m]
        before = np.where(a > e, pos * (t - e) / max(a - e, 1e-9), pos)
        after = pos + (lengths[i] - pos) * (t - b) / max(end - b, 1e-9)
        d[m] = np.clip(np.where(t < a, before, np.where(t < b, pos, after)), 0, lengths[i])
    xy = np.full((len(times), 2), np.nan)
    for j in np.unique(kk[valid]):
        m = valid & (kk == j)
        xy[m] = net.at(veh["path"][j], d[m])
    return {"k": np.where(valid, kk, -1), "d": d, "s": cum[kk] + d, "xy": xy}


# ---------------------------------------------------------------- verification


class SegmentGrid:
    """Distance (capped at ``reach``) from points to the nearest lane centre line."""

    def __init__(self, net: Network, cell: float = 20.0, reach: float = 2.0):
        self.cell, self.reach = cell, reach
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        a_list, b_list = [], []
        for k in range(len(net.lanes)):
            p, _ = net.geom(k)
            for a, b in itertools.pairwise(p):
                n = len(a_list)
                a_list.append(a)
                b_list.append(b)
                lo = np.floor((np.minimum(a, b) - reach) / cell).astype(int)
                hi = np.floor((np.maximum(a, b) + reach) / cell).astype(int)
                for i in range(lo[0], hi[0] + 1):
                    for j in range(lo[1], hi[1] + 1):
                        buckets[(i, j)].append(n)
        self.a, self.b = np.array(a_list), np.array(b_list)
        self.buckets = {k: np.array(v) for k, v in buckets.items()}

    def distance(self, pts: np.ndarray) -> np.ndarray:
        out = np.full(len(pts), self.reach)
        cells = np.floor(pts / self.cell).astype(int)
        order = np.lexsort((cells[:, 1], cells[:, 0]))
        keys = cells[order]
        bounds = np.flatnonzero(np.any(np.diff(keys, axis=0) != 0, axis=1)) + 1
        for grp in np.split(order, bounds):
            seg = self.buckets.get(tuple(cells[grp[0]]))
            if seg is None:
                continue
            a, b = self.a[seg], self.b[seg]
            d = b - a
            dd = np.maximum((d * d).sum(1), 1e-12)
            p = pts[grp]
            t = np.clip(((p[:, None] - a[None]) * d[None]).sum(2) / dd[None], 0, 1)
            near = a[None] + t[..., None] * d[None]
            dist = np.hypot(*(p[:, None] - near).transpose(2, 0, 1)).min(1)
            out[grp] = np.minimum(dist, self.reach)
        return out


def _close_pairs(frames: list[np.ndarray], radius: float) -> tuple[int, int]:
    """(points with another point within ``radius``, points) over frames of x/y arrays."""
    hit = total = 0
    for p in frames:
        total += len(p)
        if len(p) < 2:
            continue
        cells = np.floor(p / radius).astype(np.int64)
        near = np.zeros(len(p), dtype=bool)
        table: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i, c in enumerate(map(tuple, cells)):
            table[c].append(i)
        for (cx, cy), members in table.items():
            cand = [
                j
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                for j in table.get((cx + dx, cy + dy), ())
            ]
            if len(cand) < 2:
                continue
            q = p[members]
            r = p[cand]
            dist = np.hypot(*(q[:, None] - r[None]).transpose(2, 0, 1))
            same = np.array(members)[:, None] == np.array(cand)[None]
            near[members] |= ((dist < radius) & ~same).any(1)
        hit += int(near.sum())
    return hit, total


def verify(
    doc: dict,
    net: Network,
    rec=None,
    sample: int = 500,
    overlap_radius: float = 4.0,
    max_speed: float = 40.0,
    grid: SegmentGrid | None = None,
) -> dict:
    """Checks of the lane-path playback against the lanes and the FCD playback.

    ``rec``: ``export.Recording`` of the FCD window (all vehicles in the domain).
    """
    t0, t1 = doc["t0"], doc["t1"]
    times = np.arange(t0, t1 + 1e-9, 1.0)
    vehicles = doc["vehicles"]
    order = sorted(
        range(len(vehicles)), key=lambda i: hashlib.sha1(vehicles[i]["id"].encode()).hexdigest()
    )
    chosen = order[:sample]
    grid = grid or SegmentGrid(net)
    pos = {i: positions(vehicles[i], net, times, t1) for i in range(len(vehicles))}

    # Lateral distance, steps and speeds for the sample.
    lat, steps, speeds, side, jump_steps = [], [], [], [], 0
    for i in chosen:
        p = pos[i]
        ok = p["k"] >= 0
        lat.append(grid.distance(p["xy"][ok]))
        both = ok[1:] & ok[:-1]
        jumped = np.zeros(len(times) - 1, dtype=bool)
        for jk, _ in vehicles[i].get("jumps", []):
            jumped |= (p["k"][:-1] < jk) & (p["k"][1:] >= jk)
        jump_steps += int((both & jumped).sum())
        use = both & ~jumped
        ds = np.diff(p["s"])[use]
        speeds.append(ds)
        delta = np.diff(p["xy"], axis=0)[use]
        steps.append(np.hypot(*delta.T))
        tang = tangents(vehicles[i], net, p)
        side.append(_sideways(delta, tang[:-1][use] + tang[1:][use]))
    lat = np.concatenate(lat) if lat else np.zeros(0)
    steps = np.concatenate(steps) if steps else np.zeros(0)
    speeds = np.concatenate(speeds) if speeds else np.zeros(0)
    side = np.concatenate(side) if side else np.zeros(0)

    # Element-level implied speeds (all vehicles).
    elem_speed, zero_dur = [], 0
    for v in vehicles:
        ends = element_ends(v, t1)
        enter = np.asarray(v["enter"])
        lengths = np.array([net.length(k) for k in v["path"]])
        dur = ends - enter
        fin = np.isfinite(dur)
        stop_on = {st["path_index"]: st for st in v.get("stops", [])}
        # Skipped: the first element (entered at the departure position, unknown),
        # elements passed by a jump and lanes shorter than 2 m (0.1 s time rounding).
        skipped = {
            k for i, _ in v.get("jumps", []) for k in range(i, len(enter)) if enter[k] == enter[i]
        }
        for k in np.flatnonzero(fin):
            if k == 0 or k in skipped or lengths[k] < 2.0:
                continue
            moving = dur[k]
            if k in stop_on:
                moving -= stop_on[k]["depart"] - stop_on[k]["arrive"]
            if moving <= 0:
                zero_dur += 1
                continue
            elem_speed.append(lengths[k] / moving)
    elem_speed = np.array(elem_speed) if elem_speed else np.zeros(0)

    # Same-lane overlaps (all vehicles, every second).
    tk, lane, dd = [], [], []
    for i, v in enumerate(vehicles):
        p = pos[i]
        ok = np.flatnonzero(p["k"] >= 0)
        tk.append(ok)
        lane.append(np.asarray(v["path"])[p["k"][ok]])
        dd.append(p["d"][ok])
    tk, lane, dd = np.concatenate(tk), np.concatenate(lane), np.concatenate(dd)
    o = np.lexsort((dd, lane, tk))
    tk, lane, dd = tk[o], lane[o], dd[o]
    pair = (tk[1:] == tk[:-1]) & (lane[1:] == lane[:-1]) & (np.diff(dd) < overlap_radius)
    flagged = np.zeros(len(tk), dtype=bool)
    flagged[1:] |= pair
    flagged[:-1] |= pair
    # 2D proximity every 10 s, lane paths vs FCD (same measure for both).
    every = range(0, len(times), 10)
    rec_frames = []
    for j in every:
        pts = [pos[i]["xy"][j] for i in range(len(vehicles)) if pos[i]["k"][j] >= 0]
        rec_frames.append(np.array(pts).reshape(-1, 2))
    near_lane, n_lane = _close_pairs(rec_frames, overlap_radius)
    out = {
        "sample_vehicles": len(chosen),
        "vehicles": len(vehicles),
        "steps_s": 1.0,
        "lane_paths": {
            "lateral_gt_1m_share": _share(lat > 1.0),
            "lateral_p99_m": _pct(lat, 99),
            "still_step_share": _share(steps < 0.01) if len(steps) else None,
            "step_gt_25m_share": _share(steps > 25.0),
            "sideways_step_gt_1m_share": _share(side > 1.0),
            "step_speed_max_mps": _round(speeds.max()) if len(speeds) else None,
            "step_speed_p99_mps": _pct(speeds, 99),
            "step_speed_gt_40_share": _share(speeds > max_speed),
            "jump_steps": jump_steps,
            "element_speed_max_mps": _round(elem_speed.max()) if len(elem_speed) else None,
            "element_speed_p99_mps": _pct(elem_speed, 99),
            "elements_over_40_mps": int((elem_speed > max_speed).sum()),
            "elements_zero_duration": zero_dur,
            "elements_timed": len(elem_speed),
            "vehicles_with_jumps_share": _share(np.array([bool(v.get("jumps")) for v in vehicles])),
            "vehicles_with_lane_changes_share": _share(
                np.array([bool(v.get("changes")) for v in vehicles])
            ),
            "lane_changes": sum(len(v.get("changes", [])) for v in vehicles),
            "same_lane_within_4m_vehicle_step_share": _share(flagged),
            "same_lane_pairs_within_4m_per_step": _round(pair.sum() / len(times)),
            "within_4m_2d_share_10s": _round(near_lane / max(n_lane, 1), 4),
        },
    }
    if rec is not None:
        out["fcd"] = _fcd_checks(
            rec,
            [vehicles[i]["id"] for i in chosen],
            grid,
            every,
            pos,
            vehicles,
            chosen,
            times,
            overlap_radius,
        )
    return out


def _fcd_checks(rec, ids, grid, every, pos, vehicles, chosen, times, radius) -> dict:
    index = {v["id"]: k for k, v in enumerate(rec.vehicles)}
    tindex = {t: j for j, t in enumerate(rec.times)}
    want = {index[i] for i in ids if i in index}
    tracks: dict[int, dict[float, tuple[float, float, float]]] = defaultdict(dict)
    for t, frame in zip(rec.times, rec.frames, strict=True):
        for i, x, y, h in frame:
            if i in want:
                tracks[i][t] = (x, y, h)
    lat, steps, side, diffs = [], [], [], []
    for vid in ids:
        if vid not in index:
            continue
        tr = tracks.get(index[vid], {})
        ts = sorted(tr)
        if not ts:
            continue
        xyh = np.array([tr[t] for t in ts])
        xy, h = xyh[:, :2], xyh[:, 2]
        lat.append(grid.distance(xy))
        consecutive = np.diff(ts) <= 1.0 + 1e-6
        delta = np.diff(xy, axis=0)[consecutive]
        steps.append(np.hypot(*delta.T))
        heading = np.column_stack([np.cos(h), np.sin(h)])
        side.append(_sideways(delta, (heading[:-1] + heading[1:])[consecutive]))
    for i in chosen:
        v = vehicles[i]
        if v["id"] not in index:
            continue
        tr = tracks.get(index[v["id"]], {})
        p = pos[i]
        for j, t in enumerate(times):
            if p["k"][j] >= 0 and t in tr:
                diffs.append(math.hypot(p["xy"][j][0] - tr[t][0], p["xy"][j][1] - tr[t][1]))
    lat = np.concatenate(lat) if lat else np.zeros(0)
    steps = np.concatenate(steps) if steps else np.zeros(0)
    side = np.concatenate(side) if side else np.zeros(0)
    diffs = np.array(diffs)
    frames = [
        np.array([(x, y) for _, x, y, _ in rec.frames[tindex[times[j]]]]).reshape(-1, 2)
        for j in every
        if times[j] in tindex
    ]
    near, n = _close_pairs(frames, radius)
    return {
        "lateral_gt_1m_share": _share(lat > 1.0),
        "lateral_p99_m": _pct(lat, 99),
        "still_step_share": _share(steps < 0.01),
        "step_gt_25m_share": _share(steps > 25.0),
        "step_max_m": _round(steps.max()) if len(steps) else None,
        "sideways_step_gt_1m_share": _share(side > 1.0),
        "within_4m_2d_share_10s": _round(near / max(n, 1), 4),
        "lane_path_vs_fcd_distance_m": {
            "median": _pct(diffs, 50),
            "p90": _pct(diffs, 90),
            "samples": len(diffs),
        },
    }


def tangents(veh: dict, net: Network, p: dict) -> np.ndarray:
    """Unit lane directions at the reconstructed positions (0 where not drawn)."""
    out = np.zeros((len(p["k"]), 2))
    for j in np.unique(p["k"][p["k"] >= 0]):
        m = p["k"] == j
        lane = veh["path"][j]
        d = p["d"][m]
        v = net.at(lane, d + 0.5) - net.at(lane, d - 0.5)
        n = np.hypot(*v.T)[:, None]
        out[m] = np.divide(v, n, out=np.zeros_like(v), where=n > 0)
    return out


def _sideways(delta: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """Displacement component across ``direction`` (not normalised: sum of tangents)."""
    n = np.hypot(*direction.T)
    cross = np.abs(direction[:, 0] * delta[:, 1] - direction[:, 1] * delta[:, 0])
    return np.divide(cross, n, out=np.zeros_like(cross), where=n > 0)


def _share(mask) -> float | None:
    mask = np.asarray(mask)
    return round(float(mask.mean()), 4) if mask.size else None


def _pct(values, q) -> float | None:
    values = np.asarray(values)
    return round(float(np.percentile(values, q)), 2) if values.size else None


def _round(v, nd: int = 2) -> float:
    return round(float(v), nd)


# ---------------------------------------------------------------- period document


def build_period(
    vehroutes: Path,
    sumo_net,
    net: Network,
    window: tuple[float, float],
    kinds: dict[str, str],
    bus_stops: dict,
    teleports: dict,
    end_xy: dict[str, tuple[float, float]] | None = None,
) -> tuple[list[dict], dict]:
    """Vehicles of one period (sorted by id) and counts."""
    planner = LanePlanner(sumo_net)
    out, counts, timing = [], defaultdict(int), {}
    for veh in read_vehroutes(vehroutes, *window):
        counts["read"] += 1
        kind = kinds.get(veh["type"]) or export.vehicle_type(veh["type"])
        entry = build_vehicle(
            veh,
            kind,
            planner,
            net,
            sumo_net,
            window,
            bus_stops,
            teleports.get(veh["id"], []),
            (end_xy or {}).get(veh["id"]),
            timing,
        )
        if entry is None:
            continue
        out.append(entry)
        counts[kind] += 1
    out.sort(key=lambda v: v["id"])
    counts = dict(counts)
    counts["entries_moved"] = timing.get("entries_moved", 0)
    counts["max_entry_shift_s"] = round(timing.get("max_entry_shift_s", 0.0), 1)
    return out, counts
