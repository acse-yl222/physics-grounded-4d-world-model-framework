# corridor_sumo

SUMO traffic simulation for city scenes on an OpenStreetMap (default) or Overture road
network (first user: `imperial_corridor`,
8 km × 8 km around Imperial College South Kensington and White City). By default the car
demand is calibrated to UK Department for Transport (DfT) road traffic counts and
simulated for configurable clock hours (AM peak, inter-peak, PM peak); the output is a
protocol v1.1 run with per-edge traffic state (flow, speed, density, level of service)
and one sparse `trajectories` layer plus a compact viewer binary per period.
`--synthetic` keeps the earlier single window with synthetic random demand.

```sh
python3 -m pip install eclipse-sumo rtree   # SUMO binaries + tools; rtree speeds up sumolib
PYTHONPATH=src python3 -m traffic.corridor_sumo.osm_extract imperial_corridor   # ~40 min, once
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --network-only
PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus build imperial_corridor \
    --net cache/imperial_corridor/traffic_sumo/<net_run_id>/net/net.net.xml
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --reuse <net_run_id>
# or everything in one go (buses only when the GTFS step was built on the same network):
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor
# periods only, reusing the network and candidate routes of an earlier run:
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --reuse <run_id> [--periods am_peak,pm_peak]
# legacy synthetic demand:
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor --synthetic [--no-tfl]
python3 tools/check_contract.py cache/imperial_corridor/traffic_sumo/<run_id>/bundle/<run_id>/manifest.json
p4d retain cache/imperial_corridor/traffic_sumo/<run_id>/bundle   # optional, registers view
```

SUMO is found through `SUMO_HOME` or the `eclipse-sumo` wheel (`sumo.SUMO_HOME`).
Parameters live in `project/<scene>/configs/traffic_sumo.json`; scene origin and domain
come from `configs/image_to_threejs.json`.

| File              | Role                                                                    |
| ----------------- | ----------------------------------------------------------------------- |
| `osm_extract.py`  | OSM subset of the buffered domain from the planet ORC (AWS Open Data)   |
| `osm_net.py`      | netconvert OSM import (eqc = scene ENU), checks, network report         |
| `overture_net.py` | Overture segments/connectors → SUMO plain XML (`.nod.xml`, `.edg.xml`)  |
| `network.py`      | netconvert options, network statistics, ENU coordinate check            |
| `tfl.py`          | TfL Unified API download/cache, route/timetable parsing, bus routes     |
| `dft.py`          | DfT count download/index, bbox filter, AADF, hourly profiles            |
| `calibrate.py`    | count → edge matching, GEH/R², edgeData targets, routeSampler           |
| `periods.py`      | per-period calibration, simulation, edge state, `traffic_state.json`    |
| `state.py`        | edgeData parsing, level-of-service classes, shape simplification        |
| `demand.py`       | vehicle types, randomTrips cars/taxis, synthetic bus lines              |
| `simulate.py`     | headless SUMO run with FCD output; period runs with edgeData            |
| `export.py`       | FCD parsing, vehicle selection, `trajectory_frames` JSON, `traffic.bin` |
| `road_network.py` | SUMO lanes/internal lanes/junctions -> `road_network.json`, OSM decks   |
| `lane_routes.py`  | vehroute exit times -> lane paths, timing, playback checks              |
| `run.py`          | end-to-end CLI                                                          |
| `sumo_env.py`     | locating SUMO binaries, tools and `sumolib`                             |

## OpenStreetMap network (default, `network.source: "osm"`)

1. **Extraction** (`osm_extract.py`). The OSM planet is read selectively from
   `s3://osm-pds/planet/planet-latest.orc` (anonymous, us-east-1; ODbL 1.0,
   © OpenStreetMap contributors). Rows are sorted by type (node, way, relation) and id,
   so the stripes holding an id set are found by bisection over stripe first keys
   (`locate`), and only `id, tags, nds` (ways), `id, lat, lon, tags` (nodes) or
   `id, tags, members` (relations) of those stripes are read, in a thread pool. Way ids
   are the OSM sources (`sources[].record_id` `w<id>@<v>`) of the Overture road
   segments of the domain plus `osm.buffer_m` (1500 m: boundary junctions, Putney and
   Wandsworth Bridges, Barnes connectivity). Ways whose `highway` can carry motor
   vehicles or buses are kept (footways, paths, cycleways, steps, rail not); ways newer
   than the Overture snapshot that share a node with a kept way are added from the
   newest way stripes. All their nodes (coordinates exactly as stored, 7 decimals; tags
   when tagged), turn restrictions (`type=restriction`/`restriction:*` with all ways
   kept) and, separately, bus route relations are written to
   `project/<scene>/input/osm/` (`osm.xml.gz`, `bus_route_relations.json.gz`,
   `index.json` with object ETag/LastModified, bbox, rules, counts, sha256, licence).
   Per-stripe results are cached in `cache/<scene>/traffic_sumo/osm/` (resume).
