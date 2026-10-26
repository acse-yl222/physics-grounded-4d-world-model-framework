# corridor_sumo

SUMO traffic simulation for Overture-based city scenes (first user: `imperial_corridor`,
8 km × 8 km around Imperial College South Kensington and White City). By default the car
demand is calibrated to UK Department for Transport (DfT) road traffic counts and
simulated for configurable clock hours (AM peak, inter-peak, PM peak); the output is a
protocol v1.1 run with per-edge traffic state (flow, speed, density, level of service)
and one sparse `trajectories` layer plus a compact viewer binary per period.
`--synthetic` keeps the earlier single window with synthetic random demand.

```sh
python3 -m pip install eclipse-sumo rtree   # SUMO binaries + tools; rtree speeds up sumolib
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
| `run.py`          | end-to-end CLI                                                          |
| `sumo_env.py`     | locating SUMO binaries, tools and `sumolib`                             |

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
4. **Matching.** Overture edges carry street names, not route numbers, so a count point
   direction goes to the nearest passenger edge within `match.radius_m` whose class fits
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
   `simulation.mesosim` (default true for `imperial_corridor`) uses SUMO's mesoscopic
   model without junction control (overtaking, interpolated FCD positions): microscopic
   runs of the calibrated demand on this Overture network deadlocked at junctions
   (≈ 75 000 teleports in the AM peak, network mean speed < 1 m/s), and mesoscopic runs
   take minutes instead of ≈ 25 min per period. `max_depart_delay_s` drops vehicles that
   cannot enter (counted in statistics), `extra_options` passes further SUMO options.
   edgeData over the measured hour at 300 s and 3600 s (all vehicles) and 3600 s for
   general traffic only (GEH check). Mesoscopic caveats: without junction control,
   signals cause no delay, so speeds on uncongested edges are optimistic; interpolated
   FCD positions can step back by tens of metres when a queued vehicle's segment exit is
   delayed (about 10 % of moving steps in `heading_vs_motion`).
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
- `traffic_<period>.json` + `.bin` (format below) and `trajectories_<period>.json`
  (one protocol `trajectories` layer `traffic_<period>` each) for the last
  `periods.fcd_window_s` seconds of the hour. Manifest samples are seconds since the
  window start (same length for all periods); the viewer index `t0` is seconds since
  midnight.

## Count-based hourly state (`count_state.py`)

The calibrated periods carry only part of the observed flow on this network (see the
fit in provenance), so `count_state.py` gives an observation-led estimate for every
hour 07:00-19:00 on counted roads: DfT directional AADF x weekday hourly share for the
flow; assumed lanes and per-lane capacity by road type; HCM 2000 signal control delay
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
