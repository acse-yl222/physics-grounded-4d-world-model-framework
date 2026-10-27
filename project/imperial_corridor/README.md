# Imperial Corridor

The user-supplied Claude presentation is preserved as the baseline for this
scene. Original exported data is retained at immutable resource revision
`e45d08934593fd3729f22dc0fd128acc3b519cac`; it is never overwritten by new results.
The original SUMO input project and signal timings were not supplied.

## What changed

- Geographic solar direction for London date/time, including daylight saving;
  building shadows, adjustable cloud cover and daylight-dependent sky lighting.
  Sky/cloud brightness is illustrative, not a measured irradiance calculation.
- Vehicle classes now have distinct bodies and nominal dimensions; trucks and
  motorcycles are no longer stretched hatchbacks. Selecting a vehicle reports
  its identity, dimensions, and rebuilt speed/elevation where available.
- Exact recorded positions replace inferred lane routes and queue compression.
  Adjacent samples interpolate without future-window smoothing; missing samples
  and implausible jumps remain discontinuous. Playback stops at the last sample.
- A new, explicitly experimental microscopic SUMO alternative adds car following,
  continuous lateral movement and conservative exclusive junction reservations.
  Original recorded replay remains available for comparison.
- Underground geometry and timetable presentation are unchanged.

## Rebuilt traffic: assumptions and limits

The network is reconstructed from exported normal-lane geometry, permissions,
connectivity and junctions. SUMO regenerates internal junction geometry and
actuated signal plans; these are not the real London signal timings.

Demand uses a deterministic 25% sample of the source vehicle routes. Routes with
teleports, disconnected edges, departures outside the window, or insufficient
initial storage are excluded and counted. There is a 120-second warmup from an
empty network. This is a visual/safety experiment, **not calibrated traffic flow**.
Buses follow recovered routes without reconstructed stops or service schedules.
Road-state and transit overlays still describe the original source model.

SUMO 1.28.0 runs at 0.1 s with seed 42, 1.2 s following time and 2.5 m minimum gap.
An experimental reservation controller groups junctions joined by links shorter
than 20 m and admits one vehicle per conflict area until its rear clears it.
Vehicles may not spawn within these combined conflict areas. Non-owners brake before the junction. This intentionally
reduces throughput; it does not reproduce London signal operation. Jam teleports
are disabled. Publication checks reject a run containing reported collisions or
teleports. Zero detected collisions in these finite runs is not a general safety
certification. Emergency braking and congestion remain diagnostic limitations.

The web replay retains position, heading, elevation and speed at 0.5 s. Protocol
trajectory frames retain every second sample (1 s), with IDs `v<index>` mapping to
the ordered vehicle list in `traffic.json`. Each protocol run retains compressed
network/routes, source snapshot, reproduction command and validation report.

## Spatial and time semantics

Origin: longitude -0.200473, latitude 51.506427. ENU metres map to the Three.js
viewer as `(east, up, -north)`. Rebuilt vehicles use SUMO lane elevation. The
original elevation survey datum is unknown; this is not surveyed bridge geometry.
Original replay has no elevation and follows the exported road surface.

Windows start at 31800, 49800 and 64200 source clock seconds. No UTC epoch is
inferred. Protocol runs use relative seconds; metadata retains the source clock.
The sunlight clock is explicitly independent of the traffic replay clock.

## Rebuild

Install the repository plus `eclipse-sumo==1.28.0 libsumo==1.28.0`. Run
`python -m traffic.rebuild_corridor --help` for the input/output and executable
arguments. Scratch goes under `cache/imperial_corridor/traffic/`; completed results
are retained outside the code checkout with `traffic.export_corridor_micro`.

`python3 tools/build_corridor_site.py EXPORT_DIR SITE_DIR/scenes/imperial_corridor`
packages the local presentation. `--data-url` selects an immutable raw GitHub
resource directory; `--micro-url` selects validated period folders. The narrow
builder does not modify other site routes or copy workspace/cache/history files.

Run `node --test tests/test_corridor.mjs`, the corridor build tests,
`make test-e2e`, and `node tests/browser_corridor.mjs PACKAGED_SCENE_URL`.

## Sources

The preserved bundle/shell are in `src/visualization/corridor/vendor`; readable
adapters and SUMO computation are separate. Data attribution remains visible:
OpenStreetMap/Overture ODbL and DfT/BODS OGL as supplied in the export. Original
procedural models have no separately supplied license; publication is at the
owner's request, not a new blanket license declaration.

Reconstruction follows [SUMO PlainXML](https://sumo.dlr.de/docs/Networks/PlainXML.html)
and uses [SUMO collision checks](https://sumo.dlr.de/docs/Simulation/Safety.html).