2. **Network** (`osm_net.py`): netconvert's OSM importer with
   `+proj=eqc +lat_ts=lat0 +lat_0=lat0 +lon_0=lon0 +R=6378137` and offset normalisation
   disabled, i.e. exactly `tfl.Enu`; the build fails unless at least 1000 unjoined OSM
   nodes sit within 0.05 m of `Enu(lon, lat)`. Left-hand traffic; OSM `lanes`,
   `lanes:forward/backward`, `turn:lanes`, `maxspeed` (mph), `oneway`, roundabouts,
   access/`motor_vehicle`/`bus`/`psv` and lane access (`bus:lanes`, busways) are used;
   untagged speeds use GB urban defaults (`DEFAULT_SPEED_MPH`), untagged lanes SUMO's
   `osmNetconvert` typemap. Signals are OSM `highway=traffic_signals` nodes, clustered
   onto their junctions (`tls.guess-signals`, `tls.join`), as actuated signals with
   netconvert phase plans (real timings unknown). Edges keep `ref`, `lanes`, `maxspeed`
   and access tags as parameters. Edges outside domain + buffer are cut and the largest
   connected component is kept. Optional plain-XML patch files (`network.osm.patches`,
   relative to `project/<scene>/configs/`) are applied in a second netconvert pass and
   recorded with their hashes. `network_report.json` gives tag completeness (share of
   main-road length with `lanes`/`maxspeed`/`ref`), lane-km by class, OSM signal nodes vs
   SUMO traffic lights, junction joins, connectivity of `network.osm.places` from/to the
   domain centre by car and bus, and the same figures for the comparison network
   (`network.osm.compare_run`).
3. **Recorded domain.** The buffer is simulated but not recorded: edge state, count
   points, `count_state.json` shapes and the playback (FCD samples) are restricted to the
   scene square.

`network.source: "overture"` keeps the earlier Overture network (below).

## DfT-calibrated periods (default)

1. **Network** as below (built, or reused with `--reuse <run_id>`).
2. **Counts.** `dft.fetch` stores, unmodified, the per-local-authority DfT tables `aadf`,
   `aadfbydirection` and `rawcount` (plus the local-authority list) from
   `storage.googleapis.com/dft-statistics/road-traffic/downloads/` in
   `project/<scene>/input/dft_traffic/` with `index.json` (URL, SHA-256, bytes, retrieval
   time, licence: Open Government Licence v3.0). The local authorities in
   `dft.local_authorities` are those with count points inside the domain (for
   `imperial_corridor`: Wandsworth 108, Westminster 109, Kensington and Chelsea 110,
   Hounslow 111, Brent 118, Camden 145, Hammersmith and Fulham 146, Ealing 147, Richmond
   upon Thames 175; Lambeth 107 has none). Count points whose latitude/longitude lie in the
   domain are kept; each uses its most recent AADF year, points last reported before
   `min_aadf_year` are dropped as stale. `estimation_method` (Counted/Estimated) is kept
   per point. Only general traffic is targeted: all motor vehicles minus
   `buses_and_coaches` (buses come from GTFS).
3. **Directions and hourly profiles.** Directional AADF comes from `aadfbydirection` of
   the same year (else the raw-count proportions, else one combined `C` direction split
   50/50 over a two-way road, flagged). The share of AADF per hour 07–18 is
   `raw hourly count / directional AADF of the count year`, averaged over the most recent
   complete weekday count dates (`profile`). Without raw counts a point uses the pooled
   median profile of its road type (`profile_source: pooled_*_fallback`). DfT counts do not
   cover 19:00–07:00: no night profile is made; the mean share of AADF outside 07–19 is
   reported as an aggregate only.
