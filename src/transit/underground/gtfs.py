"""London Underground timetable subset of the BODS UK aggregate GTFS feed.

The feed already downloaded for the bus pipeline (``traffic.corridor_sumo.gtfs_bus
download``, Open Government Licence v3.0) also carries the London Underground
(agency "London Underground (TfL)", ``route_type`` 1). ``subset`` streams the zip once
(no extraction) and writes, for one service day, every Underground trip with *all*
its calls (clipping to the domain happens later, on the track geometry) to
``project/<scene>/input/underground/gtfs/`` with ``index.json`` (provenance, the
service day and why, which rail operators are absent from the feed, counts, hashes).

  PYTHONPATH=src python3 -m transit.underground.gtfs imperial_corridor
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from traffic.corridor_sumo.gtfs_bus import (
    LICENSE,
    SOURCE,
    _iter_trip_groups,
    _read_csv,
    _rows,
    _write_csv,
    active_services,
    sha256_file,
)

from .config import line_id, load_scene, log


def is_rail_type(value: str) -> bool:
    """GTFS tram/metro/rail: basic types 0-2, extended 100-199 (rail), 400-499 (urban
    rail) and 900-999 (tram)."""
    try:
        t = int(value)
    except (TypeError, ValueError):
        return False
    return t in (0, 1, 2) or 100 <= t <= 199 or 400 <= t <= 499 or 900 <= t <= 999


def feed_coverage(routes: list[dict], agencies: dict) -> dict:
    """Rail-like route types per agency, and whether Elizabeth line / Overground appear."""
    rail = Counter()
    for r in routes:
        if is_rail_type(r["route_type"]):
            name = agencies.get(r["agency_id"], {}).get("agency_name", r["agency_id"])
            rail[f"{r['route_type']}|{name}"] += 1
    elizabeth = any(
        line_id(r.get("route_short_name")) == "elizabeth"
        or "elizabeth line" in (r.get("route_long_name") or "").lower()
        for r in routes
        if is_rail_type(r["route_type"])
    )
    overground = any(
        "overground" in agencies.get(r["agency_id"], {}).get("agency_name", "").lower()
        or line_id(r.get("route_short_name")) == "overground"
        for r in routes
        if is_rail_type(r["route_type"])
    )
    return {
        "rail_route_types_by_agency": dict(sorted(rail.items())),
        "elizabeth_line_present": elizabeth,
        "london_overground_present": overground,
        "rule": "rail-like route_type (0-2, 100-199, 400-499, 900-999) whose route short "
        "name maps to the line, or whose agency name contains 'Overground'",
    }


def subset(zip_path: Path, out_dir: Path, cfg: dict, download_info: dict) -> dict:
    z = zipfile.ZipFile(zip_path)
    feed_info = next(_rows(z, "feed_info.txt"), {})
    agencies = {r["agency_id"]: r for r in _rows(z, "agency.txt")}
    all_routes = list(_rows(z, "routes.txt"))
    coverage = feed_coverage(all_routes, agencies)
    agency_ids = {a for a, r in agencies.items() if r["agency_name"] == cfg["agency_name"]}
    routes = {
        r["route_id"]: r
        for r in all_routes
        if r["agency_id"] in agency_ids and r["route_type"] in ("1", "401", "402")
    }
    log(f"{len(routes)} Underground routes ({cfg['agency_name']})")
    trips_all = [r for r in _rows(z, "trips.txt") if r["route_id"] in routes]
    services = {t["service_id"] for t in trips_all}
    calendar = [r for r in _rows(z, "calendar.txt") if r["service_id"] in services]
    exceptions = [r for r in _rows(z, "calendar_dates.txt") if r["service_id"] in services]
    day = str(cfg["service_date"])
    active = active_services(day, calendar, exceptions)
    trips = {t["trip_id"].encode(): t for t in trips_all if t["service_id"] in active}
    per_line = Counter(routes[t["route_id"]]["route_short_name"] for t in trips.values())
    missing = sorted(
        {r["route_short_name"] for r in routes.values()} - set(per_line), key=str.lower
    )
    log(f"service date {day}: {len(trips)} trips; per line {dict(per_line)}")
    if missing:
        log(f"  lines without trips on {day}: {missing}")

    kept: dict[str, list[dict]] = {}
    log("streaming stop_times.txt ...")
    with z.open("stop_times.txt") as handle:
        header = handle.readline().decode("utf-8-sig").strip().split(",")
        for tid, lines in _iter_trip_groups(handle, header):
            if tid not in trips:
                continue
            text = b"".join(lines).decode("utf-8")
            rows = [dict(zip(header, r, strict=False)) for r in csv.reader(io.StringIO(text))]
            rows.sort(key=lambda r: int(r["stop_sequence"]))
            kept[tid.decode()] = rows
    log(f"  {len(kept)} trips with stop times")
    stop_ids = {r["stop_id"] for rows in kept.values() for r in rows}
    stops_all = {r["stop_id"]: r for r in _rows(z, "stops.txt")}
    stops = {s: stops_all[s] for s in stop_ids if s in stops_all}
    for s in list(stops.values()):
        parent = s.get("parent_station")
        if parent and parent in stops_all:
            stops[parent] = stops_all[parent]

    out_dir.mkdir(parents=True, exist_ok=True)
    trip_rows = [trips[t.encode()] for t in sorted(kept)]
    st_rows = [r for t in sorted(kept) for r in kept[t]]
    route_rows = [routes[r] for r in sorted(routes)]
    cal_rows = [r for r in calendar if r["service_id"] in active]
    files = {
        "routes.txt": _write_csv(out_dir / "routes.txt", list(route_rows[0]), route_rows),
        "stops.txt": _write_csv(
            out_dir / "stops.txt",
            list(next(iter(stops.values()))),
            sorted(stops.values(), key=lambda s: s["stop_id"]),
        ),
        "trips.txt": _write_csv(out_dir / "trips.txt", list(trip_rows[0]), trip_rows),
        "calendar.txt": _write_csv(out_dir / "calendar.txt", list(cal_rows[0]), cal_rows)
        if cal_rows
        else 0,
        "stop_times.txt.gz": _write_csv(
            out_dir / "stop_times.txt.gz", list(st_rows[0]), st_rows, compress=True
        ),
    }
    files = {k: v for k, v in files.items() if (out_dir / k).is_file()}
    index = {
        "schema": "underground-gtfs-subset-v1",
        "source": SOURCE,
        "license": LICENSE,
        "attribution": "Contains public sector information licensed under the Open Government "
        "Licence v3.0 (Bus Open Data Service, Department for Transport)",
        "synthetic": False,
        "nature": "Scheduled timetable (working timetable as published in BODS GTFS); not "
        "real-time, no train positions, no crowding",
        "download": download_info,
        "feed_info": feed_info,
        "agency": cfg["agency_name"],
        "service_date": day,
        "service_date_selection": cfg.get(
            "service_date_note", "configured (gtfs.service_date in underground.json)"
        ),
        "services_active": sorted(active),
        "lines_on_service_date": dict(sorted(per_line.items())),
        "lines_without_trips": missing,
        "feed_coverage": coverage,
        "filters": {
            "routes": f"agency_name == {cfg['agency_name']!r}, route_type 1",
            "trips": "all trips of those routes running on service_date (calendar + "
            "calendar_dates); every call kept (not clipped)",
            "stops": "every stop called at, plus parent stations",
        },
        "counts": {
            "routes": len(route_rows),
            "trips": len(trip_rows),
            "stop_times": len(st_rows),
            "stops": len(stops),
        },
        "files": {
            name: {"rows": rows, "sha256": sha256_file(out_dir / name)}
            for name, rows in files.items()
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


def load(directory: Path) -> dict:
    """Subset tables: index, routes, stops, trips and stop times grouped by trip."""
    index = json.loads((directory / "index.json").read_text())
    times = defaultdict(list)
    for r in _read_csv(directory / "stop_times.txt.gz"):
        times[r["trip_id"]].append(r)
    for rows in times.values():
        rows.sort(key=lambda r: int(r["stop_sequence"]))
    return {
        "index": index,
        "routes": {r["route_id"]: r for r in _read_csv(directory / "routes.txt")},
        "stops": {r["stop_id"]: r for r in _read_csv(directory / "stops.txt")},
        "trips": {r["trip_id"]: r for r in _read_csv(directory / "trips.txt")},
        "times": dict(times),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("scene")
    p.add_argument("--zip", type=Path, help="feed zip (default: config gtfs.zip under cache)")
    args = p.parse_args(argv)
    ctx = load_scene(args.scene)
    cfg, storage = ctx["cfg"], ctx["storage"]
    zip_path = args.zip or storage.cache_root / args.scene / cfg["gtfs"]["zip"]
    info_path = zip_path.parent / "download.json"
    info = json.loads(info_path.read_text()) if info_path.is_file() else {"file": zip_path.name}
    out = storage.assets(args.scene, "input") / cfg.get("input_dir", "underground") / "gtfs"
    index = subset(zip_path, out, cfg["gtfs"], info)
    log(json.dumps({k: index[k] for k in ("counts", "lines_on_service_date")}, indent=2))
    log(json.dumps(index["feed_coverage"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
