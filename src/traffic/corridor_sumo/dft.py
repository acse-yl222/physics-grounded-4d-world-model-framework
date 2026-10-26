"""UK Department for Transport (DfT) road traffic counts: download, filter, hourly profiles.

Three per-local-authority CSV tables from the DfT road traffic statistics bucket are used
(Open Government Licence v3.0):

- ``aadf``: annual average daily flow per count point and year (both directions);
- ``aadf_direction``: the same split by direction of travel;
- ``rawcount``: the manual counts behind them, one row per count point, direction,
  count date and hour (07:00-19:00 only; ``hour`` is the start of the hour).

Files are stored unmodified under ``project/<scene>/input/dft_traffic/`` with an
``index.json`` (URL, SHA-256, size, retrieval time, licence). All later steps read only
those files.

Hourly profiles are expressed as the share of AADF in a clock hour:
``share[h] = raw count in hour h on the count date / AADF of that direction and year``.
DfT has no hourly data between 19:00 and 07:00, so nothing here produces night hours.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from .tfl import Enu

BASE_URL = "https://storage.googleapis.com/dft-statistics/road-traffic/downloads"
DATASETS = {
    "aadf": "aadf/local_authority_id/dft_aadf_local_authority_id_{id}.csv",
    "aadf_direction": (
        "aadfbydirection/local_authority_id/dft_aadfbydirection_local_authority_id_{id}.csv"
    ),
    "rawcount": "rawcount/local_authority_id/dft_rawcount_local_authority_id_{id}.csv",
}
LA_LIST = "data-gov-uk/local_authority_traffic.csv"
LICENCE = {
    "name": "Open Government Licence v3.0",
    "url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    "attribution": "Contains public sector information licensed under the Open Government "
    "Licence v3.0 (Department for Transport road traffic statistics).",
}
# Vehicle-class columns kept from the DfT tables.
CLASSES = (
    "two_wheeled_motor_vehicles",
    "cars_and_taxis",
    "buses_and_coaches",
    "lgvs",
    "all_hgvs",
    "all_motor_vehicles",
)
# Classes simulated as general traffic; buses_and_coaches are excluded (buses come from GTFS).
GENERAL = ("cars_and_taxis", "lgvs", "all_hgvs", "two_wheeled_motor_vehicles")
DFT_HOURS = tuple(range(7, 19))  # manual counts cover 07:00-19:00
DIRECTIONS = ("N", "E", "S", "W")


# ---------------------------------------------------------------- download


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _download(url: str, target: Path, timeout: float = 120.0) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "p4d-corridor-sumo/1"})
    partial = target.with_name(target.name + ".partial")
    with urllib.request.urlopen(request, timeout=timeout) as response, partial.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    partial.rename(target)


def file_name(dataset: str, la_id: int) -> str:
    return Path(DATASETS[dataset].format(id=la_id)).name


def fetch(dest: Path, la_ids: list[int], log=print) -> dict:
    """Download missing DfT tables for ``la_ids`` into ``dest``; (re)write ``index.json``.

    Existing files are kept as they are (raw data is never rewritten); their recorded
    hash is checked against the file.
    """
    dest.mkdir(parents=True, exist_ok=True)
    index_path = dest / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    files = index.get("files", {})
    wanted = [("la_list", None, LA_LIST)] + [
        (ds, la, DATASETS[ds].format(id=la)) for la in la_ids for ds in DATASETS
    ]
    for dataset, la, rel in wanted:
        name = Path(rel).name
        target = dest / name
        url = f"{BASE_URL}/{rel}"
        if target.exists() and name in files:
            if _sha256(target) != files[name]["sha256"]:
                raise RuntimeError(f"{target} does not match its recorded SHA-256")
            continue
        log(f"DfT: downloading {url}")
        _download(url, target)
        files[name] = {
            "url": url,
            "dataset": dataset,
            "local_authority_id": la,
            "sha256": _sha256(target),
            "bytes": target.stat().st_size,
            "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    index = {
        "source": "UK Department for Transport road traffic statistics",
        "base_url": BASE_URL,
        "licence": LICENCE,
        "note": "Files are stored exactly as downloaded.",
        "files": dict(sorted(files.items())),
    }
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    return index


def index_digest(index: dict, names: list[str]) -> str:
    """One SHA-256 over the recorded hashes of the files used (stable input identity)."""
    joined = "\n".join(f"{n} {index['files'][n]['sha256']}" for n in sorted(names))
    return hashlib.sha256(joined.encode()).hexdigest()


# ---------------------------------------------------------------- parsing


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def domain_bbox(origin: dict, half_m: float) -> tuple[float, float, float, float]:
    """(lon_min, lat_min, lon_max, lat_max) of the square scene domain."""
    enu = Enu(origin["longitude"], origin["latitude"])
    lon0, lat0 = enu.inverse(-half_m, -half_m)
    lon1, lat1 = enu.inverse(half_m, half_m)
    return lon0, lat0, lon1, lat1


def inside(rows: list[dict], bbox: tuple[float, float, float, float]) -> list[dict]:
    """Rows whose count point latitude/longitude lie inside ``bbox`` (bounds inclusive)."""
    lon0, lat0, lon1, lat1 = bbox
    kept = []
    for row in rows:
        try:
            lon, lat = float(row["longitude"]), float(row["latitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
            kept.append(row)
    return kept


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def general(row: dict) -> float:
    """General traffic (all motor vehicles minus buses and coaches) of a DfT row."""
    return _num(row.get("all_motor_vehicles")) - _num(row.get("buses_and_coaches"))


@dataclass
class CountPoint:
    id: str
    road_name: str
    road_type: str  # "Major" / "Minor"
    lon: float
    lat: float
    x: float
    y: float
    year: int
    estimation_method: str
    estimation_method_detailed: str
    local_authority_id: int
    local_authority_name: str
    start_junction: str = ""
    end_junction: str = ""
    aadf: dict = field(default_factory=dict)  # class -> veh/day, both directions
    # direction -> {"general": veh/day, "share": fraction of general, "source": ...}
    directions: dict = field(default_factory=dict)
    direction_source: str = ""


def latest_points(aadf_rows: list[dict], enu: Enu) -> dict[str, CountPoint]:
    """Most recent AADF year per count point."""
    best: dict[str, dict] = {}
    for row in aadf_rows:
        cp = row["count_point_id"]
        if cp not in best or int(row["year"]) > int(best[cp]["year"]):
            best[cp] = row
    points = {}
    for cp, row in best.items():
        lon, lat = float(row["longitude"]), float(row["latitude"])
        x, y = enu(lon, lat)
        points[cp] = CountPoint(
            id=cp,
            road_name=row.get("road_name", ""),
            road_type=row.get("road_type", ""),
            lon=lon,
            lat=lat,
            x=round(x, 2),
            y=round(y, 2),
            year=int(row["year"]),
            estimation_method=row.get("estimation_method", ""),
            estimation_method_detailed=row.get("estimation_method_detailed", ""),
            local_authority_id=int(row.get("local_authority_id") or 0),
            local_authority_name=row.get("local_authority_name", ""),
            start_junction=row.get("start_junction_road_name", ""),
            end_junction=row.get("end_junction_road_name", ""),
            aadf={c: _num(row.get(c)) for c in CLASSES},
        )
    return points


def direction_aadf(direction_rows: list[dict]) -> dict[tuple[str, int], dict[str, float]]:
    """(count point, year) -> {direction: general traffic AADF}."""
    out: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in direction_rows:
        key = (row["count_point_id"], int(row["year"]))
        out[key][row["direction_of_travel"]] = general(row)
    return dict(out)


def assign_directions(
    points: dict[str, CountPoint],
    by_direction: dict[tuple[str, int], dict[str, float]],
    raw_split: dict[str, dict[str, float]],
) -> None:
    """Split each point's general AADF over its directions of travel (in place).

    Preference: DfT AADF-by-direction of the same year; else the directional proportions
    of the point's raw counts; else 50/50 over both directions of an unknown orientation
    (direction ``C``, flagged).
    """
    for cp, point in points.items():
        total = point.aadf["all_motor_vehicles"] - point.aadf["buses_and_coaches"]
        dirs = by_direction.get((cp, point.year))
        if dirs and sum(dirs.values()) > 0:
            s = sum(dirs.values())
            point.directions = {
                d: {"general": total * v / s, "share": v / s} for d, v in sorted(dirs.items())
            }
            point.direction_source = "dft_aadf_by_direction"
        elif raw_split.get(cp):
            split = raw_split[cp]
            point.directions = {d: {"general": total * v, "share": v} for d, v in split.items()}
            point.direction_source = "raw_count_proportions"
        else:
            point.directions = {"C": {"general": total, "share": 1.0}}
            point.direction_source = "unknown_split_50_50"


# ---------------------------------------------------------------- hourly profiles


def is_weekday(iso_date: str) -> bool:
    try:
        return date.fromisoformat(iso_date[:10]).weekday() < 5
    except ValueError:
        return False


def raw_days(raw_rows: list[dict]) -> dict[tuple[str, str], dict[str, dict[int, dict]]]:
    """(count point, direction) -> count date -> hour -> row."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    for row in raw_rows:
        key = (row["count_point_id"], row["direction_of_travel"])
        out[key][row["count_date"][:10]][int(row["hour"])] = row
    return out


