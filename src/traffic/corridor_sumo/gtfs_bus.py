"""BODS GTFS bus timetables -> scene subset, stops, schedule metrics and SUMO buses.

Source: the DfT Bus Open Data Service (BODS) UK aggregate GTFS feed, as mirrored by the
Mobility Database (Open Government Licence v3.0). The feed's ``stop_id``/``stop_code``
are NaPTAN ATCO/SMS codes with real coordinates. Everything here is a *scheduled*
timetable: no real-time vehicle positions or passenger loads are used or implied.

  PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus download imperial_corridor
  PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus subset imperial_corridor
  PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus build imperial_corridor

``download`` streams the national zip (~1.3 GB) to ``cache/<scene>/traffic_sumo/
gtfs_download/``; ``subset`` streams it once (no extraction) and writes the domain
subset to ``project/<scene>/input/gtfs_bods/`` with ``index.json`` (provenance);
``build`` reads only that subset and the newest SUMO network and writes
``cache/<scene>/traffic_sumo/gtfs/`` (``stops.json``, ``schedule.json``,
``matching.json`` and per period ``bus_stops.add.xml``, ``buses.rou.xml``,
``trips.json``, ``period.json``). SUMO times are seconds after midnight of the
chosen service day, so a period run must use ``begin``/``end`` from ``period.json``.
"""

from __future__ import annotations

import argparse
import base64
import bisect
import csv
import gzip
import hashlib
import heapq
import io
import itertools
import json
import math
import statistics
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import quoteattr

from . import sumo_env
from .tfl import Enu

SIMULATION = "traffic_sumo"
SOURCE_URL = (
    "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/"
    "gb-unknown-uk-aggregate-feed-gtfs-2014.zip?alt=media"
)
LICENSE = "Open Government Licence v3.0 (Bus Open Data Service, Department for Transport)"
SOURCE = "DfT Bus Open Data Service (BODS) UK aggregate GTFS, Mobility Database mirror"
ZIP_NAME = "gb-unknown-uk-aggregate-feed-gtfs-2014.zip"
PERIODS = {"am_peak": [8, 9], "inter_peak": [13, 14], "pm_peak": [17, 18]}
HOURS = [5, 24]
# England and Wales bank holidays (gov.uk) over the feed's plausible validity.
BANK_HOLIDAYS = {
    "20260101", "20260403", "20260406", "20260504", "20260525", "20260831", "20261225",
    "20261228", "20270101", "20270326", "20270329", "20270503", "20270531", "20270830",
    "20271227", "20271228",
}  # fmt: skip
NATURE = {
    "stops_and_timetables": "BODS GTFS: real NaPTAN stop locations and real *scheduled* "
    "timetables (not real-time, not observed running times)",
    "delays_speeds_status": "SUMO model estimates (synthetic car/taxi demand), not observations",
    "unavailable": "no real-time vehicle positions (AVL/SIRI-VM) or passenger loads were used",
}


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# ---------------------------------------------------------------- small helpers


def is_bus_route_type(value) -> bool:
    """GTFS bus: basic type 3 or the extended 700-799 bus range."""
    try:
        t = int(value)
    except (TypeError, ValueError):
        return False
    return t == 3 or 700 <= t <= 799


def parse_time(text: str) -> int:
    """GTFS ``HH:MM:SS`` (hours may exceed 23) -> seconds after midnight."""
    h, m, s = (int(p) for p in text.strip().split(":"))
    return 3600 * h + 60 * m + s