4. **Matching.** On the OSM network an edge whose `ref` contains the DfT route number
   (A4, A315, ...) wins (`ref+heading`), and edges with only other route numbers are
   skipped. Overture edges carry street names, not route numbers, so otherwise a count
   point direction goes to the nearest passenger edge within `match.radius_m` whose class fits
   the DfT road type (major: motorway–secondary, minor: secondary–living street; weaker
   pairings recorded as `weak_class`) and whose heading is within
   `heading_tolerance_deg` of the direction of travel. A DfT street name, when given,
   matches by normalised name; edges named after the link's start/end junction roads are
   skipped. Quality, distance and unmatched reasons are reported.
5. **Calibration.** Edge target = directional AADF × hourly share (mean when several
   points share an edge). A candidate route set (`calibration.candidates`: fringe-weighted
   long trips biased to fast roads plus shorter local trips, randomTrips + duarouter with
   randomised weights) is sampled by SUMO `tools/routeSampler.py` to match the targets of
   the hour and of a warm-up interval (`periods.warmup_s`, previous hour's profile).
   routeSampler bounds only counted edges, and random candidate routes overload
   uncounted and under-laned edges, which gridlocked every test run. Capacity screening
   (`calibration.capacity_screening`) therefore drops sampled vehicles, in seeded random
   order, while their route crosses an edge loaded beyond `veh_h_lane × lanes` (counted
   edges: at least their target). The fit is reported per count as GEH and summarised
   (% GEH < 5, R²) for the routeSampler output, after screening and for the simulated
   flows, whether good or poor. Vehicle types follow the pooled DfT class mix of the hour
   (car/taxi, LGV, HGV, two-wheeler; passenger permissions).
6. **Simulation** per period in seconds since midnight: `start − warmup … end`.
   `simulation.mesosim` with `extra_options: {"meso-junction-control": true}` (the
   `imperial_corridor` default) uses SUMO's mesoscopic model _with_ junction control:
   vehicles wait at red signals and give way at priority junctions (overtaking,
   interpolated FCD positions). `mesosim: false` runs the microscopic model; on the
   OSM network it is no longer the Overture deadlock (≈ 75 000 teleports, mean speed
   < 1 m/s) but still congests progressively: AM peak with GTFS buses, 12 338 teleports
   (7 367 jam, 4 257 yield, 714 wrong lane), 22 000 vehicles still in the network at
   09:00, 18 min per period, simulated counts R² 0.05; reducing demand to 60 % still
   left ≈ 1 500 teleports in 50 min (Marylebone Road, Shepherd's Bush Green, Goldhawk
   Road, A4 Great West Road). Without real signal timings and junction calibration the
   microscopic model is not used for the recorded runs. `max_depart_delay_s` drops
   vehicles that cannot enter (counted in statistics), `extra_options` passes further
   SUMO options (e.g. `ignore-junction-blocker`, `time-to-impatience` for micro tests).
   edgeData over the measured hour at 300 s and 3600 s (all vehicles) and 3600 s for
   general traffic only (GEH check). Mesoscopic caveats: queues are per edge segment
   (no lane-level interactions, no spillback inside junctions); interpolated FCD
   positions can step back by tens of metres when a queued vehicle's segment exit is
   delayed (`heading_vs_motion`). Without junction control (Overture runs before the
   OSM network) signals caused no delay and speeds were optimistic.
7. **Buses (GTFS step).** If `cache/<scene>/traffic_sumo/<gtfs_dir>/<period_id>/`
   contains `bus_stops.add.xml` and `buses.rou.xml`, both are added to that period with
   `--stop-output <period dir>/stopinfos.xml`; departures must use the same
   seconds-since-midnight clock. The built-in `bus` vType is omitted when those files
   define one. Without them the period runs without buses.
8. **State.** Per edge and interval: `q` (entered veh/h), `v` (m/s), `k` (veh/km),
   `k_lane` (veh/km/lane), `occ` (%), `wait` (s) and `los`. LOS uses the speed ratio to
   the edge speed limit (≥ 0.8 free, 0.6–0.8 moderate, 0.4–0.6 heavy, < 0.4 congested),
   raised to at least heavy at `k_lane` ≥ 40 and to congested at ≥ 70, and capped at
   moderate when `k_lane` < 7 (isolated stops at signals). Edges without vehicles have no
   state.

Bundle `data/` files:

- `traffic_state.json` (`corridor-traffic-state-v1`): `periods`, `edges` (id, name, cls,
  lanes, free_speed, length, shape simplified to 2 m), `state[period][edge]` hourly
  `{q, v, k, k_lane, occ, wait, los}`, per-period `summary` and `calibration`,
  `count_points` (observed/simulated flow and GEH per period), `thresholds`, `provenance`.
- `traffic_state_5min.json`: 5-minute `[q, v, k_lane, los_index]` per edge and period.
- `count_state.json` (`corridor-count-state-v1`, see below) on the same network.
- `bus_status.json` (`bus_status.compute` over this run's period stop output) and
  `bus_stops.json` (the GTFS step's `stops.json`), when the GTFS step was built.
- `network_report.json` (OSM networks): tag completeness, lane-km by class, signals,
  junction joins, connectivity and the comparison with `network.osm.compare_run`.
- `traffic_<period>.json` + `.bin` (format below) and `trajectories_<period>.json`
  (one protocol `trajectories` layer `traffic_<period>` each) for the last
  `periods.fcd_window_s` seconds of the hour. Manifest samples are seconds since the
  window start (same length for all periods); the viewer index `t0` is seconds since
  midnight.
- `road_network.json` and `traffic_routes_<period>.json`: the lane-accurate playback
  (next section).

## Lane-accurate playback (`road_network.py`, `lane_routes.py`)

Mesoscopic FCD positions jump between lanes and across junctions (vehicles move between
25 m queue segments), and the viewer's Overture road surfaces are not the OSM network the
vehicles drive on. The run therefore also exports the drivable SUMO network and, per
period, each vehicle's lane path with entry times, so a viewer draws roads and vehicles
from one geometry and moves vehicles along lane centre lines.

- `road_network.json` (`corridor-road-network-v1`; above 12 MB an index,
  `corridor-road-network-index-v1`, of `road_network_<k>.json` chunks that split
  `edges`, `lanes`, `connections` and `junctions` into contiguous slices with global
  indices), read with sumolib (`withInternal=True`):
  - `edges`: `id, name, type, from, to, speed, priority, lanes`, plus `level` and
    `structure` (bridge, tunnel, covered) where OSM says so;
  - `lanes`: `id, edge, index` (SUMO lane index, 0 = kerbside), `width, speed, length`
    (SUMO length), `allow` when closed to cars (e.g. `bus`) and `shape` `[[x, y, z]]`;
    internal lanes (`:` ids) have `edge` null and `junction`;
  - `connections`: `from_lane, to_lane, via, dir`, `tl` at signals; also from each
    internal lane to the next lane of its via chain;
  - `junctions`: `id, type, shape`, `deck_m` when raised; plus `counts`, `provenance`.

  Lanes with a point or segment in the scene square are kept whole (not clipped);
  internal lanes of connections between kept lanes are included;
  pedestrian-, bicycle- and rail-only lanes are dropped. x/y are scene ENU metres; z is
  `DemSurface.road(x, y)`, plus OSM bridge decks: the net carries no bridge/layer tags,
  so they come from the scene OSM subset via the lane `origId` (OSM way ids) and
  projection onto the way; level `max(layer, 1 if bridge)` × `DECK_M` 6.5 m (city model)
  above the line between the street heights at the ends of the bridge run, slope limited
  to 6 % from the run ends and between levels; mid-span junctions are raised so lanes,
  internal lanes and junction polygons meet. Tunnels/covered ways are flagged in
  `structure` and left on the street surface. Shapes are resampled every 10 m for the
  terrain, simplified in 3D at 0.1 m and rounded to 0.1 m.

- `traffic_routes_<period>.json` (`corridor-traffic-routes-v1`; chunked like the road
  network above 12 MB) with `period, t0, t1, vehicles, lane_choice, timing, provenance`
  for every vehicle on an exported lane in the playback window (the window of
  `traffic_<period>.bin`); elements are trimmed to the window. A vehicle has
  `id, type, path, enter, leave` and, where needed, `jumps, changes, stops, end_pos`.
  `path` holds lane indices into `road_network` `lanes` in driving order, internal lanes
  of each connection included; `enter` the time each element is entered; `leave` the
  time the last one is left (null while still driving at the end; `end_pos` is then the
  FCD position along it at `t1`).
  - Times come from SUMO `--vehroute-output` with `exit-times` and `write-unfinished`
    (both work in the mesoscopic model): entry = departure or the exit time of the
    previous edge. Meso has no internal edges, so a connection's internal lanes get
    `min(length / internal lane speed, the time at the edge's mean speed)` at the end of
    the edge before it. Exit times are whole seconds; where an element would be passed
    faster than 1.3 × its speed limit its entry is moved earlier, taking time from the
    elements before it (count and maximum shift in provenance).
  - Lane choice: per vehicle a dynamic programme over the lanes its vClass may use,
    minimising lane changes along SUMO connections (via chains inserted); unavoidable
    changes are listed in `changes` (lateral hop at the start of that element); ties go
    by a per-vehicle hash so traffic spreads over equivalent lanes; buses use their stop
    lane on stop edges. `stops` (`path_index`, `pos_m` along the exported shape,
    `arrive`, `depart`) come from the route output's `started`/`ended`.
  - `jumps` `[i, t]`: element `i - 1` was left at `t` and the vehicle is hidden until
    `enter[i]` (jam teleports from the SUMO warning log `sumo_warnings.log`, or leaving
    the exported network); viewers cut there instead of animating.
  - Per period the run reconstructs 500 vehicles (SHA-1 order) at 1 s and records in
    `periods.<id>.recorded.lane_playback.verification`: distance to the nearest lane
    centre line, sideways steps (> 1 m across the lane/heading direction), still steps,
    steps > 25 m, implied speeds (flag > 40 m/s), share of vehicles with jumps or lane
    changes, vehicles on the same lane within 4 m (all vehicles), and the same figures
    for the FCD playback. Constant speed within an element ignores queue spacing, so
    queued vehicles can overlap on a lane; meso does not assign lanes, so lane
    assignment is a reconstruction.

## Count-based hourly state (`count_state.py`)

The calibrated periods carry only part of the observed flow (see the fit in
provenance), so `count_state.py` gives an observation-led estimate for every hour
07:00-19:00 on counted roads: DfT directional AADF x weekday hourly share for the
flow; lanes from OSM `lanes` tags where tagged (`lanes_source: osm`, general-traffic
lanes of the matched edge) or else the assumed minimum per direction
(`lanes_source: assumed`) and per-lane capacity by road type; HCM 2000 signal control delay
(junction-controlled roads) or BPR (grade-separated roads) for speed; density
`k = q / v`; LOS from the volume/capacity ratio (speed ratio on grade-separated roads).
Every assumption is written into the output. No hour outside 07:00-19:00 is estimated.

```sh
PYTHONPATH=src python3 -m traffic.corridor_sumo.count_state \
    project/imperial_corridor/configs/traffic_sumo.json \
    --net cache/imperial_corridor/traffic_sumo/<run_id>/net/net.net.xml --out count_state.json
```

## Synthetic single window (`--synthetic`)

1. **Network.** `fetch_overture.py --layers segments connectors` writes the transport
   layers to `project/<scene>/input/overture_transport/` (kept apart from the geometry
   pipeline's `input/overture/`, whose hashes are recorded in `project.json`). Drivable
   road classes motorway…service and living_street are kept (service `parking_aisle`
   and `driveway` skipped); footways, paths, cycleways, steps, pedestrian streets,
   tracks, abandoned/under-construction roads and private roads are dropped; bridges
   and road tunnels are kept. Segments are split at Overture connectors (one SUMO node
   per connector); ends cut by the domain edge become fringe nodes. Lanes and default
   speeds come from the class table in `overture_net.py`; tagged `speed_limits` win.
   `access_restrictions` give one-way roads (`denied` + `heading`), bus-only
   carriageways (`denied` + `allowed mode=[bus]`) and private roads (`allowed` only
   for `recognized` users). Overture has no signal locations: junctions where three or
   more trunk/primary/secondary/tertiary pieces meet are signalised, and netconvert's
   TLS guessing, junction joining, ramp and roundabout guessing are on. The net is
   left-hand drive and is reduced to its largest connected component.
2. **Coordinates.** netconvert runs with `--offset.disable-normalization`, so SUMO
   x,y are scene ENU metres. `network.describe` fails the run unless the location
   offset is (0, 0) and every unjoined node sits at its plain-XML position.
3. **Demand.** Cars and taxis are _synthetic_: `randomTrips.py` with fringe weighting,
   a minimum trip distance and duarouter validation (`--validate`). Buses come from the
   TfL cache in `project/<scene>/input/tfl/` when it exists (map-matched with
   `sumolib.route.mapTrace`, stops as `busStop`s, headway from the API timetable).
   Without a cache the run tries to download one (needs `api.tfl.gov.uk`; `TFL_APP_KEY`
   optional) and otherwise logs that TfL buses are skipped and adds synthetic bus
   lines (long bus-permitted randomTrips routes biased to fast roads, fixed headway,
   no stops). TfL data is never fabricated: lines without geometry or frequency are
   skipped unless `tfl.default_headway_s` is set, which is recorded as an assumption.
4. **Simulation.** 0–1200 s, 1 s steps; FCD recorded from 300 s (warm-up excluded),
   i.e. samples 300…1199 s (900 frames). Teleports are SUMO's (`time_to_teleport_s`);
   a teleporting vehicle is absent from FCD and is not interpolated.
5. **Exports** in `cache/<scene>/traffic_sumo/<run_id>/bundle/<run_id>/`:
   - `manifest.json` — `traffic` layer, `trajectory_frames`, ids = SUMO vehicle ids,
     positions ENU metres with z = 0, samples = recorded seconds; provenance records
     the synthetic flags, SUMO version, net/demand hashes, network statistics and the
     full configuration. `sumo/` holds the gzipped net and demand for reproduction.
   - `data/traffic.json` + `data/traffic.bin` — schema `corridor-traffic-v1`:
     `{schema, t0, dt, frames, synthetic, vehicles:[{id, type}], provenance, binary}`.
     `traffic.bin` is little-endian; per frame `uint32 count`, then `count ×
{uint32 vehicleIndex, float32 x, float32 y, float32 headingRad}`, heading in ENU
     radians counter-clockwise from +x (`radians(90 − sumo_angle)`).

## Size budget

Per period (or the single synthetic window), all simulated vehicles are kept in FCD, but the exports carry a subset so that
`traffic.bin` stays under `export.max_bin_bytes` (14 000 000 bytes) and at most
`export.max_concurrent_vehicles` vehicles appear in a frame. Frames stay at 1 s.
Selection is per vehicle — whole trajectories only: all buses first, then cars and
taxis in SHA-1 order of their ids (deterministic, independent of departure time).
The protocol layer and the binary contain the same subset; counts of simulated and
exported vehicles are in provenance.

## Verification

- Heading/coordinates: the run reports `heading_vs_motion`, the angle between the
  exported heading and the displacement between consecutive frames (median ≈ 0°),
  and the network coordinate check above. Unit tests cover the SUMO angle convention.
- `python3 -m unittest tests.test_corridor_sumo -v` covers the Overture conversion,
  netconvert coordinates (skipped without SUMO), TfL parsing on a fixture marked
  synthetic, DfT bbox filter, profiles and fallback, direction splits, heading/class
  matching, GEH/R², LOS classes, count matching and routeSampler on a tiny network
  (skipped without SUMO), binary round trip, vehicle selection and protocol validation.
- `python3 -m unittest tests.test_corridor_lanes -v` covers the road network export and
  lane paths on a tiny netconvert junction (skipped without SUMO: lanes, internal lanes,
  connections, kerbside left turn, bus-only lane, spreading over equivalent lanes,
  playback on the centre lines), the timing split, playback with a stop, a jump and an
  open end, vehroute/teleport parsing, bridge decks and chunking of both documents.

## BODS GTFS timetable buses (`gtfs_bus.py`, `bus_status.py`)

Real _scheduled_ bus services from the DfT Bus Open Data Service (BODS) UK aggregate
GTFS feed (Mobility Database mirror, Open Government Licence v3.0). Stop locations
are NaPTAN (`stop_id` = ATCO code, `stop_code` = SMS code). No real-time vehicle
positions or passenger loads are used: delays, speeds, regularity and status are SUMO
model estimates.

```sh
PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus download imperial_corridor  # ~1.3 GB
PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus subset imperial_corridor    # ~75 s
PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus build imperial_corridor     # ~4 min
PYTHONPATH=src python3 -m traffic.corridor_sumo.gtfs_bus validate imperial_corridor  # optional
PYTHONPATH=src python3 -m traffic.corridor_sumo.bus_status \
    project/imperial_corridor/configs/traffic_sumo.json [<period run dir> ...]
```

1. **Download** streams the zip to `cache/<scene>/traffic_sumo/gtfs_download/` and
   writes `download.json` (URL, generation-pinned object metadata, retrieval time,
   sha256). GCS stores the object gzip-encoded and publishes the md5 of the stored
   bytes; when a proxy decodes the transfer, that md5 cannot be checked and the
   zip's per-member CRC-32 test is recorded instead.
2. **Subset** streams `stop_times.txt` (4.7 GB) and `shapes.txt` from the zip without
   extracting it, into `project/<scene>/input/gtfs_bods/` (git-ignored scene input):
   domain stops (location type 0/blank plus stations and parents), bus routes
   (`route_type` 3 or 700–799) with a trip calling in the domain on any day,
   and the trips of one representative service day clipped to their first..last
   domain stop. `trips.txt` adds the domain entry/exit times and the neighbouring
   outside stops. The day is a Tuesday–Thursday within six weeks of the feed start,
   not an England/Wales bank holiday, with the most scheduled trips nationally
   (`gtfs.service_date` or `--date` override it). `index.json` records provenance,
   the selection candidates, counts and file hashes.
3. **Build** reads only the subset and the newest SUMO network
   (`cache/<scene>/traffic_sumo/*/net/net.net.xml`, or `--net`) and writes
   `cache/<scene>/traffic_sumo/gtfs/`:
   - `stops.json`: `[{id, code, name, x, y, lat, lon, routes, parent?, station?}]`.
   - `schedule.json`: per route-direction (`<short name>|<direction_id>`, operator
     route ids with the same short name are merged) the main stop pattern, simplified
     path, busiest stop and, for the periods and each hour 05–24, trips/h at the
     busiest stop, headway (60 / trips/h and the mean gap there), median scheduled
     domain run time and speed; plus scheduled buses/h per stop. Trips that leave and
     re-enter the domain keep their longest inside run of stops.
   - `matching.json`: per route-direction and stop pattern, the share of stops
     matched, matched path length vs shape length (where the feed has shapes) and vs
     the straight-line stop chain.
   - `<period>/bus_stops.add.xml`, `buses.rou.xml`, `trips.json`, `period.json`
     for the trips inside the domain during [start − 20 min, end].
4. **Map matching** (`Matcher`) is an HMM/Viterbi over candidate kerbside bus lanes
   near each stop (lane 0; a stop on the right of the lane direction is penalised
   because the net drives on the left), with bus-permitted shortest paths compared
   against the stop-to-stop distance along the GTFS shape or the straight line.
   Stops with no bus lane within `stop_snap_m` count as unmatched; up to
   `max_skipped_stops` consecutive others may be skipped at a cost. Each matched
   stop becomes a 20 m `<busStop>` (id = ATCO code, `#n` when the same stop is
   matched onto another lane; name = ATCO code + stop name).
5. **SUMO vehicles**: one `<vehicle type="bus">` per scheduled trip, `departPos="stop"`
   at its first call in the window, with `<stop busStop arrival duration until>`:
   arrival = scheduled arrival, `until` = scheduled departure (`hold_at`: `all` or
   `timepoints`), `duration` = `dwell_s`. Times are seconds after midnight of the
   service day, matching `periods.py`. The vType `bus` comes from
   `demand.write_vtypes`/`write_general_vtypes`, not from these files.
6. **Bus status** pairs each vehicle's scheduled calls with SUMO `stopinfos.xml`
   (stop output) of the period run: arrival delay (`started` − scheduled arrival) over
   calls scheduled in [start, end − 10 min] (mean, 90th percentile, unreached share),
   simulated vs scheduled run time and speed for trips completed in the run, and at
   the busiest stop the headway coefficient of variation and bunching (share of
   headways < 0.5 × scheduled). Status: the worse of mean delay (< 2 / 5 / 10 min)
   and p90 delay (< 5 / 10 / 20 min) gives on time / minor / major / severe; more
   than 25 % unreached calls (buses teleported past simulated jams) is `model gap`
   rather than a delay class. Periods without stop output report
   `schedule only`; `no service` and `not simulated` (unmatched) are explicit.
   Thresholds are written into `bus_status.json`.

`validate` runs a buses-only SUMO period on the network and writes
`<period>/validate/{stopinfos,tripinfos,statistics}.xml` and `validation.json`
(stops reached, teleports, warnings). `python3 -m unittest tests.test_corridor_gtfs`
covers the bbox filter, service-day selection, clipping, schedule metrics, matching
on a tiny grid (skipped without SUMO) and the status computation with a fixture
marked synthetic.
