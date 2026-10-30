# Birds in framework scenes

Runs the bird flock model (`urban_geometry.birds.sim`) inside a framework scene and writes a bird
replay that the city viewer shows in every scene that has one. The birds use the scene's own city
geometry, its published wind / pollution / temperature fields and its sun; roost and forage sites
are chosen from the scene's land cover. Like the UAV layer, the replay is computed offline once per
scene and played back by the viewer on its own clock.

## Pipeline (per scene)

```bash
# 0. once, at the repository root: the GLB baker's packages (Node 22+; not saved to package.json)
npm install --no-save @gltf-transform/core@4 @gltf-transform/extensions@4 @gltf-transform/functions@4 meshoptimizer
pip install -e '.[birds,geometry]'   # scipy, numba, Pillow, DracoPy (the voxeliser's dependencies)

S=white_city                          # or south_ken, tower_hamlets
W=cache/$S/birds                      # any work folder

# 1. the scene's published scene.json and field frames (or point --fields at a local scenes/<id> folder)
PYTHONPATH=src python -m urban_geometry.birds.scene.run fetch-fields --scene $S --dest $W/scene

# 2. the scene's city GLB (scene.json model.parts_manifest, SHA-256 checked) and supplement, if any
PYTHONPATH=src python -m urban_geometry.birds.scene.run fetch-model --scene $S --fields $W/scene --dest $W/models

# 3. geometry: bake + framework voxeliser (2 m) + land cover (~1 min); the fetch-model output
#    prints the exact command, including --supplement for South Kensington
PYTHONPATH=src python -m urban_geometry.birds.scene.run prepare-geometry --scene $S   --glb $W/models/<city>.glb --out $W/voxel_2m

# 4. run (4 flocks x 300 birds, dt 0.05 s, over the span of the scene's wind frames)
PYTHONPATH=src python -m urban_geometry.birds.scene.run run --scene $S --geometry $W/voxel_2m --fields $W/scene
```

Scene IDs: `south_ken`, `white_city`, `tower_hamlets` (Canary Wharf). The viewer IDs
`south_kensington` and `canary_wharf` are accepted too.

| step | what it does |
|---|---|
| `prepare-geometry` | `bake_glb.mjs` decodes meshopt/quantisation, applies every node transform, drops textures and the animated demo actors (South Kensington birds and traffic, the layers the viewer already hides); the unchanged framework voxeliser `urban_geometry.voxelization.prepare_glb` writes the standard 2 m geometry directory; `landcover()` adds 2 m masks for low vegetation, tree crowns and water using `prepare_glb`'s own classifier plus the city viewer's tree conventions. |
| `fetch-fields` | downloads `scene.json`, `physics/manifest.json`, `physics/web/index.json` and the wind / pollution / temperature frames from the public site. |
| `fetch-model` | reassembles the city GLB from the resource catalogue's parts (each SHA-256 checked) and downloads `model.supplement` (South Kensington's 306 added buildings). |
| `run` | chooses one roost and its own forage sites per flock (`placement.py`), crops the bird geometry around each flock, runs each flock roost to roost in its own process (`--flocks`, `--n-birds` per flock, `--workers`) and merges them into one replay. |

## Outputs

`project/<scene>/input/<version>/` (default version `birds_YYYYMMDD`):

- `bird_replay.json`, `bird_replay.i16`, `bird_states.u8`: the viewer replay (schema `uwm-bird-replay-2`,
  see `export.py`); ~36 MB for 1200 birds over 2500 s at 1 frame/s.
- `bird_replay.json` also records, per flock (`flocks`: its birds, sites and why they were chosen,
  its moments: Roosting, Leaving the roost, Foraging, Heading home, Murmuration, Settling), the field
  sources and their encodings, the sun clock, the resolved configuration and run checks (non-finite
  positions, birds inside buildings, states seen, fraction roosted at the end).
- `provenance/` (geometry metadata) and `work/bird_geometry_<flock>.npz` (the cropped collision
  grids; not needed by the viewer).

`project/<scene>/configs/bird_visualization.json` points the viewer at that replay (it mirrors
`uav_visualization.json`). `project/*/input/` is git-ignored like the UAV routes; add the replay
files with `git add -f` when they should be published.

## Viewer

`src/visualization/legacy/viewer/3d/bird-layer.js` loads `bird_visualization.json` for the current
scene. South Kensington shows it inside its existing replay (Birds tab, bird tracker); the earlier
`agents/demo_rev02/data/birds*` replays remain a fallback. Every other scene with a bird config gets
a Birds tab and layer toggle; the Birds shot orbits the flock, plays the day on its own clock
(default 10x, the step slider seeks) and labels the local time. In both, the bird panel has a flock
picker (the camera follows that flock's largest group) and a "Jump to" menu (start / middle of each
moment of that flock's day). Scenes without a config are unchanged.

## What the birds take from the scene

| input | source | note |
|---|---|---|
| buildings | the scene's city GLB through `prepare_glb` (2 m) | the GLB the viewer shows, so birds align with it |
| roost / forage sites | land cover from the same GLB | per flock, not shared: forage on parks, then waterside ground, then flat roofs (open columns only, no solid voxel, and 16 m clear of anything taller than 8 m, where the model's route guidance can stop short of a site); roosts: flat roofs near forage, ~1 km apart |
| wind | the scene's published wind frames (`scene.json` layer `wind`) | 2-D slice at one height (8-12 m South Kensington, 8-16 m White City, 2 m Canary Wharf) applied at every altitude |
| pollution | published pollution frames | arbitrary tracer units scaled to 0-1 by the 99th percentile over the bird domain |
| temperature | published temperature frames | degrees C as published |
| daylight | the scene solar run's sun altitudes (`physics/manifest.json`) for `--date` | Canary Wharf publishes no daily solar run or georeference: `urban_flow.physics.solar.model.sun_position` at Canary Wharf's public coordinates |
| noise | none in the framework | the bird model's own (no sources) |

Each field is mapped onto bird time with its `scene.json` `t0_s` / `step_s` (the viewer's mapping)
and held at its ends. The run spans the wind frames (2500 s South Kensington, 5000 s White City,
10000 s Canary Wharf), into which a whole local day from 45 min before sunrise to 1 h after sunset
is compressed: birds start and end on the roost. Light is sin(altitude) / sin(noon altitude), which
keeps the bird model's light thresholds near sunrise, late afternoon and sunset. The default date
is 2026-12-21 (murmurations are a winter behaviour; the scenes also have 2026-06-21).

## Changes to the bird model

All optional and off by default (standalone results are bit-identical to before):

- `SimConfig.external_fields`, read by `environment.get_environment` and `wind.get_wind`;
- `SimConfig.day_clock`, read by `environment.day_phase` / `day_fraction`;
- `SimConfig.route_cell_m`: wave routing on a coarser copy of the geometry (`integrator._routing_geometry`),
  so 2 m collision grids do not explode the routing graph; the routing cache key is computed once.
- `SimConfig.route_block_fraction` (`run --route-block-fraction`): share of a coarse routing cell that must be
  solid to block it; 0 (default, the shipped replays) = any solid voxel, 0.5 = at least half, which keeps
  sites right beside tall buildings reachable at the cost of routes passing closer to walls.

## Limits

Heuristic site placement, not a survey; the fields are 2-D published slices, not the 3-D solver
output; obstacle avoidance is a soft force (the run checks report any flying samples inside
buildings); not an ecological validation.

## Checks

`python -m unittest tests.test_birds_scene` (synthetic fixtures) and, with a served viewer and a
replay, `node tests/browser_scene_birds.cjs` (see its header).