def fmt_time(seconds: float) -> str:
    s = round(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def inside(x: float, y: float, half: float) -> bool:
    return abs(x) <= half and abs(y) <= half


def domain_stops(rows, enu: Enu, half: float) -> dict[str, dict]:
    """Stops (location_type 0/blank) and stations (1) inside the square domain.

    Parent stations of an inside stop are kept even when their own point lies outside.
    Each kept row gains ``x``/``y`` (scene ENU metres) and ``lat``/``lon`` floats.
    """
    by_id, kept = {}, {}
    for row in rows:
        if (row.get("location_type") or "0") not in ("0", "1"):
            continue
        try:
            lat, lon = float(row["stop_lat"]), float(row["stop_lon"])
        except (KeyError, ValueError):
            continue
        x, y = enu(lon, lat)
        rec = {**row, "lat": lat, "lon": lon, "x": x, "y": y}
        by_id[row["stop_id"]] = rec
        if inside(x, y, half):
            kept[row["stop_id"]] = rec
    for rec in list(kept.values()):
        parent = rec.get("parent_station")
        if parent and parent in by_id and parent not in kept:
            kept[parent] = by_id[parent]
    return kept


def _day(text: str) -> date:
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def active_services(day: str, calendar: list[dict], exceptions: list[dict]) -> set[str]:
    """Service ids running on ``day`` (YYYYMMDD) from calendar.txt + calendar_dates.txt."""
    weekday = _day(day).strftime("%A").lower()
    active = {
        r["service_id"]
        for r in calendar
        if r["start_date"] <= day <= r["end_date"] and r.get(weekday) == "1"
    }
    for r in exceptions:
        if r["date"] == day:
            if r["exception_type"] == "1":
                active.add(r["service_id"])
            elif r["exception_type"] == "2":
                active.discard(r["service_id"])
    return active


def choose_service_date(
    calendar: list[dict],
    exceptions: list[dict],
    trips_per_service: Counter,
    start: str,
    end: str,
    *,
    weekdays=(1, 2, 3),
    horizon_days: int = 42,
    holidays=BANK_HOLIDAYS,
) -> tuple[str, list[dict]]:
    """Representative weekday: a Tue-Thu (``weekdays``, Monday = 0) that is not a bank
    holiday, within ``horizon_days`` of the feed start, with the most scheduled trips
    (earliest on ties). Returns the date and the candidate scores."""
    first = _day(start)
    last = min(_day(end), first + timedelta(days=horizon_days))
    scores = []
    day = first
    while day <= last:
        key = day.strftime("%Y%m%d")
        if day.weekday() in weekdays and key not in holidays:
            services = active_services(key, calendar, exceptions)
            trips = sum(trips_per_service.get(s, 0) for s in services)
            scores.append({"date": key, "weekday": day.strftime("%A"), "trips": trips})
        day += timedelta(days=1)
    if not scores:
        raise ValueError(f"no Tue-Thu service day between {start} and {last}")
    best = max(scores, key=lambda s: (s["trips"], -int(s["date"])))
    return best["date"], scores


def clip_span(stop_ids: list[str], in_domain) -> tuple[int, int] | None:
    """Indices of the first and last stop inside the domain (None when none is)."""
    idx = [i for i, s in enumerate(stop_ids) if in_domain(s)]
    return (idx[0], idx[-1]) if idx else None


# ---------------------------------------------------------------- download


def download(target_dir: Path, url: str = SOURCE_URL, reuse: bool = True) -> dict:
    """Stream the feed zip into ``target_dir`` and write ``download.json`` (provenance).

    GCS stores the object gzip-encoded and publishes the md5 of the *stored* bytes.
    When the gzip bytes arrive undecoded their md5 is checked; when an intermediary has
    already decoded them (as the agent proxy does) the md5 cannot be checked and the
    zip's per-member CRC-32 test is the integrity check instead. Both are recorded.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path, info_path = target_dir / ZIP_NAME, target_dir / "download.json"
    if reuse and zip_path.is_file() and info_path.is_file():
        return json.loads(info_path.read_text())
    meta_url = url.split("?")[0]
    with urllib.request.urlopen(meta_url, timeout=60) as response:
        meta = json.loads(response.read())
    retrieved = datetime.now(UTC).isoformat()
    md5_check = "not verifiable: transfer gzip encoding was decoded before reaching us"
    if not (reuse and zip_path.is_file()):
        request = urllib.request.Request(media_url(meta, url), headers={"Accept-Encoding": "gzip"})
        partial = zip_path.with_suffix(".partial")
        md5 = hashlib.md5()  # matches the md5 GCS publishes for the stored bytes
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
            first = response.read(2)
            raw_gzip = first == b"\x1f\x8b"
            md5.update(first)
            if raw_gzip:  # decode ourselves after checking the stored bytes' md5
                tmp = partial.with_suffix(".gz")
                with tmp.open("wb") as gz:
                    gz.write(first)
                    while chunk := response.read(1 << 20):
                        md5.update(chunk)
                        gz.write(chunk)
                ok = base64.b64encode(md5.digest()).decode() == meta.get("md5Hash")
                md5_check = "match" if ok else "MISMATCH"
                if not ok:
                    raise RuntimeError(f"md5 mismatch for {url}")
                with gzip.open(tmp, "rb") as stream:
                    while chunk := stream.read(1 << 20):
                        out.write(chunk)
                tmp.unlink()
            else:
                out.write(first)
                while chunk := response.read(1 << 20):
                    out.write(chunk)
        partial.rename(zip_path)
    else:
        retrieved = datetime.fromtimestamp(zip_path.stat().st_mtime, UTC).isoformat()
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        members = {i.filename: i.file_size for i in z.infolist()}
    if bad is not None:
        raise RuntimeError(f"zip CRC check failed at {bad}")
    info = {
        "source": SOURCE,
        "url": url,
        "license": LICENSE,
        "retrieved_at": retrieved,
        "object_metadata": {
            k: meta.get(k)
            for k in (
                "name",
                "generation",
                "size",
                "md5Hash",
                "crc32c",
                "updated",
                "contentEncoding",
            )
        },
        "file": ZIP_NAME,
        "bytes": zip_path.stat().st_size,
        "sha256": sha256_file(zip_path),
        "md5_check": md5_check,
        "zip_crc_check": "all members pass",
        "members": members,
    }
    info_path.write_text(json.dumps(info, indent=2) + "\n")
    return info


def media_url(meta: dict, url: str) -> str:
    """Generation-pinned media link so the bytes match the recorded metadata."""
    return meta.get("mediaLink") or url


# ---------------------------------------------------------------- subset


def _rows(z: zipfile.ZipFile, name: str):
    with z.open(name) as handle:
        yield from csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig", newline=""))


def _write_csv(path: Path, fields: list[str], rows, compress: bool = False) -> int:
    opener = gzip.open if compress else open
    n = 0
    with opener(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            n += 1
    return n


def _iter_trip_groups(handle, header: list[str]):
    """Yield ``(trip_id, [raw lines])`` from a stop_times stream grouped by trip."""
    if header[:4] != ["trip_id", "arrival_time", "departure_time", "stop_id"]:
        raise ValueError(f"unexpected stop_times.txt header {header}")
    current, buf, done = None, [], set()
    for line in handle:
        tid = line.split(b",", 1)[0]
        if tid != current:
            if current is not None:
                yield current, buf
                done.add(current)
            if tid in done:
                raise ValueError("stop_times.txt is not grouped by trip_id")
            current, buf = tid, []
        buf.append(line)
    if current is not None:
        yield current, buf


def subset(zip_path: Path, out_dir: Path, enu: Enu, half: float, cfg: dict, download_info: dict):
    """Write the domain subset of the national feed (one streaming pass per big file)."""
    z = zipfile.ZipFile(zip_path)
    feed_info = next(_rows(z, "feed_info.txt"), {})
    log("reading stops, routes, agencies, calendars ...")
    stops = domain_stops(_rows(z, "stops.txt"), enu, half)
    routes = {
        r["route_id"]: r for r in _rows(z, "routes.txt") if is_bus_route_type(r["route_type"])
    }
    agencies = {r["agency_id"]: r for r in _rows(z, "agency.txt")}
    calendar = list(_rows(z, "calendar.txt"))
    exceptions = list(_rows(z, "calendar_dates.txt"))
    log("reading trips ...")
    trips, per_service = {}, Counter()
    for r in _rows(z, "trips.txt"):
        if r["route_id"] in routes:
            trips[r["trip_id"].encode()] = r
            per_service[r["service_id"]] += 1
    start = feed_info.get("feed_start_date") or min(r["start_date"] for r in calendar)
    end = feed_info.get("feed_end_date") or max(r["end_date"] for r in calendar)
    cal_end = max([r["end_date"] for r in calendar] + [r["date"] for r in exceptions])
    if cfg.get("service_date"):
        day, scores = str(cfg["service_date"]), []
    else:
        day, scores = choose_service_date(calendar, exceptions, per_service, start, end)
    services = active_services(day, calendar, exceptions)
    log(f"service date {day}: {len(services)} active services; {len(stops)} domain stops")

    platform = {s for s, r in stops.items() if (r.get("location_type") or "0") == "0"}
    platform_b = {s.encode() for s in platform}
    touched_routes: set[str] = set()
    kept: dict[str, list[dict]] = {}
    log("streaming stop_times.txt ...")
    with z.open("stop_times.txt") as handle:
        header = handle.readline().decode("utf-8-sig").strip().split(",")
        for n, (tid, lines) in enumerate(_iter_trip_groups(handle, header)):
            if n % 500000 == 0 and n:
                log(f"  {n} trips scanned, {len(kept)} kept")
            meta = trips.get(tid)
            if meta is None or not any(ln.split(b",", 4)[3] in platform_b for ln in lines):
                continue
            touched_routes.add(meta["route_id"])
            if meta["service_id"] not in services:
                continue
            text = b"".join(lines).decode("utf-8")
            rows = [dict(zip(header, r, strict=False)) for r in csv.reader(io.StringIO(text))]
            rows.sort(key=lambda r: int(r["stop_sequence"]))
            kept[tid.decode()] = rows
    log(f"{len(kept)} trips on {day} call at domain stops; {len(touched_routes)} routes any day")

    trip_rows, st_rows, shape_ids = [], [], set()
    for tid, rows in kept.items():
        meta = trips[tid.encode()]
        ids = [r["stop_id"] for r in rows]
        lo, hi = clip_span(ids, platform.__contains__)
        span = rows[lo : hi + 1]
        before = rows[lo - 1] if lo > 0 else None
        after = rows[hi + 1] if hi + 1 < len(rows) else None
        trip_rows.append(
            {
                **meta,
                "domain_entry_time": span[0]["arrival_time"] or span[0]["departure_time"],
                "domain_exit_time": span[-1]["departure_time"] or span[-1]["arrival_time"],
                "domain_first_sequence": span[0]["stop_sequence"],
                "domain_last_sequence": span[-1]["stop_sequence"],
                "prev_outside_stop": before["stop_id"] if before else "",
                "prev_outside_departure": before["departure_time"] if before else "",
                "next_outside_stop": after["stop_id"] if after else "",
                "next_outside_arrival": after["arrival_time"] if after else "",
                "trip_first_stop": rows[0]["stop_id"],
                "trip_last_stop": rows[-1]["stop_id"],
                "trip_start_time": rows[0]["departure_time"],
                "trip_end_time": rows[-1]["arrival_time"],
                "stops_total": len(rows),
            }
        )
        st_rows += span
        if meta.get("shape_id"):
            shape_ids.add(meta["shape_id"])

    shapes = _subset_shapes(z, shape_ids, enu, half) if shape_ids else {}
    log(f"{len(shapes)} of {len(shape_ids)} shapes intersect the domain")

    out_dir.mkdir(parents=True, exist_ok=True)
    used_routes = {routes[r]["route_id"] for r in touched_routes}
    active_routes = {t["route_id"] for t in trip_rows}
    route_rows = [
        {**routes[r], "active_on_service_date": int(r in active_routes)}
        for r in sorted(used_routes)
    ]
    agency_rows = [
        agencies[a] for a in sorted({r["agency_id"] for r in route_rows}) if a in agencies
    ]
    stop_fields = list(next(iter(stops.values())).keys())
    files = {
        "agency.txt": _write_csv(out_dir / "agency.txt", list(agency_rows[0]), agency_rows),
        "routes.txt": _write_csv(out_dir / "routes.txt", list(route_rows[0]), route_rows),
        "stops.txt": _write_csv(
            out_dir / "stops.txt", stop_fields, sorted(stops.values(), key=lambda s: s["stop_id"])
        ),
        "trips.txt": _write_csv(out_dir / "trips.txt", list(trip_rows[0]), trip_rows),
        "stop_times.txt.gz": _write_csv(
            out_dir / "stop_times.txt.gz", list(st_rows[0]), st_rows, compress=True
        ),
    }
    if shapes:
        shape_rows = [p for sid in sorted(shapes) for p in shapes[sid]]
        files["shapes.txt.gz"] = _write_csv(
            out_dir / "shapes.txt.gz", list(shape_rows[0]), shape_rows, compress=True
        )
    index = {
        "schema": "gtfs-bods-subset-v1",
        "source": SOURCE,
        "license": LICENSE,
        "attribution": "Contains public sector information licensed under the Open Government "
        "Licence v3.0 (Bus Open Data Service, Department for Transport)",
        "synthetic": False,
        "nature": NATURE["stops_and_timetables"],
        "download": download_info,
        "feed_info": feed_info,
        "feed_validity": {"feed_info": [start, end], "calendar_last_date": cal_end},
        "service_date": day,
        "service_date_selection": {
            "rule": "configured"
            if cfg.get("service_date")
            else "Tue-Thu within 6 weeks of "
            "feed start, not an England/Wales bank holiday, most scheduled bus trips "
            "nationally (earliest on ties)",
            "candidates": scores,
        },
        "domain": {
            "origin": {"longitude": enu.lon0, "latitude": enu.lat0},
            "half_m": half,
            "lonlat_bbox": [*enu.inverse(-half, -half), *enu.inverse(half, half)],
            "projection": "tfl.Enu tangent plane (same as fetch_overture)",
        },
        "filters": {
            "stops": "location_type 0/blank inside the domain, plus stations (1) and parents",
            "routes": "route_type 3 or 700-799 with >= 1 trip (any day) calling at a domain stop",
            "trips": "bus trips running on service_date calling at >= 1 domain stop; "
            "stop_times clipped to first..last domain stop (sequence and scheduled times kept); "
            "trips.txt adds domain entry/exit times and the neighbouring outside stops",
            "shapes": "points inside the domain plus one neighbour either side",
        },
        "counts": {
            "domain_stops": len(platform),
            "domain_stations": len(stops) - len(platform),
            "routes_any_day": len(route_rows),
            "routes_on_service_date": len(active_routes),
            "trips_on_service_date": len(trip_rows),
            "stop_times": len(st_rows),
            "shapes": len(shapes),
            "agencies": len(agency_rows),
        },
        "files": {
            name: {"rows": rows, "sha256": sha256_file(out_dir / name)}
            for name, rows in files.items()
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


def _subset_shapes(z: zipfile.ZipFile, wanted: set[str], enu: Enu, half: float) -> dict:
    wanted_b = {s.encode() for s in wanted}
    points: dict[str, list] = defaultdict(list)
    log("streaming shapes.txt ...")
    with z.open("shapes.txt") as handle:
        header = handle.readline().decode("utf-8-sig").strip().split(",")
        for line in handle:
            if line.split(b",", 1)[0] in wanted_b:
                points[line.split(b",", 1)[0].decode()].append(line.decode("utf-8").strip())
    out = {}
    for sid, lines in points.items():
        rows = [dict(zip(header, r, strict=False)) for r in csv.reader(lines)]
        rows.sort(key=lambda r: int(r["shape_pt_sequence"]))
        flags = [
            inside(*enu(float(r["shape_pt_lon"]), float(r["shape_pt_lat"])), half) for r in rows
        ]
        keep = [
            r
            for i, r in enumerate(rows)
            if flags[i] or (i > 0 and flags[i - 1]) or (i + 1 < len(rows) and flags[i + 1])
        ]
        if any(flags):
            out[sid] = keep
    return out


# ---------------------------------------------------------------- load subset


def _read_csv(path: Path) -> list[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_subset(directory: Path, enu: Enu) -> dict:
    """Subset tables keyed for the build step."""
    index = json.loads((directory / "index.json").read_text())
    stops = {}
    for r in _read_csv(directory / "stops.txt"):
        lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
        x, y = enu(lon, lat)
        stops[r["stop_id"]] = {**r, "lat": lat, "lon": lon, "x": x, "y": y}
    routes = {r["route_id"]: r for r in _read_csv(directory / "routes.txt")}
    agencies = {r["agency_id"]: r for r in _read_csv(directory / "agency.txt")}
    trips = {r["trip_id"]: r for r in _read_csv(directory / "trips.txt")}
    times = defaultdict(list)
    for r in _read_csv(directory / "stop_times.txt.gz"):
        times[r["trip_id"]].append(r)
    for rows in times.values():
        rows.sort(key=lambda r: int(r["stop_sequence"]))
    shapes = defaultdict(list)
    if (directory / "shapes.txt.gz").is_file():
        for r in _read_csv(directory / "shapes.txt.gz"):
            shapes[r["shape_id"]].append(
                (
                    int(r["shape_pt_sequence"]),
                    enu(float(r["shape_pt_lon"]), float(r["shape_pt_lat"])),
                )
            )
        shapes = {k: [p for _, p in sorted(v)] for k, v in shapes.items()}
    return dict(
        index=index, stops=stops, routes=routes, agencies=agencies, trips=trips, times=times,
        shapes=dict(shapes),
    )  # fmt: skip


def scheduled_trips(sub: dict) -> dict[str, list[dict]]:
    """Trips grouped by route-direction key ``<short name>|<direction_id>``.

    Each trip: ``{trip_id, route_id, key, shape_id, headsign, stops:[{stop, arr, dep,
    timepoint}], domain_runs}`` with the longest run of consecutive domain stops (a trip
    that leaves and re-enters the domain keeps its longest inside run; ``domain_runs``
    counts the runs).
    """
    platform = {s for s, r in sub["stops"].items() if (r.get("location_type") or "0") == "0"}
    groups = defaultdict(list)
    for tid, meta in sub["trips"].items():
        route = sub["routes"][meta["route_id"]]
        key = f"{route['route_short_name'] or route['route_id']}|{meta.get('direction_id') or '0'}"
        runs, stops = [], []
        for r in sub["times"].get(tid, []):
            if r["stop_id"] not in platform:
                if stops:
                    runs.append(stops)
                    stops = []
                continue
            arr = parse_time(r["arrival_time"] or r["departure_time"])
            dep = parse_time(r["departure_time"] or r["arrival_time"])
            stops.append(
                {"stop": r["stop_id"], "arr": arr, "dep": dep, "timepoint": r.get("timepoint")}
            )
        if stops:
            runs.append(stops)
        stops = max(runs, key=len) if runs else []
        if len(stops) < 2:
            continue
        groups[key].append(
            {
                "trip_id": tid,
                "route_id": meta["route_id"],
                "key": key,
                "shape_id": meta.get("shape_id") or "",
                "headsign": meta.get("trip_headsign") or "",
                "stops": stops,
                "domain_runs": len(runs),
            }
        )
    for trips in groups.values():
        trips.sort(key=lambda t: t["stops"][0]["dep"])
    return dict(groups)


# ---------------------------------------------------------------- geometry


def polyline_length(points) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))


def project_monotone(points, targets, max_jump_m: float = 60.0) -> list[tuple[float, float]]:
    """Project ``targets`` in order onto polyline ``points``; return ``(offset, dist)``.

    Offsets never decrease: each target is projected onto the segments at or after the
    previous projection, taking the first segment within ``max_jump_m`` that is a local
    minimum of distance (so a route passing the same place twice is handled in order).
    """
    cum = [0.0]
    for a, b in itertools.pairwise(points):
        cum.append(cum[-1] + math.dist(a, b))
    out, seg0 = [], 0
    for p in targets:
        best = None
        for i in range(seg0, len(points) - 1):
            off, d = _seg_project(points[i], points[i + 1], p)
            if best is None or d < best[2]:
                best = (i, cum[i] + off, d)
            elif best[2] <= max_jump_m and d > best[2] + max_jump_m:
                break  # left the neighbourhood of a good match
        if best is None:
            out.append((cum[-1] if cum else 0.0, math.inf))
            continue
        seg0 = best[0]
        out.append((max(best[1], out[-1][0] if out else 0.0), best[2]))
    return out


def _seg_project(a, b, p) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = (
        0.0
        if length2 == 0
        else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    )
    q = (a[0] + t * dx, a[1] + t * dy)
    return t * math.sqrt(length2), math.dist(p, q)


def simplify(points, tolerance: float = 5.0) -> list:
    """Douglas-Peucker polyline simplification (iterative)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = 0.0, None
        for k in range(i + 1, j):
            d = _seg_project(points[i], points[j], points[k])[1]
            if d > best:
                best, idx = d, k
        if idx is not None and best > tolerance:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [p for p, k in zip(points, keep, strict=True) if k]


# ---------------------------------------------------------------- schedule metrics


def windows(periods: dict = PERIODS, hours=HOURS) -> dict[str, tuple[int, int]]:
    out = {name: (3600 * a, 3600 * b) for name, (a, b) in periods.items()}
    out.update({f"h{h:02d}": (3600 * h, 3600 * (h + 1)) for h in range(hours[0], hours[1])})
    return out


def busiest_stop(trips: list[dict]) -> str | None:
    counts = Counter(s["stop"] for t in trips for s in t["stops"])
    return max(counts, key=lambda s: (counts[s], s)) if counts else None


def headways(times: list[float]) -> list[float]:
    ordered = sorted(times)
    return [b - a for a, b in itertools.pairwise(ordered)]


def runtime(trip: dict) -> int:
    return trip["stops"][-1]["arr"] - trip["stops"][0]["dep"]


def schedule_metrics(trips: list[dict], wins: dict, distance_of=None) -> dict:
    """Scheduled service per window for one route-direction.

    - ``trips_per_h``: departures at the route-direction's busiest stop (most calls over
      the day) within the window, per hour; ``headway_min`` = 60 / trips_per_h.
    - ``headway_busiest_stop_min``: mean gap between consecutive departures there (>= 2).
    - ``runtime_min``: median scheduled time from the first to the last domain stop over
      trips entering the domain in the window; ``speed_kmh``: median of distance/runtime
      with ``distance_of(trip)`` metres (stop-to-stop along the shape or SUMO path), or
      ``(metres, seconds)`` when only part of the trip (its matched stops) is measured.
    """
    stop = busiest_stop(trips)
    deps = sorted(s["dep"] for t in trips for s in t["stops"] if s["stop"] == stop)
    out = {}
    for name, (t0, t1) in wins.items():
        hours = (t1 - t0) / 3600
        lo, hi = bisect.bisect_left(deps, t0), bisect.bisect_left(deps, t1)
        inwin = deps[lo:hi]
        entering = [t for t in trips if t0 <= t["stops"][0]["dep"] < t1]
        rec = {
            "trips_per_h": round(len(inwin) / hours, 2),
            "trips_in_domain": sum(
                1 for t in trips if t["stops"][0]["dep"] < t1 and t["stops"][-1]["arr"] >= t0
            ),
        }
        if not inwin and not entering:
            out[name] = rec
            continue
        if inwin:
            rec["headway_min"] = round(60 / (len(inwin) / hours), 2)
        gaps = headways(inwin)
        if gaps:
            rec["headway_busiest_stop_min"] = round(statistics.fmean(gaps) / 60, 2)
            rec["headway_max_min"] = round(max(gaps) / 60, 2)
        runtimes = [runtime(t) for t in entering]
        runtimes = [r for r in runtimes if r > 0]
        if runtimes:
            rec["runtime_min"] = round(statistics.median(runtimes) / 60, 2)
        if distance_of is not None:
            speeds, dists = [], []
            for t in entering:
                d = distance_of(t)
                if d is None:
                    continue
                dist, rt = d if isinstance(d, tuple) else (d, runtime(t))
                if rt > 0 and dist > 0:
                    speeds.append(dist / rt * 3.6)
                    dists.append(dist)
            if speeds:
                rec["speed_kmh"] = round(statistics.median(speeds), 2)
                rec["distance_km"] = round(statistics.median(dists) / 1000, 3)
        out[name] = rec
    return {"busiest_stop": stop, "windows": out}


# ---------------------------------------------------------------- SUMO matching


class Matcher:
    """Map stop sequences onto a SUMO net: HMM/Viterbi over candidate kerbside lanes.

    Candidates of a stop are the lowest-index bus lane of each edge within ``radius``
    (lane 0 is the kerb lane; the net is left-hand drive, so a stop on the right of the
    lane direction is penalised). Transitions are bus-permitted shortest paths whose
    length is compared with the stop-to-stop distance along the GTFS shape (or, with no
    shape, with the straight-line distance). Up to ``max_skip`` consecutive unmatched
    stops may be skipped at a cost each, so a stop off the network does not break a route.
    """

    def __init__(self, net, *, radius=40.0, candidates=6, max_skip=2, skip_cost=250.0):
        self.net, self.radius, self.k = net, radius, candidates
        self.max_skip, self.skip_cost = max_skip, skip_cost
        self._cand: dict[str, list] = {}
        self._out: dict = {}

    def candidates(self, sid: str, x: float, y: float) -> list[dict]:
        if sid in self._cand:
            return self._cand[sid]
        found: dict = {}
        for lane, dist in self.net.getNeighboringLanes(x, y, self.radius):
            edge = lane.getEdge()
            if edge.getFunction() or not lane.allows("bus") or edge.getID() in found:
                continue
            lanes = [ln for ln in edge.getLanes() if ln.allows("bus")]
            kerb = lanes[0]
            pos, d = kerb.getClosestLanePosAndDist((x, y))
            side = _side(kerb, pos, (x, y))
            cost = 2.0 * d + (25.0 if side < -1.0 else 0.0)  # left-hand: stop on the left
            found[edge.getID()] = {"edge": edge, "lane": kerb, "pos": pos, "dist": d, "cost": cost}
        best = sorted(found.values(), key=lambda c: c["cost"])[: self.k]
        self._cand[sid] = best
        return best

    def _outgoing(self, edge):
        """Bus-permitted successors with the junction gap (edge end to successor start;
        internal junction lanes are not loaded, so this stands in for their length)."""
        out = self._out.get(edge)
        if out is None:
            end = edge.getShape()[-1]
            out = [
                (e, math.dist(end, e.getShape()[0]))
                for e in edge.getAllowedOutgoing("bus")
                if not e.getFunction()
            ]
            self._out[edge] = out
        return out

    def gap(self, a, b) -> float:
        return next((g for e, g in self._outgoing(a) if e is b), 0.0)

    def distances(self, src: dict, targets: dict, bound: float) -> dict:
        """Driving distance from ``src`` (lane pos) to each target edge's lane pos."""
        start = src["edge"]
        res, pred = {}, {start: None}
        for tid, t in targets.items():
            if t["edge"] is start and t["pos"] >= src["pos"] - 1.0:
                res[tid] = (max(0.0, t["pos"] - src["pos"]), [start])
        base = start.getLength() - src["pos"]
        heap, seen, counter = [(base, 0, start)], set(), itertools.count(1)
        best = {start: base}
        by_edge = defaultdict(list)
        for tid, t in targets.items():
            by_edge[t["edge"]].append(tid)
        while heap:
            d, _, edge = heapq.heappop(heap)
            if edge in seen or d > bound:
                continue
            seen.add(edge)
            for nxt, gap in self._outgoing(edge):
                for tid in by_edge.get(nxt, ()):
                    total = d + gap + targets[tid]["pos"]
                    if tid not in res or total < res[tid][0]:
                        path, e = [nxt], edge
                        while e is not None:
                            path.append(e)
                            e = pred[e]
                        res[tid] = (total, path[::-1])
                nd = d + gap + nxt.getLength()
                if nxt not in seen and nd < best.get(nxt, math.inf):
                    best[nxt], pred[nxt] = nd, edge
                    heapq.heappush(heap, (nd, next(counter), nxt))
        return res

    def match(self, stops: list[dict], ref: list[float] | None) -> dict:
        """``stops``: [{stop, x, y}]; ``ref``: cumulative distance along the shape per stop.

        Returns ``{edges, stops:[{index, stop, lane, pos, dist}], path_length,
        ref_length, matched_share}`` (``edges`` empty when nothing could be matched).
        """
        n = len(stops)
        all_cands = [self.candidates(s["stop"], s["x"], s["y"]) for s in stops]
        # Stops with no bus lane within the radius (e.g. off the network) are unmatched
        # outright and do not use up the skip allowance; DP runs over the others.
        idx = [i for i in range(n) if all_cands[i]]
        cands = [all_cands[i] for i in idx]
        nq = len(idx)

        def want(i0: int, i1: int) -> float:
            if ref is not None:
                return ref[i1] - ref[i0]
            return sum(
                math.dist((stops[a]["x"], stops[a]["y"]), (stops[a + 1]["x"], stops[a + 1]["y"]))
                for a in range(i0, i1)
            )

        INF = math.inf
        cost = [[INF] * len(c) for c in cands]
        back: list[list] = [[None] * len(c) for c in cands]
        for q in range(min(nq, self.max_skip + 1)):
            for j, c in enumerate(cands[q]):
                cost[q][j] = c["cost"] + self.skip_cost * q
        for q in range(nq):
            for j, c in enumerate(cands[q]):
                if cost[q][j] == INF:
                    continue
                targets, refs = {}, {}
                for k in range(q + 1, min(nq, q + self.max_skip + 2)):
                    w = want(idx[q], idx[k])
                    for m, t in enumerate(cands[k]):
                        targets[(k, m)] = t
                        refs[(k, m)] = w
                if not targets:
                    continue
                bound = 2.5 * max(refs.values()) + 600.0
                for (k, m), (d, path) in self.distances(c, targets, bound).items():
                    w = refs[(k, m)]
                    trans = abs(d - w) if ref is not None else max(0.0, d - w)
                    total = cost[q][j] + trans + cands[k][m]["cost"] + self.skip_cost * (k - q - 1)
                    if total < cost[k][m]:
                        cost[k][m] = total
                        back[k][m] = (q, j, d, path)
        end = None
        for q in range(nq - 1, max(-1, nq - self.max_skip - 2), -1):
            for j in range(len(cands[q])):
                total = cost[q][j] + self.skip_cost * (nq - 1 - q)
                if total < INF and (end is None or total < end[0]):
                    end = (total, q, j)
        if end is None:
            return {"edges": [], "stops": [], "matched_share": 0.0}
        chain, q, j = [], end[1], end[2]
        while True:
            chain.append((q, j, back[q][j]))
            if back[q][j] is None:
                break
            q, j = back[q][j][0], back[q][j][1]
        chain.reverse()
        edges, placed, length = [], [], 0.0
        for q, j, link in chain:
            c, i = cands[q][j], idx[q]
            if link is None:
                edges = [c["edge"]]
            else:
                length += link[2]
                edges += link[3][1:]
            placed.append(
                {
                    "index": i,
                    "stop": stops[i]["stop"],
                    "lane": c["lane"],
                    "pos": c["pos"],
                    "dist": c["dist"],
                }
            )
        first, last = placed[0]["index"], placed[-1]["index"]
        return {
            "edges": [e.getID() for e in edges],
            "stops": placed,
            "path_length": length,
            "ref_length": (ref[last] - ref[first]) if ref is not None else None,
            "matched_share": len(placed) / n,
            "cost": end[0],
        }


def _side(lane, pos: float, p) -> float:
    """Signed lateral offset of ``p`` from ``lane`` (+ = left of the driving direction)."""
    shape = lane.getShape()
    acc = 0.0
    for a, b in itertools.pairwise(shape):
        seg = math.dist(a, b)
        if acc + seg >= pos or b == shape[-1]:
            dx, dy = b[0] - a[0], b[1] - a[1]
            norm = math.hypot(dx, dy) or 1.0
            return (dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / norm
        acc += seg
    return 0.0


def latest_net(cache_root: Path) -> Path:
    nets = sorted(cache_root.glob("*/net/net.net.xml"), key=lambda p: p.stat().st_mtime)
    if not nets:
        raise FileNotFoundError(f"no SUMO network under {cache_root}/*/net/; run run.py first")
    return nets[-1]


# ---------------------------------------------------------------- build


def build(sub: dict, net_path: Path, out_dir: Path, cfg: dict) -> dict:
    """Stops, schedule metrics, matching and per-period SUMO files into ``out_dir``."""
    sumolib = sumo_env.sumolib()
    log(f"reading {net_path} ...")
    net = sumolib.net.readNet(str(net_path))
    groups = scheduled_trips(sub)
    stops = sub["stops"]
    periods = cfg.get("periods", PERIODS)
    wins = windows(periods, cfg.get("hours", HOURS))
    matcher = Matcher(
        net,
        radius=cfg.get("stop_snap_m", 40.0),
        max_skip=cfg.get("max_skipped_stops", 2),
    )

    # Distinct stop patterns per route-direction (with the most common shape).
    patterns: dict[tuple, dict] = {}
    for key, trips in groups.items():
        for t in trips:
            pid = (key, tuple(s["stop"] for s in t["stops"]))
            pat = patterns.setdefault(
                pid, {"key": key, "stops": pid[1], "trips": [], "shapes": Counter()}
            )
            pat["trips"].append(t)
            if t["shape_id"]:
                pat["shapes"][t["shape_id"]] += 1
    log(f"{len(groups)} route-directions, {len(patterns)} stop patterns; map matching ...")

    match_report = defaultdict(lambda: {"patterns": 0, "trips": 0, "stops": 0, "matched": 0})
    for n, (pid, pat) in enumerate(sorted(patterns.items(), key=lambda kv: kv[0])):
        pts = [{"stop": s, "x": stops[s]["x"], "y": stops[s]["y"]} for s in pat["stops"]]
        shape = sub["shapes"].get(pat["shapes"].most_common(1)[0][0]) if pat["shapes"] else None
        ref = None
        if shape and len(shape) >= 2:
            proj = project_monotone(shape, [(p["x"], p["y"]) for p in pts])
            if max(d for _, d in proj) <= 75.0:
                ref = [o for o, _ in proj]
        pat["ref"] = ref
        pat["shape"] = shape
        pat["match"] = matcher.match(pts, ref)
        if n % 50 == 0:
            log(f"  {n}/{len(patterns)} patterns")
        rep = match_report[pat["key"]]
        weight = len(pat["trips"])
        rep["patterns"] += 1
        rep["trips"] += weight
        rep["stops"] += weight * len(pts)
        rep["matched"] += weight * len(pat["match"]["stops"])
        m = pat["match"]
        if m["edges"] and m.get("ref_length"):
            rep.setdefault("_ratio", []).append(
                (weight, m["path_length"] / max(1.0, m["ref_length"]))
            )
        if len(m["stops"]) >= 2:
            i0, i1 = m["stops"][0]["index"], m["stops"][-1]["index"]
            crow = sum(
                math.dist((pts[a]["x"], pts[a]["y"]), (pts[a + 1]["x"], pts[a + 1]["y"]))
                for a in range(i0, i1)
            )
            m["crowfly_length"] = crow
            if crow > 0:
                rep.setdefault("_crow", []).append((weight, m["path_length"] / crow))

    # Distance per pattern for scheduled speeds: along the shape, else the SUMO path.
    # Partially matched patterns are measured between their first and last matched stop.
    def distance_of(trip):
        pat = patterns[(trip["key"], tuple(s["stop"] for s in trip["stops"]))]
        if pat["ref"] is not None:
            return pat["ref"][-1] - pat["ref"][0]
        m = pat["match"]
        if len(m["stops"]) < 2:
            return None
        i0, i1 = m["stops"][0]["index"], m["stops"][-1]["index"]
        return m["path_length"], trip["stops"][i1]["arr"] - trip["stops"][i0]["dep"]

    route_names = {k: k.split("|")[0] for k in groups}
    serving = defaultdict(set)
    for key, trips in groups.items():
        for t in trips:
            for s in t["stops"]:
                serving[s["stop"]].add(route_names[key])

    # busStops: one per (ATCO stop, lane); overlapping stops on a lane share the first.
    bus_stops: dict[tuple, dict] = {}
    by_lane = defaultdict(list)
    for pat in patterns.values():
        for p in pat["match"]["stops"]:
            k = (p["stop"], p["lane"].getID())
            if k in bus_stops:
                p["bus_stop"] = bus_stops[k]["id"]
                bus_stops[k]["lines"].add(route_names[pat["key"]])
                continue
            length = min(20.0, p["lane"].getLength())
            start = min(max(0.0, p["pos"] - length / 2), p["lane"].getLength() - length)
            clash = next(
                (b for b in by_lane[k[1]] if start < b["end"] and b["start"] < start + length), None
            )
            if clash is not None:
                p["bus_stop"] = clash["id"]
                bus_stops[k] = clash
                clash["lines"].add(route_names[pat["key"]])
                clash["shared"].add(p["stop"])
                continue
            n_same = sum(1 for kk in bus_stops if kk[0] == p["stop"])
            sid = p["stop"] if n_same == 0 else f"{p['stop']}#{n_same + 1}"
            rec = {
                "id": sid,
                "atco": p["stop"],
                "lane": k[1],
                "start": start,
                "end": start + length,
                "lines": {route_names[pat["key"]]},
                "shared": set(),
            }
            bus_stops[k] = rec
            by_lane[k[1]].append(rec)
            p["bus_stop"] = sid

    # Route summaries and schedule metrics.
    route_out = []
    for key, trips in sorted(groups.items()):
        main = max((p for p in patterns.values() if p["key"] == key), key=lambda p: len(p["trips"]))
        rid = trips[0]["route_id"]
        route = sub["routes"][rid]
        agency = sub["agencies"].get(route.get("agency_id"), {}).get("agency_name")
        m = main["match"]
        if m["edges"]:
            path = []
            for e in m["edges"]:
                shape = net.getEdge(e).getShape()
                path += shape if not path else shape[1:]
            path_src = "sumo_path"
        elif main["shape"]:
            path, path_src = main["shape"], "gtfs_shape"
        else:
            path = [(stops[s]["x"], stops[s]["y"]) for s in main["stops"]]
            path_src = "stop_sequence"
        rep = match_report[key]
        ratios = rep.pop("_ratio", [])
        rep["matched_share"] = round(rep["matched"] / rep["stops"], 4) if rep["stops"] else 0.0
        if ratios:
            rep["path_vs_shape_length"] = round(
                sum(w * r for w, r in ratios) / sum(w for w, _ in ratios), 3
            )
        crow = rep.pop("_crow", [])
        if crow:
            rep["path_vs_crowfly_stop_chain"] = round(
                sum(w * r for w, r in crow) / sum(w for w, _ in crow), 3
            )
        metrics = schedule_metrics(trips, wins, distance_of)
        route_out.append(
            {
                "key": key,
                "route": route_names[key],
                "route_id": rid,
                "direction": key.split("|")[1],
                "agency": agency,
                "headsign": Counter(t["headsign"] for t in trips).most_common(1)[0][0],
                "trips_on_day": len(trips),
                "stops": list(main["stops"]),
                "path": [[round(x, 1), round(y, 1)] for x, y in simplify(path, 5.0)],
                "path_source": path_src,
                "busiest_stop": metrics["busiest_stop"],
                "schedule": metrics["windows"],
                "matching": rep,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    stop_list = []
    for sid, s in sorted(stops.items()):
        rec = {
            "id": sid,
            "code": s.get("stop_code") or None,
            "name": s.get("stop_name"),
            "x": round(s["x"], 2),
            "y": round(s["y"], 2),
            "lat": round(s["lat"], 7),
            "lon": round(s["lon"], 7),
            "routes": sorted(serving.get(sid, ()), key=_route_sort),
        }
        if s.get("parent_station"):
            rec["parent"] = s["parent_station"]
        if s.get("location_type") == "1":
            rec["station"] = True
        stop_list.append(rec)
    provenance = provenance_block(sub["index"], net_path)
    (out_dir / "stops.json").write_text(json.dumps(stop_list, separators=(",", ":")) + "\n")
    schedule = {
        "schema": "corridor-bus-schedule-v1",
        "service_date": sub["index"]["service_date"],
        "periods": periods,
        "hours": cfg.get("hours", HOURS),
        "routes": route_out,
        "stop_buses_per_h": stop_buses_per_hour(groups, wins),
        "definitions": schedule_metrics.__doc__,
        "provenance": provenance,
    }
    (out_dir / "schedule.json").write_text(json.dumps(schedule, separators=(",", ":")) + "\n")

    # Per-period SUMO files.
    warm = 60 * cfg.get("warmup_min", 20)
    dwell = cfg.get("dwell_s", 20)
    hold = cfg.get("hold_at", "all")
    period_info = {}
    for name, (h0, h1) in periods.items():
        t0, t1 = 3600 * h0, 3600 * h1
        begin = t0 - warm
        pdir = out_dir / name
        pdir.mkdir(exist_ok=True)
        vehicles, used = [], set()
        trips_json = {}
        for pat in patterns.values():
            m = pat["match"]
            if not m["edges"] or len(m["stops"]) < 2:
                continue
            edge_index = _stop_edge_index(m)
            cum = [0.0]  # route distance to the start of each edge
            for e, f in itertools.pairwise(m["edges"]):
                ea, eb = net.getEdge(e), net.getEdge(f)
                cum.append(cum[-1] + ea.getLength() + matcher.gap(ea, eb))
            for t in pat["trips"]:
                if t["stops"][0]["dep"] > t1 or t["stops"][-1]["arr"] < begin:
                    continue
                calls = []
                for p, e_idx in zip(m["stops"], edge_index, strict=True):
                    s = t["stops"][p["index"]]
                    if s["arr"] < begin:
                        continue
                    if calls and calls[-1]["bus_stop"] == p["bus_stop"]:
                        calls[-1]["dep"] = s["dep"]
                        continue
                    calls.append(
                        {
                            **s,
                            "bus_stop": p["bus_stop"],
                            "edge_index": e_idx,
                            "offset": cum[e_idx] + p["pos"],
                        }
                    )
                if len(calls) < 2 or calls[0]["arr"] >= t1:
                    continue
                vid = f"bus_{route_names[pat['key']]}_{pat['key'].split('|')[1]}_{t['trip_id']}"
                vid = vid.replace(" ", "_")
                edges = m["edges"][calls[0]["edge_index"] :]
                stops_xml = ""
                for c in calls:
                    until = (
                        f' until="{c["dep"]}"'
                        if hold == "all" or (hold == "timepoints" and c.get("timepoint") == "1")
                        else ""
                    )
                    stops_xml += (
                        f'        <stop busStop="{c["bus_stop"]}" arrival="{c["arr"]}" '
                        f'duration="{dwell}"{until}/>\n'
                    )
                used.update(c["bus_stop"] for c in calls)
                depart = calls[0]["arr"]
                vehicles.append(
                    (
                        depart,
                        (
                            f'    <vehicle id={quoteattr(vid)} type="bus" depart="{depart}" '
                            f'line={quoteattr(route_names[pat["key"]])} departPos="stop" '
                            f'departLane="best">\n'
                            f'        <route edges="{" ".join(edges)}"/>\n{stops_xml}'
                            "    </vehicle>\n"
                        ),
                    )
                )
                trips_json[vid] = {
                    "trip_id": t["trip_id"],
                    "key": pat["key"],
                    # [ATCO, busStop, scheduled arrival, scheduled departure, metres along
                    # the vehicle's SUMO route from its first stop]
                    "stops": [
                        [
                            c["stop"],
                            c["bus_stop"],
                            c["arr"],
                            c["dep"],
                            round(c["offset"] - calls[0]["offset"], 1),
                        ]
                        for c in calls
                    ],
                }
        vehicles.sort(key=lambda v: v[0])
        lines = ["<additional>\n"]
        unique = {rec["id"]: rec for rec in bus_stops.values()}  # shared records once
        for rec in sorted(unique.values(), key=lambda r: r["id"]):
            if rec["id"] not in used:
                continue
            nm = f"{rec['atco']} {stops[rec['atco']].get('stop_name') or ''}".strip()
            lines.append(
                f'    <busStop id={quoteattr(rec["id"])} lane="{rec["lane"]}" '
                f'startPos="{rec["start"]:.2f}" endPos="{rec["end"]:.2f}" name={quoteattr(nm)} '
                f"lines={quoteattr(' '.join(sorted(rec['lines'], key=_route_sort)))}/>\n"
            )
        lines.append("</additional>\n")
        (pdir / "bus_stops.add.xml").write_text("".join(lines))
        (pdir / "buses.rou.xml").write_text(
            "<routes>\n    <!-- BODS GTFS scheduled trips; vType 'bus' comes from "
            "demand.write_vtypes -->\n" + "".join(v for _, v in vehicles) + "</routes>\n"
        )
        info = {
            "period": name,
            "window_s": [t0, t1],
            "begin_s": begin,
            "end_s": t1,
            "record_from_s": t0,
            "time_base": f"seconds after midnight of {sub['index']['service_date']}",
            "vehicles": len(vehicles),
            "bus_stops": len(used),
            "dwell_s": dwell,
            "hold_at": hold,
            "requires_vtype": "bus (demand.write_vtypes)",
        }
        (pdir / "period.json").write_text(json.dumps(info, indent=2) + "\n")
        (pdir / "trips.json").write_text(
            json.dumps({"period": info, "vehicles": trips_json}, separators=(",", ":")) + "\n"
        )
        period_info[name] = info
        log(f"{name}: {len(vehicles)} buses, {len(used)} busStops -> {pdir}")

    matching = {
        "method": Matcher.__doc__,
        "net": str(net_path),
        "net_sha256": sha256_file(net_path),
        "routes": {r["key"]: r["matching"] for r in route_out},
        "patterns": [
            {
                "key": p["key"],
                "trips": len(p["trips"]),
                "stops": len(p["stops"]),
                "matched": len(p["match"]["stops"]),
                "path_length_m": round(p["match"].get("path_length") or 0, 1),
                "crowfly_stop_chain_m": round(p["match"].get("crowfly_length") or 0, 1),
                "shape_length_m": round(p["match"]["ref_length"], 1)
                if p["match"].get("ref_length")
                else None,
                "unmatched_stops": sorted(
                    set(p["stops"]) - {s["stop"] for s in p["match"]["stops"]}
                ),
            }
            for p in patterns.values()
        ],
    }
    (out_dir / "matching.json").write_text(json.dumps(matching, indent=1) + "\n")
    return {"routes": route_out, "periods": period_info, "matching": matching}


def stop_buses_per_hour(groups: dict, wins: dict) -> dict:
    """Scheduled departures per hour at each stop (all routes) per window."""
    deps = defaultdict(list)
    for trips in groups.values():
        for t in trips:
            for s in t["stops"]:
                deps[s["stop"]].append(s["dep"])
    out = {}
    for stop, times in deps.items():
        times.sort()
        rec = {}
        for name, (t0, t1) in wins.items():
            n = bisect.bisect_left(times, t1) - bisect.bisect_left(times, t0)
            if n:
                rec[name] = round(n / ((t1 - t0) / 3600), 2)
        out[stop] = rec
    return out


def _stop_edge_index(match: dict) -> list[int]:
    """Index into ``match['edges']`` of each placed stop's edge (in route order)."""
    out, i = [], 0
    edges = match["edges"]
    for p in match["stops"]:
        eid = p["lane"].getEdge().getID()
        while i < len(edges) and edges[i] != eid:
            i += 1
        if i == len(edges):
            raise ValueError(f"stop {p['stop']} edge {eid} not on its matched route")
        out.append(i)
    return out


def _route_sort(name: str):
    digits = "".join(itertools.takewhile(str.isdigit, name))
    return (0, int(digits), name) if digits else (1, 0, name)


def provenance_block(index: dict, net_path: Path | None = None) -> dict:
    out = {
        "nature": NATURE,
        "source": index.get("source"),
        "license": index.get("license"),
        "attribution": index.get("attribution"),
        "url": index.get("download", {}).get("url"),
        "retrieved_at": index.get("download", {}).get("retrieved_at"),
        "feed_sha256": index.get("download", {}).get("sha256"),
        "feed_version": index.get("feed_info", {}).get("feed_version"),
        "service_date": index.get("service_date"),
        "subset_files": index.get("files"),
        "synthetic": False,
    }
    if net_path is not None:
        out["sumo_net"] = str(net_path)
    return out


# ---------------------------------------------------------------- validation


def validate(net_path: Path, period_dir: Path, out_dir: Path) -> dict:
    """Buses-only SUMO run of one period: do the files load, are routes connected and
    stops reached? Writes ``stopinfos.xml``, ``tripinfos.xml`` and ``validation.json``."""
    from . import demand, simulate

    info = json.loads((period_dir / "period.json").read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    vtypes = demand.write_vtypes(out_dir)
    cmd = [
        sumo_env.binary("sumo"), "-n", net_path, "-a",
        f"{vtypes},{period_dir / 'bus_stops.add.xml'}", "-r", period_dir / "buses.rou.xml",
        "-b", info["begin_s"], "-e", info["end_s"], "--time-to-teleport", 120,
        "--ignore-route-errors", "true", "--no-step-log", "true",
        "--stop-output", out_dir / "stopinfos.xml",
        "--tripinfo-output", out_dir / "tripinfos.xml",
        "--statistic-output", out_dir / "statistics.xml",
        "--duration-log.statistics", "true",
    ]  # fmt: skip
    log_path = out_dir / "sumo.log"
    log_path.unlink(missing_ok=True)
    sumo_env.run(cmd, log=log_path)
    text = log_path.read_text()
    warnings = [ln for ln in text.splitlines() if ln.startswith(("Warning", "Error"))]
    kinds = Counter(
        "teleport" if "teleport" in ln.lower() else ln.split(";")[0].split("'")[0][:60]
        for ln in warnings
    )
    trips = json.loads((period_dir / "trips.json").read_text())["vehicles"]
    observed = Counter()
    root_stops = 0
    for _, el in ET.iterparse(out_dir / "stopinfos.xml"):
        if el.tag == "stopinfo":
            observed[el.get("id")] += 1
            root_stops += 1
            el.clear()
    expected = {v: len(t["stops"]) for v, t in trips.items()}
    due = {  # stops whose scheduled arrival falls before the end of the run
        v: sum(1 for c in t["stops"] if c[2] <= info["end_s"] - 600) for v, t in trips.items()
    }
    result = {
        "period": info["period"],
        "net": str(net_path),
        "vehicles": len(trips),
        "statistics": simulate.read_statistics(out_dir / "statistics.xml"),
        "stops_expected": sum(expected.values()),
        "stops_due_10min_before_end": sum(due.values()),
        "stops_reached": root_stops,
        "stops_reached_share_of_due": round(
            sum(min(observed[v], due[v]) for v in due) / max(1, sum(due.values())), 4
        ),
        "vehicles_without_any_stop": sum(1 for v in trips if observed[v] == 0),
        "warnings": dict(kinds.most_common(20)),
    }
    (out_dir / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


# ---------------------------------------------------------------- CLI


def scene_context(scene: str):
    from common.storage import Storage

    storage = Storage.load()
    meta = storage.metadata(scene)
    cfg = json.loads((meta / "configs/traffic_sumo.json").read_text())
    geo = json.loads(
        (meta / cfg.get("geometry_config", "configs/image_to_threejs.json")).read_text()
    )
    enu = Enu(geo["origin"]["longitude"], geo["origin"]["latitude"])
    gcfg = cfg.get("gtfs", {})
    paths = {
        "download": storage.scratch(cfg["scene_id"], SIMULATION, "gtfs_download"),
        "subset": storage.assets(cfg["scene_id"], "input") / gcfg.get("input_dir", "gtfs_bods"),
        "out": storage.scratch(cfg["scene_id"], SIMULATION, gcfg.get("output_dir", "gtfs")),
        "runs": storage.cache_root / cfg["scene_id"] / SIMULATION,
    }
    return cfg, gcfg, enu, geo["domain_m"] / 2, paths


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("command", choices=["download", "subset", "build", "all", "validate"])
    p.add_argument("scene")
    p.add_argument("--zip", type=Path, help="local feed zip (default: the download cache)")
    p.add_argument("--net", type=Path, help="SUMO net (default: newest run's net.net.xml)")
    p.add_argument("--date", help="service date YYYYMMDD (default: config or automatic)")
    p.add_argument("--period", action="append", help="validate: period(s) (default: all)")
    args = p.parse_args(argv)
    _cfg, gcfg, enu, half, paths = scene_context(args.scene)
    if args.date:
        gcfg = {**gcfg, "service_date": args.date}
    if args.command in ("download", "all"):
        info = download(paths["download"], gcfg.get("source_url", SOURCE_URL))
        log(json.dumps({k: info[k] for k in ("bytes", "sha256", "md5_check")}, indent=2))
    if args.command in ("subset", "all"):
        zip_path = args.zip or paths["download"] / ZIP_NAME
        info_path = zip_path.parent / "download.json"
        info = json.loads(info_path.read_text()) if info_path.is_file() else {"file": str(zip_path)}
        index = subset(zip_path, paths["subset"], enu, half, gcfg, info)
        log(json.dumps(index["counts"], indent=2))
    if args.command in ("build", "all"):
        sub = load_subset(paths["subset"], enu)
        net = args.net or latest_net(paths["runs"])
        result = build(sub, net, paths["out"], gcfg)
        log(json.dumps(result["periods"], indent=2))
    if args.command == "validate":
        net = args.net or latest_net(paths["runs"])
        for period in args.period or list(gcfg.get("periods", PERIODS)):
            pdir = paths["out"] / period
            result = validate(net, pdir, pdir / "validate")
            log(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