def point_profiles(
    raw_rows: list[dict],
    by_direction: dict[tuple[str, int], dict[str, float]],
    *,
    min_year: int = 2010,
    max_dates: int = 3,
    weekdays_only: bool = True,
) -> dict[tuple[str, str], dict]:
    """Per (count point, direction): mean share of AADF per hour 07-18 from raw counts.

    For each count date (complete 07-19 coverage, year >= ``min_year``, Mon-Fri when
    ``weekdays_only``), ``share[h] = general(raw hour h) / general AADF`` of that direction
    and year. The ``max_dates`` most recent dates are averaged.
    """
    profiles = {}
    for (cp, direction), days in raw_days(raw_rows).items():
        usable = []
        for day, hours in days.items():
            year = int(day[:4])
            if year < min_year or set(DFT_HOURS) - set(hours):
                continue
            if weekdays_only and not is_weekday(day):
                continue
            aadf = by_direction.get((cp, year), {}).get(direction)
            if not aadf or aadf <= 0:
                continue
            usable.append((day, {h: general(hours[h]) / aadf for h in DFT_HOURS}))
        if not usable:
            continue
        usable.sort(reverse=True)
        chosen = usable[:max_dates]
        profiles[(cp, direction)] = {
            "share": {h: statistics.fmean(s[h] for _, s in chosen) for h in DFT_HOURS},
            "dates": [d for d, _ in chosen],
            "source": "point_raw_counts",
        }
    return profiles


