# transit.underground

London Underground _scheduled_ service for a city scene (first user:
`imperial_corridor`, 8 km × 8 km): OpenStreetMap track geometry with an assumed
vertical profile, stations with platforms and entrances, timetabled trains from the
BODS GTFS feed map-matched onto the tracks, scheduled frequency/headway/run-time
status, and protocol v1.1 sparse trajectories. No real-time data (train positions,
delays, crowding) is available or used; every train position is a scheduled position.

```sh
PYTHONPATH=src python3 -m transit.underground.osm imperial_corridor    # ~1 h, once (planet ORC)
PYTHONPATH=src python3 -m transit.underground.gtfs imperial_corridor   # ~2 min, once
PYTHONPATH=src python3 -m transit.underground.run imperial_corridor [--run-id <id>]
python3 tools/check_contract.py \
    cache/imperial_corridor/underground/<run_id>/bundle/<run_id>/manifest.json
```

Parameters: `project/<scene>/configs/underground.json`; scene origin and domain come
from `configs/image_to_threejs.json` (ENU via `traffic.corridor_sumo.tfl.Enu`, the
equirectangular tangent plane used by the rest of the scene). Inputs are written to the
git-ignored `project/<scene>/input/underground/{osm,gtfs}/` with `index.json`
provenance; per-stripe extraction caches live in `cache/<scene>/underground/osm/`.
The run registers nothing under `project/`.

| File          | Role                                                                         |
| ------------- | ---------------------------------------------------------------------------- |
| `config.py`   | scene loading, line reference table (TfL colours, line kind), line ids       |
| `osm.py`      | OSM railway subset from the planet ORC (Overture ids → relations/ways/nodes) |
| `gtfs.py`     | Underground subset of the BODS GTFS zip for one service day                  |
| `geometry.py` | track graph, depth model, clipping, simplification, map matching             |
| `build.py`    | tracks, stations/platforms/entrances, patterns, period trips, status         |
| `run.py`      | end-to-end CLI and protocol bundle                                           |

## Inputs

1. **OSM geometry** (`osm.py`, ODbL 1.0, © OpenStreetMap contributors). The planet
   ORC `s3://osm-pds/planet/planet-latest.orc` is read with the stripe reader of
   `traffic.corridor_sumo.osm_extract` (binary search over stripe first keys, retries,
   per-stripe JSON cache). Way ids are the OSM sources of Overture transportation
   segments with `subtype = rail` in the domain + `buffer_m` (1500 m); Overture base
   `infrastructure` transit features (subway/railway stations, platforms) add station
   and platform ids. All relation stripes are read once for `route` =
   subway/train/light_rail/railway/tram relations touching those ways, their
   `route_master`s and `public_transport=stop_area` relations. The ways of the route
   relations, and platform/station ways of routes and stop areas, are added. Overture
   carries no subway entrances, and OSM entrances are standalone nodes, so one pass
   over every node stripe collects the coordinates of all way nodes and every node in
   the bbox tagged as a station, entrance, platform or stop.
2. **Timetables** (`gtfs.py`, Open Government Licence v3.0). The BODS UK aggregate
   GTFS zip downloaded by `traffic.corridor_sumo.gtfs_bus download` contains
   "London Underground (TfL)" (`route_type` 1, several `route_id`s per line). All
   trips of one service day are kept with every call; the day is configured
   (`gtfs.service_date`, 2026-06-25, the same Thursday as the bus subset; all eleven
   lines run on it). The feed has no Elizabeth line and no London Overground
   (`index.json` → `feed_coverage`); those lines appear with OSM tracks and stations
   only (`timetable: false`, no trains). GTFS times are whole minutes with
   arrival = departure (no dwell).

## Model

- **Tracks.** Ways with `railway` ∈ subway, rail, light_rail, narrow_gauge (sidings
  and yards included, `service` kept) with a node within domain + buffer form an
  undirected graph densified to `graph_step_m` (20 m). Lines per way come from OSM route
  relations (`relation_line`: network London Underground or `route=subway`, Elizabeth
  line, Overground lines Lioness/Mildmay/Suffragette/Weaver/Windrush/Liberty). Ways
  are merged into chains at degree-2 joins with equal lines/level, clipped to the
  domain (a polyline whose first point is outside starts on the boundary; z is
  interpolated) and simplified (3D Douglas–Peucker, `simplify_m` = 1 m).
