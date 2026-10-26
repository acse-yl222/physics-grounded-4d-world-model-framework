"""TfL Unified API adapter: cached bus routes/stops/frequencies -> SUMO bus demand.

Download (``fetch``) needs network access to ``api.tfl.gov.uk``; ``TFL_APP_KEY`` is
used when set (never written to disk). Everything is cached under
``project/<scene>/input/tfl/`` with ``provenance.json`` written last, so an
interrupted download never looks complete. ``build_sumo`` reads only that cache.
No TfL data is ever invented: lines without a usable route geometry are skipped,
and lines without an API frequency are skipped unless the scene configuration
sets an explicit ``default_headway_s`` (recorded as an assumption).

Powered by TfL Open Data. Contains OS data (c) Crown copyright and database rights.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import quoteattr

from . import sumo_env

API = "https://api.tfl.gov.uk"
LICENSE = (
    "Powered by TfL Open Data. Contains OS data (c) Crown copyright and database rights 2016 "
    "and Geomni UK Map data (c) and database rights 2019 (TfL Open Data terms)"
)
DIRECTIONS = ("outbound", "inbound")
R = 6378137.0


class Enu:
    """Same tangent-plane projection as ``fetch_overture.Enu`` (scene ENU metres)."""

    def __init__(self, lon: float, lat: float):
        self.lon0, self.lat0 = lon, lat
        self.kx = math.radians(1) * R * math.cos(math.radians(lat))
        self.ky = math.radians(1) * R

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky

    def inverse(self, x: float, y: float) -> tuple[float, float]:
        return self.lon0 + x / self.kx, self.lat0 + y / self.ky


# ---------------------------------------------------------------- download


def _get(path: str, params: dict | None = None, timeout: float = 30.0):
    query = dict(params or {})
    key = os.environ.get("TFL_APP_KEY")
    if key:
        query["app_key"] = key
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    request = urllib.request.Request(url, headers={"User-Agent": "p4d-corridor-sumo/1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:  # rate limited: back off
                time.sleep(10 * (attempt + 1))
                continue
            raise


def _public_url(path: str, params: dict | None = None) -> str:
    """URL as recorded in provenance (never contains the app key)."""
    return API + path + ("?" + urllib.parse.urlencode(params) if params else "")


def stop_grid(half: float, radius: float) -> list[tuple[float, float]]:
    """Circle centres (ENU) whose ``radius`` discs cover the square domain."""
    step = radius * math.sqrt(2)
    n = max(1, math.ceil(2 * half / step))
    centres = [-half + step * (i + 0.5) * (2 * half / (n * step)) for i in range(n)]
    return [(x, y) for x in centres for y in centres]


def fetch(cache_dir: Path, origin: dict, half: float, cfg: dict, log=print) -> Path:
    """Download TfL bus lines intersecting the domain into ``cache_dir``.

    Files are written to ``<cache_dir>.partial`` and renamed only when complete;
    on any failure the partial download is removed and the error re-raised.
    """
    partial = cache_dir.with_name(cache_dir.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    try:
        _download(partial, origin, half, cfg, log)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    partial.rename(cache_dir)
    return cache_dir


def _download(partial: Path, origin: dict, half: float, cfg: dict, log) -> None:
    enu = Enu(origin["longitude"], origin["latitude"])
    (partial / "route_sequence").mkdir(parents=True)
    (partial / "timetable").mkdir()
    requests: list[dict] = []

    def save(rel: str, data, path: str, params: dict | None = None) -> None:
        target = partial / rel
        target.write_text(json.dumps(data, separators=(",", ":")))
        requests.append(
            {
                "file": rel,
                "url": _public_url(path, params),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )

    bus_lines = _get("/Line/Mode/bus")
    save("lines.json", bus_lines, "/Line/Mode/bus")
    bus_ids = {line["id"] for line in bus_lines}

    radius = float(cfg.get("stop_search_radius_m", 1000))
    stops: dict[str, dict] = {}
    truncated = []
    for i, (x, y) in enumerate(stop_grid(half, radius)):
        lon, lat = enu.inverse(x, y)
        params = {
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "radius": int(radius),
            "stopTypes": "NaptanPublicBusCoachTram",
            "modes": "bus",
            "returnLines": "true",
        }
        page = _get("/StopPoint", params)
        save(f"stop_search_{i:03d}.json", page, "/StopPoint", params)
        if page.get("total") and page["total"] > len(page.get("stopPoints", [])):
            truncated.append(i)
        for stop in page.get("stopPoints", []):
            sx, sy = enu(stop["lon"], stop["lat"])
            if abs(sx) <= half and abs(sy) <= half:
                stops[stop["naptanId"]] = stop
    lines = sorted({ln["id"] for s in stops.values() for ln in s.get("lines", [])} & bus_ids)
    log(f"TfL: {len(stops)} bus stops and {len(lines)} bus lines inside the domain")
    timetables = 0
    for line in lines:
        for direction in DIRECTIONS:
            path = f"/Line/{urllib.parse.quote(line)}/Route/Sequence/{direction}"
            params = {"excludeCrowding": "true"}
            data = _get(path, params)
            save(f"route_sequence/{line}_{direction}.json", data, path, params)
            if not cfg.get("timetable", True):
                continue
            first = first_stop(data)
            if first is None:
                continue
            path = f"/Line/{urllib.parse.quote(line)}/Timetable/{urllib.parse.quote(first)}"
            params = {"direction": direction}
            try:
                save(f"timetable/{line}_{direction}.json", _get(path, params), path, params)
                timetables += 1
            except urllib.error.HTTPError as exc:
                log(f"TfL: no timetable for {line} {direction} ({exc.code})")
    (partial / "stop_points.json").write_text(
        json.dumps({"stopPoints": list(stops.values())}, separators=(",", ":"))
    )
    provenance = {
        "source": "TfL Unified API",
        "api": API,
        "license": LICENSE,
        "fetched_at": datetime.now(UTC).isoformat(),
        "app_key_used": bool(os.environ.get("TFL_APP_KEY")),
        "domain": {"origin": origin, "half_m": half},
        "lines": lines,
        "stop_points": len(stops),
        "timetables": timetables,
        "truncated_stop_searches": truncated,
        "synthetic": False,
        "requests": requests,
    }
    (partial / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


# ---------------------------------------------------------------- parsing


def first_stop(sequence: dict) -> str | None:
    for route in sequence.get("orderedLineRoutes") or []:
        if route.get("naptanIds"):
            return route["naptanIds"][0]
    return None


def parse_line_strings(sequence: dict) -> list[list[tuple[float, float]]]:
    """TfL ``lineStrings`` (JSON-encoded GeoJSON MultiLineString coords) -> [(lon, lat)]."""
    out = []
    for text in sequence.get("lineStrings") or []:
        coords = json.loads(text) if isinstance(text, str) else text
        # Each string is [[ [lon,lat], ... ]] (a list of polylines).
        if coords and isinstance(coords[0][0], (int, float)):
            coords = [coords]
        for line in coords:
            pts = [(float(p[0]), float(p[1])) for p in line]
            if len(pts) >= 2:
                out.append(pts)
    return out


def parse_route_sequence(sequence: dict) -> list[dict]:
    """Route variants of one line direction.

    Returns ``[{line, direction, name, service_type, stops:[{id, name, lon, lat}],
    polyline:[(lon, lat)]}]``; the polyline is the ``lineStrings`` entry closest to
    the variant's stops (empty when TfL gave no geometry).
    """
    coords: dict[str, dict] = {}
    for seq in sequence.get("stopPointSequences") or []:
        for stop in seq.get("stopPoint") or []:
            for key in {stop.get("id"), stop.get("stationId"), stop.get("naptanId")} - {None}:
                coords[key] = stop
    for station in sequence.get("stations") or []:
        coords.setdefault(station.get("id"), station)
    polylines = parse_line_strings(sequence)
    variants = []
    for route in sequence.get("orderedLineRoutes") or []:
        stops = []
        for nid in route.get("naptanIds") or []:
            stop = coords.get(nid)
            if stop is None or stop.get("lat") is None or stop.get("lon") is None:
                continue
            stops.append(
                {"id": nid, "name": stop.get("name"), "lon": stop["lon"], "lat": stop["lat"]}
            )
        best, best_score = [], math.inf
        for poly in polylines:
            score = _mean_stop_distance(stops, poly)
            if score < best_score:
                best, best_score = poly, score
        variants.append(
            {
                "line": sequence.get("lineId"),
                "direction": sequence.get("direction"),
                "name": route.get("name"),
                "service_type": route.get("serviceType"),
                "stops": stops,
                "polyline": best,
            }
        )
    return variants


def _mean_stop_distance(stops, poly) -> float:
    if not stops:
        return math.inf
    total = 0.0
    for s in stops:
        total += min((s["lon"] - x) ** 2 + (s["lat"] - y) ** 2 for x, y in poly)
    return total / len(stops)


def parse_headway(timetable: dict, schedule: str = "Monday to Friday", hour: int = 8) -> dict:
    """Headway (s) at ``hour`` from a TfL timetable response, or ``headway_s: None``.

    Uses the departures listed for that hour (``knownJourneys``) when present,
    otherwise the period frequency (minutes) covering that hour.
    """
    routes = (timetable.get("timetable") or {}).get("routes") or []
    schedules = [s for r in routes for s in r.get("schedules") or []]
    chosen = next((s for s in schedules if s.get("name") == schedule), None)
    chosen = chosen or (schedules[0] if schedules else None)
    if not chosen:
        return {"headway_s": None, "method": "no schedule"}
    journeys = [j for j in chosen.get("knownJourneys") or [] if int(j.get("hour", -1)) == hour]
    if journeys:
        return {
            "headway_s": 3600 / len(journeys),
            "method": f"{len(journeys)} departures {hour:02d}:00-{hour + 1:02d}:00",
            "schedule": chosen.get("name"),
        }
    for period in chosen.get("periods") or []:
        lo = period.get("fromTime", {}).get("hour")
        hi = period.get("toTime", {}).get("hour")
        freq = period.get("frequency") or {}
        if lo is None or hi is None or not freq:
            continue
        if int(lo) <= hour < int(hi) or (int(hi) < int(lo) and (hour >= int(lo) or hour < int(hi))):
            values = [freq.get(k) for k in ("lowestFrequency", "highestFrequency") if freq.get(k)]
            if values:
                return {
                    "headway_s": 60 * sum(values) / len(values),
                    "method": "period frequency",
                    "schedule": chosen.get("name"),
                }
    return {"headway_s": None, "method": "no frequency for hour", "schedule": chosen.get("name")}


def load_cache(cache_dir: Path) -> dict | None:
    """Provenance of a complete cache, or None when absent/incomplete."""
    path = cache_dir / "provenance.json"
    return json.loads(path.read_text()) if path.is_file() else None


def cache_digest(cache_dir: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(cache_dir.rglob("*.json")):
        h.update(str(path.relative_to(cache_dir)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- SUMO demand


def _densify(points, step: float):
    out = [points[0]]
    for a, b in itertools.pairwise(points):
        d = math.dist(a, b)
        n = int(d // step)
        out += [
            (a[0] + (b[0] - a[0]) * k / (n + 1), a[1] + (b[1] - a[1]) * k / (n + 1))
            for k in range(1, n + 1)
        ]
        out.append(b)
    return out


def _inside_runs(points, half):
    runs, current = [], []
    for p in points:
        if abs(p[0]) <= half and abs(p[1]) <= half:
            current.append(p)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _repair(net, edges, vclass):
    """Fill disconnected consecutive edges with shortest paths; keep the longest valid run."""
    if not edges:
        return []
    runs, current = [], [edges[0]]
    for nxt in edges[1:]:
        a, b = net.getEdge(current[-1]), net.getEdge(nxt)
        if b in a.getOutgoing():
            current.append(nxt)
            continue
        path, _ = net.getShortestPath(a, b, vClass=vclass)
        if path and len(path) <= 12:
            current += [e.getID() for e in path[1:]]
        else:
            runs.append(current)
            current = [nxt]
    runs.append(current)
    best = max(runs, key=lambda r: sum(net.getEdge(e).getLength() for e in r))
    deduped = [best[0]] + [e for p, e in itertools.pairwise(best) if e != p]
    return deduped


def build_sumo(
    cache_dir: Path, net_path: Path, out_dir: Path, scene: dict, cfg: dict, sim: dict, log=print
) -> dict:
    """Map-match cached TfL bus routes to the net; write busStops and flows."""
    sumolib = sumo_env.sumolib()
    from sumolib.route import mapTrace

    enu = Enu(scene["origin"]["longitude"], scene["origin"]["latitude"])
    half = scene["half_m"]
    net = sumolib.net.readNet(str(net_path))
    stops_xml, routes_xml, report = {}, [], {"lines": [], "skipped": []}
    dwell = cfg.get("dwell_s", 20)
    for path in sorted((cache_dir / "route_sequence").glob("*.json")):
        sequence = json.loads(path.read_text())
        variants = [v for v in parse_route_sequence(sequence) if v["polyline"]]
        regular = [v for v in variants if (v["service_type"] or "Regular") == "Regular"]
        if not (regular or variants):
            report["skipped"].append({"file": path.name, "reason": "no route geometry"})
            continue
        variant = (regular or variants)[0]
        line, direction = variant["line"] or path.stem, variant["direction"] or ""
        timetable = cache_dir / "timetable" / path.name
        headway = (
            parse_headway(
                json.loads(timetable.read_text()),
                cfg.get("schedule", "Monday to Friday"),
                int(cfg.get("hour", 8)),
            )
            if timetable.exists()
            else {"headway_s": None, "method": "no timetable cached"}
        )
        if headway["headway_s"] is None:
            if cfg.get("default_headway_s"):
                headway = {"headway_s": float(cfg["default_headway_s"]), "method": "assumed"}
            else:
                report["skipped"].append(
                    {"file": path.name, "reason": f"no frequency ({headway['method']})"}
                )
                continue
        trace_all = [enu(lon, lat) for lon, lat in variant["polyline"]]
        runs = _inside_runs(_densify(trace_all, 20.0), half - 5)
        if not runs:
            report["skipped"].append({"file": path.name, "reason": "route outside domain"})
            continue
        trace = max(runs, key=len)
        matched = list(mapTrace(trace, net, 25.0, vClass="bus", fillGaps=300))
        edges = _repair(net, [e.getID() if hasattr(e, "getID") else e for e in matched], "bus")
        if not edges or sum(net.getEdge(e).getLength() for e in edges) < 200:
            report["skipped"].append({"file": path.name, "reason": "map matching failed"})
            continue
        index = {e: i for i, e in enumerate(edges)}
        stops, last = [], (-1, -1.0)
        for stop in variant["stops"]:
            x, y = enu(stop["lon"], stop["lat"])
            if abs(x) > half or abs(y) > half:
                continue
            best = None
            for lane, dist in net.getNeighboringLanes(x, y, 30.0):
                edge = lane.getEdge().getID()
                if edge not in index or not lane.allows("bus") or lane.getLength() < 15:
                    continue
                pos = lane.getClosestLanePosAndDist((x, y))[0]
                key = (index[edge], pos)
                if key <= last:
                    continue
                cost = dist + 3.0 * lane.getIndex()  # prefer the kerbside lane
                if best is None or cost < best[0]:
                    best = (cost, lane, pos, key)
            if best is None:
                continue
            _, lane, pos, key = best
            last = key
            length = lane.getLength()
            start = min(max(0.0, pos - 10.0), length - 15.0)
            sid = f"tfl_{stop['id']}_{lane.getID()}"
            stops_xml[sid] = (
                f'    <busStop id="{sid}" lane="{lane.getID()}" startPos="{start:.2f}" '
                f'endPos="{start + 15.0:.2f}" name={quoteattr(stop.get("name") or stop["id"])} '
                f"lines={quoteattr(line)}/>\n"
            )
            stops.append(sid)
        rid = f"tfl_{line}_{direction}".replace(" ", "_")
        period = headway["headway_s"]
        offset = (int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 1000) / 1000 * period
        body = "".join(f'        <stop busStop="{s}" duration="{dwell}"/>\n' for s in stops)
        routes_xml.append(
            f'    <route id="{rid}" edges="{" ".join(edges)}">\n{body}    </route>\n'
            f'    <flow id="{rid}" type="bus" route="{rid}" line={quoteattr(line)} '
            f'begin="{sim["begin_s"] + offset:.1f}" end="{sim["end_s"]}" period="{period:.1f}"/>\n'
        )
        report["lines"].append(
            {
                "id": rid,
                "line": line,
                "direction": direction,
                "route": variant["name"],
                "edges": len(edges),
                "stops": len(stops),
                "headway_s": round(period, 1),
                "headway_method": headway["method"],
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    stops_path, routes_path = out_dir / "tfl_busstops.add.xml", out_dir / "tfl_buses.rou.xml"
    stops_path.write_text("<additional>\n" + "".join(stops_xml.values()) + "</additional>\n")
    routes_path.write_text("<routes>\n" + "".join(routes_xml) + "</routes>\n")
    log(f"TfL: {len(report['lines'])} line directions matched, {len(report['skipped'])} skipped")
    report["bus_stops"] = len(stops_xml)
    return {"additional": stops_path, "routes": routes_path, "report": report}