def pooled_profiles(
    profiles: dict[tuple[str, str], dict], road_types: dict[str, str]
) -> dict[str, dict]:
    """Median hourly share per road type over the point profiles (fallback profile)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for (cp, _), prof in profiles.items():
        groups[road_types.get(cp, "")].append(prof["share"])
    allp = [p["share"] for p in profiles.values()]
    out = {}
    for road_type, shares in [*groups.items(), ("all", allp)]:
        if shares:
            out[road_type] = {
                "share": {h: statistics.median(s[h] for s in shares) for h in DFT_HOURS},
                "n_profiles": len(shares),
            }
    return out


def profile_for(
    cp: str,
    direction: str,
    road_type: str,
    profiles: dict[tuple[str, str], dict],
    pooled: dict[str, dict],
) -> dict:
    """Profile of one point direction, else the pooled road-type profile (flagged)."""
    own = profiles.get((cp, direction))
    if own:
        return own
    if direction == "C":
        # Combined direction: average of the point's directional profiles, if any.
        mine = [p["share"] for (c, _), p in profiles.items() if c == cp]
        if mine:
            return {
                "share": {h: statistics.fmean(s[h] for s in mine) for h in DFT_HOURS},
                "source": "point_raw_counts_mean_of_directions",
            }
    group = road_type if road_type in pooled else "all"
    if group not in pooled:
        raise ValueError("No DfT raw-count profile available in the domain")
    return {
        "share": pooled[group]["share"],
        "source": f"pooled_{group.lower()}_fallback",
        "fallback": True,
    }


def raw_direction_split(raw_rows: list[dict], min_year: int = 2010) -> dict[str, dict[str, float]]:
    """Directional proportions of each point's most recent raw count date (07-19 totals)."""
    latest: dict[str, str] = {}
    for row in raw_rows:
        if int(row["year"]) >= min_year:
            cp = row["count_point_id"]
            latest[cp] = max(latest.get(cp, ""), row["count_date"][:10])
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in raw_rows:
        cp = row["count_point_id"]
        if latest.get(cp) == row["count_date"][:10]:
            totals[cp][row["direction_of_travel"]] += general(row)
    out = {}
    for cp, dirs in totals.items():
        s = sum(dirs.values())
        if s > 0:
            out[cp] = {d: v / s for d, v in sorted(dirs.items())}
    return out


def class_mix(raw_rows: list[dict], hour: int, min_year: int = 2010) -> dict[str, float]:
    """Pooled share of each general-traffic class in ``hour`` over recent weekday counts."""
    sums = dict.fromkeys(GENERAL, 0.0)
    for row in raw_rows:
        recent = int(row["hour"]) == hour and int(row["year"]) >= min_year
        if recent and is_weekday(row["count_date"]):
            for c in GENERAL:
                sums[c] += _num(row.get(c))
    total = sum(sums.values())
    if total <= 0:
        raise ValueError(f"No raw counts for hour {hour}")
    return {c: v / total for c, v in sums.items()}
