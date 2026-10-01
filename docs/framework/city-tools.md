# South Kensington / White City shared city tools

Both canonical scenes expose the same geometry, wind, temperature, solar,
pollution-tracer, flood, traffic, daylight-thermal and public-transport interfaces.
UAV and bird remain outside this parity requirement. Interface parity does not
mean identical geography, grid resolution, forcing, calibration or scientific validity.

## Entry points

Use a Python environment with the dependencies required by the selected solver.
The local traffic/geometry environment was installed from `tools/requirements-city.txt`;
the thermal diagnostic uses the existing physics-toolkit PyTorch environment.

```sh
PYTHONPATH=src cache/traffic_env/bin/python -m common.cli city catalog
PYTHONPATH=src cache/traffic_env/bin/python -m common.cli city audit
PYTHONPATH=src cache/traffic_env/bin/python -m common.cli city call white_city field.sample --arguments '{"module":"wind","x":0,"y":0,"time_s":100}'
PYTHONPATH=src cache/traffic_env/bin/python -m common.cli city call south_ken traffic.run --arguments '{"duration":300,"speed_factor":0.7,"seed":42}'
```

`pipeline.run` accepts a `run_id` for continuing dependent stages in the same
workspace. A fresh wind-only run correctly reports missing geometry; it does not
reuse an arbitrary previous cache directory. Large wind/thermal runs retain their
existing solver/environment requirements. No new generic tool implies that a
solver's weights have been calibrated for both cities.

## Traffic

```sh
PYTHONPATH=src cache/traffic_env/bin/python -m traffic.sumo_pipeline fetch south_ken
PYTHONPATH=src cache/traffic_env/bin/python -m traffic.sumo_pipeline run south_ken --retain
PYTHONPATH=src cache/traffic_env/bin/python -m traffic.transport south_ken
PYTHONPATH=src cache/traffic_env/bin/python -m traffic.transport south_ken --resume
PYTHONPATH=src cache/traffic_env/bin/python -m traffic.observations
```

Replace `south_ken` with `white_city` for the identical workflow. OSM snapshots
are retained in scene inputs, with source URL, checksums and individual tiles.
Networks explicitly use left-hand traffic and a buffered geographic extent.
Demand uses fixed-seed random trips; signals use guessed actuated programmes.
White City's inherited fitted rotation/scale/translation and South Kensington's
authoring map are preserved in scene configuration. These are inherited model
alignment estimates, not new survey control.

Every complete SUMO run retains source/configuration, OSM, network, routes,
SUMO configuration, logs, trip summaries, full and display-cropped trajectories,
signal states and protocol manifest. The displayed road and vehicle crop does
not change network-wide traffic statistics. The speed intervention is applied
through TraCI: rerunning `run.sumocfg` alone does **not** reproduce that intervention.
Use the retained source snapshot and `config.json` with the shared runner.

TfL context retains dated API responses. Resume only fetches missing responses,
preserving the original timestamps of successful requests. DfT raw historical
hourly counts are saved separately from synthetic demand. The system does not
label random trips or TfL arrival predictions as observed origin–destination demand.

## Physics and planning

`common.city import-fields` registers original arrays with their own time axes,
sample heights and explicit invalid masks. It does not recompute legacy physics.
Solar clocks use recorded UTC or Europe/London local timestamps with DST.
`field.sample` refuses spatial/time extrapolation.

`urban_flow.physics.city_diurnal prepare SCENE` retains compact inputs from the
configured legacy source directories; `run SCENE --device cuda` uses those retained
inputs. Both scenes use the same state-carrying 3-D thermal solver, 32 m horizontal
/ 8 m vertical grid, first 64 m of the atmosphere, one frozen 3-D wind snapshot,
and recorded summer solar forcing. It is a controlled daylight diagnostic with
constant ambient temperature and uniform surface parameters. White City's
artificial SCALED ground plane is excluded from the thermal building mask.

`urban_planning.city_prepare SCENE` prepares the same direct-radiation panel
siting task on scene-specific shadows. It uses hypothetical flat-ground sites;
the historical South Kensington DTM pilot remains separate. Planning sessions
write into cache, leaving frozen task inputs intact. The existing budgeted tools,
RSI runner and curriculum accept both scenes and reject cross-scene input mixing.
The parity lifecycle tests use a **fixture provider**, not an LLM performance benchmark.

South Kensington's solver-only GLB is created by `tools/bake_city_geometry.mjs`.
It bakes active-scene node transforms and preserves material names; it omits
textures/normals. The original visualization GLB stays intact. Node dependency
versions are in `tools/requirements-city-node.json`.

## Validation and limits

```sh
PYTHONPATH=src cache/traffic_env/bin/python -m common.city_validation
python3 tools/check_contract.py examples/contract-v1/manifest.json
PYTHONPATH=src cache/physics_toolkit/venv/bin/python -m unittest discover -s tests -v
node --test tests/test_viewer.mjs
```

`tests/browser_city_parity.cjs` checks all selected module views and both integrated
traffic/geometry views. Set `PUPPETEER_MODULE`, `CHROME_PATH` and `UWM_VIEWER_URL`
for the local browser environment. Scene configurations name selected runs; no
result is selected by file modification time.

Remaining scientific work: map and validate DfT observation points against
directional edges; estimate and independently validate demand; obtain/validate
signal timings; check congestion across longer warm-start runs. Legacy pollution
remains a normalized tracer, thermal/weather settings remain controlled scenarios,
and existing refined geometry has not triggered a complete new coupled CFD/solar/
flood campaign. These limits apply to both cities. No datasets or site changes
were published by this integration.
