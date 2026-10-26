# corridor_sumo

SUMO traffic simulation for Overture-based city scenes (first user: `imperial_corridor`,
8 km × 8 km around Imperial College South Kensington and White City). Output is a
protocol v1.1 run with one sparse `trajectories` layer plus a compact binary for the
web viewer.

```sh
python3 -m pip install eclipse-sumo rtree   # SUMO binaries + tools; rtree speeds up sumolib
PYTHONPATH=src python3 -m traffic.corridor_sumo.run imperial_corridor [--no-tfl]
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
| `demand.py`       | vehicle types, randomTrips cars/taxis, synthetic bus lines              |
| `simulate.py`     | headless SUMO run with FCD output                                       |
| `export.py`       | FCD parsing, vehicle selection, `trajectory_frames` JSON, `traffic.bin` |
| `run.py`          | end-to-end CLI                                                          |
| `sumo_env.py`     | locating SUMO binaries, tools and `sumolib`                             |

## Pipeline

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

All simulated vehicles are kept in FCD, but the exports carry a subset so that
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
  synthetic, binary round trip, vehicle selection and protocol validation.