- **Depth (assumed, `depth_source` per track).** No measured depths are used.
  A tunnel (`tunnel=yes`) gets its line's typical depth: sub-surface
  District/Circle/H&C/Metropolitan `subsurface_m` 6 m, deep tube `deep_m` 22 m, other
  rail `rail_tunnel_m` 12 m, overrides in `per_line_m` (Elizabeth line 22 m: bored at
  tube depth); a way shared by several lines takes the deepest. OSM `layer` is
  relative, so each line's length-weighted most common tunnel layer is its reference:
  that layer (or a missing one) sits at the typical depth and every layer below/above
  it adds/removes `layer_step_m` (6 m), clamped to one step shallower and
  `max_layer_steps` (2) deeper (and to [`min_tunnel_m`, `max_depth_m`]). Tunnels
  without a known line use 6 m (railway=subway) or 12 m
  (`assumed_typical_line_unknown`). Bridges/viaducts (or layer > 0): +6 m per layer,
  ramped down onto the approaches over `bridge_ramp_m` (100 m). Everything else is at
  0 (flat ground; embankments, cuttings and terrain not modelled). Portals: depth rises
  linearly from 0 at the vertex shared with a surface way to the full depth
  `portal_ramp_m` (200 m) into the tunnel (min-plus relaxation on the graph, gradient
  depth/200 m); layer changes between tunnels ramp with the same gradient.
  `summary.tunnel_crossings` counts crossings of different-line tunnels (both > 3 m
  below ground) and lists those whose assumed levels are < 3 m apart.
- **Stations.** GTFS parent stations (`940GZZLU…`) inside the domain; lines from the
  trips calling there. Platform stops without a parent get the NaPTAN station code
  (`9400ZZLUxxxN` → `940GZZLUxxx`, added at their mean position when the feed lacks
  it). Each line's platform is an OSM platform way (railway=platform /
  public_transport=platform) within `station_match_m` whose centre is ≤ 25 m from
  that line's track, drawn as the track section it spans; otherwise a
  `platform_length_m` (120 m) section of the line's track centred on the GTFS platform
  stops (`source` says which). Platform z = track z there; station `z` = shallowest
  platform. Elizabeth/Overground stations are OSM `railway=station` nodes near those
  lines' stops (`timetable: false`, id = `naptan:AtcoCode` or `osm:n…`). Entrances
  (`railway=subway_entrance`/`train_station_entrance`) go to the station named by a
  stop area containing them, else the nearest station within 350 m.
- **Patterns and trains.** Each trip's calls are cut to the inside stations plus one
  outside neighbour on each side (a trip that leaves the domain for two or more
  outside calls, the Circle loop, is split into runs `<trip_id>#1`, `#2`); trips with equal (line, direction, stations) share
  a pattern. Consecutive GTFS platform stops are joined by the shortest track path
  restricted to the line's ways (multi-source Dijkstra from track vertices within
  `station_match_m`, cost = length + 2 × snapping), else on any rail way
  (`track_any_rail`), else a straight segment (`straight_fallback`); a path longer than
  4 × the straight distance counts as failed. `match.path_over_straight` and per-pair
  methods are reported. The path is clipped to the domain; `station_offsets_m` are
  distances from the clipped start (negative / beyond the length for outside
  stations). A period file lists every trip inside the domain during
  [start − `lead_s`, end] with `[arr, dep]` per pattern station (seconds after
  midnight). Positions are linear in distance between a departure and the next
  arrival (constant speed, no acceleration profile), stationary between arrival and
  departure.
- **Status** (`status: "scheduled"`): per line and GTFS direction and period, trains
  per hour (departures in [start, end) at the busiest domain station), mean scheduled
  headway there, median domain run time and speed of trains crossing the whole domain
  on their pattern; per station and line, trains per hour per period and first/last
  train of the service day counting calls from 04:00 (times past 24:00 allowed); the
  feed's 00:00–04:00 calls on the service day are counted separately
  (`calls_before_04h`).

## Bundle

`cache/<scene>/underground/<run_id>/bundle/<run_id>/`:

- `manifest.json`: one `trajectories` layer `underground_<period>` per period
  (`trajectory_frames`, `data/trajectories_<period>.json`, scheduled positions every
  `trajectory_dt_s` = 10 s from start − 10 min to end; samples are seconds since that
  window start, ids = GTFS trip ids, z = track level); JSON artifacts below, config
  copy, source snapshot.
- `data/underground.json` (`underground-network-v1`): `lines` (id, name, colour,
  kind, timetable), `tracks`, `stations` (platforms, entrances), `summary`,
  `provenance`.
- `data/underground_trains_<period>.json` (`underground-trains-v1`): `patterns`,
  `trips`, `t0`, `t1`, provenance.
- `data/underground_status.json` (`underground-status-v1`).

`python3 -m unittest tests.test_underground -v` covers the portal ramp, layer
separation, bridge approaches, clipping, simplification, map matching on a synthetic
track graph, headway/trains-per-hour, schedule interpolation and an end-to-end
synthetic line.
