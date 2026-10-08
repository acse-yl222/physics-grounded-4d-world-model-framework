# Wave PDE ground-station routes

This module computes directed routes for the 30 South Kensington ground stations.
Each route includes a vertical 30 m ascent, a 3D Wave PDE route, and a vertical
30 m descent. The intermediate path is not constrained to a constant altitude.
It uses the `wavepde.torch_backend` numerical library; no scheduling is involved.
The separate WavePde-UAV-Path-Model repository remains the solver's source of truth.

## Reproduce

Use Python with the Wave PDE package, PyTorch/CUDA, NumPy and SciPy installed.
For example, install the companion checkout with `pip install -e /path/to/WavePde-UAV-Path-Model`
in an environment with a compatible PyTorch build. From this framework root:

```bash
PYTHONPATH=src /path/to/torch-env/bin/python -m uav_routing.compute \
  --geometry project/south_ken/input/wavepde_geometry_2m \
  --station-file project/south_ken/input/stations_ground_20261007/stations.json \
  --ground-mode --output cache/south_ken/wavepde/my_run
```

The scene data is local, not included automatically with a source checkout.
The input height map comes from the baked city GLB and the existing
`urban_geometry.voxelization.prepare_glb` adapter at 2 m resolution. Compute uses
8 m maximum pooling, one-cell horizontal building padding and solid columns.
The retained reference run is `wavepde_ground_20261007_8m`. Its manifest records
input hashes, source snapshots, all 870 paths, and independent validation results.
Raw wave detector times are uncalibrated and are not flight durations. Reported
flight durations integrate the anisotropic no-wind model along the complete path.
Use a fresh output directory for new inputs; identity checks protect checkpoints.

## UAV city visualization

`project/south_ken/configs/uav_visualization.json` selects the route export.
Export a compatible retained ground-route run once with:

```bash
PYTHONPATH=src python -m uav_routing.export --run-id wavepde_ground_20261007_8m
```

Existing exports are never overwritten. The export is an internal legacy-viewer
adapter asset, declared in the run's artifacts, not a new protocol layer format.
`wavepde-uav-preview-1` defines little-endian float32 records
`[east_m, up_m, south_m, elapsed_s]`; each route has an offset/count and directed
station IDs. The ENU conversion is `(east,north,up) -> (east,up,-north)`.

The integrated city viewer (`src/visualization/legacy/viewer/3d/?scene=south_kensington`)
uses 300 independently moving UAVs with seed 20261007. Each picks its next outgoing
route randomly; no reverse-path shortcut is used. Initial phases are staggered,
route endpoints join continuously, and the existing time slider can seek reproducibly.
The UAV camera shot shows all current route centrelines. Existing traffic and bird
replays are retained. UAVs do not load schedules, parking plans or order data.

This is illustrative random flight, not fleet collision avoidance. Building checks
use the sampled routing grid, not continuous GLB geometry. A shared station may be
visited by multiple UAVs at once. Ground site locations are model-derived.

Checks: `node --test tests/test_random_uav.mjs`; validate the retained manifest with
`python tools/check_contract.py project/south_ken/runs/wavepde_ground_20261007_8m/manifest.json`.

## White City

The White City viewer also shows 300 independent UAVs on 870 computed directed
routes. Its 30 demonstration sites (3 hubs, 9 collection, 18 dropoff) are selected
from White City's own geometry, not transferred from South Kensington. Sites use
supported 6 × 6 m ground patches, free padded routing columns, and at least 8 m
sampled road/canopy clearance. The first is near the scene origin; the remaining
sites use deterministic farthest-point placement. These are not surveyed landing
facilities. Existing White City traffic and transport layers remain independent.

Use the prepared White City voxel directory, including `height_m.npy`, ground
height/valid rasters and 8 m asphalt/canopy masks:

```bash
PYTHONPATH=src python -m uav_routing.ground_sites --scene white_city --geometry /path/to/voxel_2m
PYTHONPATH=src python -m uav_routing.compute --scene white_city --geometry /path/to/voxel_2m \
  --ground-mode --output cache/white_city/wavepde/my_run
PYTHONPATH=src python -m uav_routing.audit --scene white_city --geometry /path/to/voxel_2m \
  --wave-repo /path/to/WavePde-UAV-Path-Model --output cache/white_city/wavepde/my_run --run-id my_run
PYTHONPATH=src python -m uav_routing.export --scene white_city --run-id my_run
```

The audit retains the source snapshot, numerical inputs and paths, and independently
checks grid intersections, endpoints, 30 m vertical legs and model travel times.
`project/white_city/configs/uav_visualization.json` selects the published preview.
The UAV tab shares the viewer's playback controls; route lines appear in this tab,
and the layer hides in physics views. Full buildings: `?scene=white_city&lite=0&pose=campus&shot=uavs&hold=1`.
Browser check: `node tests/browser_white_city_uav.cjs` with `PUPPETEER_MODULE`,
`CHROME_PATH` and optionally `UWM_VIEWER_URL` set for the test environment.
