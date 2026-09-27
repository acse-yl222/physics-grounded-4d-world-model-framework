## Geometry expansion (2026-09-13)

35 refined building assets are integrated locally with reversible **Building refinements** comparison. [Current status and artifacts](geometry/expansion/docs/STATUS.md). A user-authorized continuous Codex goal is extending the adjacent frontier; no independent local daemon is installed. Facades without confirmed target references remain artistic estimates.

# Urban World Model Visualiser

Interactive 3-D web page for the urban world model scenes. Each scene is one folder under `scenes/` (city model, physics
fields, masks, optional transport / replay layers) described by a `scene.json`; the viewer loads whichever scene
`?scene=<id>` names (selector in the page's top-left corner). Two scenes so far:

| scene | content |
|---|---|
| `south_kensington` (default) | South Kensington core008: wind, temperature, sunlight, day cycle, pollution and flooding on the 4 m grid (768 × 704 cells), the packed city model with the OSM supplement and the building refinements, and the traffic / UAV / bird replay from `agents/demo_rev02/` |
| `white_city` | White City 9 km² (Television Centre, Westfield, the Imperial White City campus): 2 m voxel geometry from the uploaded GLB, SCALED wind (8 m frames, 100 steps of 50 s), 3-D physical temperature (21 frames), tracer pollution (100 frames), sunlight (8 m irradiance every 10 min, 2 m shadows) and flooding (37 frames of a 3 h cloudburst) from the workstation run `output/white_city`, plus a **TfL transport layer** (tube / rail lines, bus routes, stations with live arrivals, bus stops, road disruptions and JamCam cameras from the TfL Unified API, placed with a georeference fitted on 939 named OSM buildings, median residual 1.6 m) and a **SUMO traffic replay** (one hour of random trips on the OSM road network with guessed actuated signals: cars, signal heads and lane ribbons, `scenes/white_city/traffic/`) |

## Layout (scenes since 2026-09-16)

| Folder | Content | Size |
|---|---|---|
| `scenes/<id>/models/` | the packed 3-D models the viewer loads (South Kensington: `south_kensington_core008_web.glb` 254 MB, `buildings_supplement.glb`, the station tile; White City: `white_city_9km2.glb` 191 MB meshopt) | 0.5 GB |
| `scenes/<id>/physics/` | the physical fields on the scene's grid: `.npy` arrays, `manifest.json`, `web/` (pre-rendered PNG frames), South Kensington also `metadata/`, `figures/`, `README_source_run.md` | 1.4 + 0.6 GB |
| `scenes/white_city/transport/` | the TfL snapshot (`raw/`) and `transport.json` in model coordinates; `georef.json` next to it | 6 MB |
| `scenes/tools/`, `scenes/<id>/tools/` | the frame pre-renderer; per-scene export scripts (White City: run output → arrays, TfL fetch, georeference, transport build) | |
| `assets/` | the South Kensington geometry split into one GLB per object, classified; `index.json` catalogue; built by `assets/tools/build_asset_library.mjs` | 1.3 GB |
| `geometry/completion/` | the 306-building OSM supplement: audit, scripts, sources, reports, editable `.blend` | 0.1 GB |
| `geometry/expansion/` | the building-by-building refinement task: per-batch manifests, modules, references, renders, `.blend` masters in `output/` | 6 GB |
| `agents/demo_rev02/` | the colleague's traffic / UAV / bird replay package (data, evidence, modules) | 85 MB |
| `viewer/` | the three.js page (`viewer/3d/`: `main.js`, `transport.js`, `replay.js`, `tile.js`, `expansion.js`, `proxy.js`), the scene loader (`viewer/scene.js`), the `.npy` Range reader (`viewer/npy.js`), the PNG frame decoder (`viewer/frames.js`) | |
| `vendor/` | one copy of three.js 0.185.1 with the fat-line addons and the Draco decoder; `agents/demo_rev02/vendor` is a symlink to it | 3 MB |
| `docs/` | GitHub Pages project page, refinement progress page, their media and generators | 15 MB |
| `tools/` | repository-level scripts (`migrate_layout.py`) | |

Entry points stay at the root: `serve.py` (static server with Range support, opens `/viewer/3d/`), `start_server.sh` (workstation).
Everything under `*.glb`, `*.npy`, `*.blend` and `geometry/expansion/output/` is git-ignored except the small masks the viewer
reads; see `.gitignore` and `scenes/README.md` (the `scene.json` schema and how to add a scene).

## Online

- **Live viewer**: https://acse-yl222.github.io/urban-world-model/viewer/3d/ (GitHub Pages; the 254 MB South Kensington model and the 191 MB White City model are fetched in parts from the companion repository https://github.com/acse-yl222/urban-world-model-models, whose Pages site allows cross-origin reads; the `models-v1` release holds the South Kensington file for download). White City: https://acse-yl222.github.io/urban-world-model/viewer/3d/?scene=white_city
- **Project page**: https://acse-yl222.github.io/urban-world-model/docs/
- Repository: https://github.com/acse-yl222/urban-world-model

Phones, tablets and machines that report 4 GB or less get **lite mode** automatically: the buildings are 4 m voxel columns
extruded from the physics masks (2 MB, loads in a few seconds) instead of the 254 MB model, everything else (fields, traffic,
UAVs, birds) is the same. `?lite=1` forces it on any device, `?lite=0` forces the full model. On narrow screens the layer
panel folds behind a **Layers** button.

## Start locally

```bash
cd UrbanWorldModelVisualizer
python3 serve.py          # opens http://localhost:8787/viewer/3d/ (next free port if busy)
python3 serve.py 9000     # custom port
```

Only the system Python 3 is needed, no numpy. `serve.py` is a static server with HTTP Range support. The page plays the
fields from the scene's `physics/web/` when it exists: one small PNG per frame (65–500 KB; written by
`uv run --with numpy,pillow python3 scenes/tools/export_web_frames.py <scene>`, ~100 MB for the twelve South Kensington layers), decoded back to
values in the browser to 1/255 of each layer's range. Without that folder it reads the frames straight from the `.npy`
files by Range request (1–9 MB per frame, fine locally, too slow over a remote link). Playback never cancels a frame that
is still loading, so a slow link lowers the frame rate instead of freezing the picture.

## 3-D view (`viewer/3d/`)

`http://localhost:8787/viewer/3d/` (`/web/` redirects there). Loads `south_kensington_core008_web.glb` (254 MB, three.js +
meshopt decoding; three.js is served from `agents/demo_rev02/vendor`, the isotherm line modules from `vendor/three/examples/jsm/lines`, so no
network access is needed). The page runs one loop with two parts:

1. **Campus tour** (traffic and UAVs from `agents/demo_rev02/`): campus overview (an orbit descending towards the Imperial College
   buildings) → the busiest signalised junction on the campus ring roads (only junctions within 165 m of the campus buildings,
   i.e. Kensington Gore / Exhibition Road and Queen's Gate) → traffic map (near-vertical view over the ring roads with the
   drivable lanes highlighted in blue, cars as white / amber dots for moving / stopped and every signal head as a red / amber /
   green dot) → a wide UAV view (high orbit over the campus showing the nearby hubs and rooftop stations; UAV models enlarged 4×
   with screen-space dots and the flight corridors drawn). Cars are the SUMO replay, UAVs the NVMF schedule replay, signals read the recorded states.
   Birds (100 pigeons from Akira's flock model, `agents/demo_rev02/birds.js`; instanced low-poly pigeons with display-only wing
   flap, purple "Birds" toggle in the panel) are counted in the stats. The page loads `agents/demo_rev02/data/birds_southken/` first:
   our own one-hour run of the unchanged model focused on South Kensington station (roost on the station roof, forage sites
   within 90 m; geometry = the 4 m wind-model building voxels cropped to X 600–1300 / Z 350–1050, built by
   `tools/birds/build_bird_geometry_southken.py`; run with the colleague's `run_city_v3.py` wrapper plus a `--roost-near /
   --forage-near` option; evidence in `evidence/birds/southken_100birds_3600s_EVIDENCE.json`). The colleague's campus run
   stays in `data/birds/` as the fallback. The **Birds** tab tracks the flock; the **Bird tracker** panel section follows the
   flock centroid or a single bird (auto orbit / behind camera, or free orbit). The replay clock
   runs the full hour of the UAV schedule (600 deliveries) and the bird run; the repository only ships the first 300 s of
   the traffic replay, so the cars and signal states loop inside that window (shown in the stats) until the full-hour files
   are dropped into `agents/demo_rev02/data/traffic/replay/`.
2. **Fields overhead**: climb to the overhead view, hide the ground, roads, trees and the traffic layers, then play the wind
   speed field, the temperature field, the sunlight, the day cycle, the pollution field and the flooding field one after another
   (12 steps/s by default, the flood and the day cycle at 2 frames/s), and return to the campus tour. The six tabs
   **Wind / Temperature / Sunlight / Day cycle / Pollution / Flooding** jump straight to one field.

Layers: wind speed as a heat map at 10 m (building cells cut out, optional streamline particles); temperature as a ground heat
map (transparent outside the study area and inside buildings) or as isotherms (every 0.1 °C, broken at walls); pollution as a
translucent concentration layer at 14 m (log opacity); flooding as a water-depth layer on the ground (`scenes/south_kensington/physics/flood/`,
1 m shallow-water run of a 3 h 2021-type cloudburst exported as 4 m block means: `depth_4m_tyx.npy`, 19 frames every 10 min,
its own clock; depth ≤ 0.02 m is dry, colour 0.02–0.6 m; in overlay mode the static `max_depth_4m_yx.npy` is shown). The
flood phase keeps the ground / roads and the green areas / trees visible under the water (the other fields hide them). The 1 m
static maps (max depth / speed / hazard, arrival time, DTM, footprint) are in the folder too; the 329 MB `depth_1m_tyx.npy`
was left on the workstation. The big tabs at the top jump to any view or to the physics fields;
Sunlight (`scenes/south_kensington/physics/solar/`, added 2026-09-12): the clear-sky solar model (1 m direct-beam shadows from ShadowNet, sky-view
factor, ASHRAE irradiance) for the summer and winter solstice, shown with the ground and trees visible as a sun / shade wash:
**Irradiance · 4 m, every 10 min** paints 1 − GHI / open-sky GHI as a blue-violet veil (99 frames on 21 June, 47 on 21 December,
12 frames/s), **Shadows · 1 m, on the hour** drapes the 1 m shadow mask (17 / 7 frames, 2 frames/s; 8.7 MB per frame, expanded into a
3072 × 2816 texture). The scene's sun light follows the frame's real sun position. Day cycle (`scenes/south_kensington/physics/temperature3d_solar/`):
Yi Qi's 3-D temperature model driven by that solar model over 21 June, hourly 05:00–24:00 (20 frames, 2 frames/s), as ground surface or
air (0–4 m, 12–16 m) temperature, either in °C or relative to the hour's ambient air temperature (default; ±12 °C for the surface,
±3 °C for the air). URL options: `?pose=overhead&phase=solar&solar=shadow&day=20261221&step=4`, `?phase=diurnal&diurnal=air0Rel`.
"Auto loop" off holds the current view; dragging the view interrupts a flight. "Map markers" in the panel turns the traffic-map
dots and lane highlight on in any view. The overlay mode lets you combine layers manually.
URL parameters: `?pose=overhead&step=80`, `?pose=campus&shot=junction&t=120&hold=1`.

Alignment between the grid and the model (top of `viewer/3d/main.js`): model X = domain x − 2116, model Z = −(domain y − 2124),
Y up; i.e. the manifest's region coordinates are the model's (X, −Z). Verified against the building extent in the README of the
data. SUMO → world: X = x − 2912.594719173, Z = 1704.705026026 − y (from the demo_rev02 README).

## South Kensington station detail tile (2026-09-12)

**Off by default** (the user found its colours too jarring next to the main model); add `?tile=1` to the page URL to load it.
`south_kensington_current.glb` (180 MB, Blender export) is a detailed model of a 390 × 400 m plate around South Kensington
station: 245 OSM buildings with PBR facades, the station with its arcade, open railway cutting and platforms, roads and
footways, gardens, trees and street lamps. `viewer/3d/tile.js` loads it next to the main model. Its local frame is rotated
against the main model by the UTM grid convergence, so it is placed with a rigid transform fitted on the 237 buildings the
two files share (OSM ids from the node extras): model X/Z = tile rotated by +0.03799 rad about Y and moved by
(901.85, 689.57) m, lifted 0.3 m; the residual is about 0.7 m (median). Inside the plate the main model's ground, roads and
paths (and the dark base plate) are clipped away (clipping planes), its copies of the tile's buildings (same OSM id),
planting, parked cars and other street items are hidden, and the three buildings only the main model has stay; outside
the plate the tile is clipped. The tile's illustrative parked cars stay hidden because the SUMO replay already draws the
traffic. **Station detail tile** in the panel switches all of this off and restores the main model.
`?cam=px,py,pz,tx,ty,tz` puts a fixed free camera anywhere (used for screenshots). The earlier
`south_kensington_paused_20260910.glb` is no longer used.

## Deployment on the workstation (ESE-YL222)

The project is synced to `~/workspace/UrbanWorldModelVisualizer` on the workstation. Start / restart:

```bash
ssh ESE-YL222
cd ~/workspace/UrbanWorldModelVisualizer && ./start_server.sh      # 0.0.0.0:8787, log in server.log, pid in server.pid
```

- **Public URL (anyone)**: https://ese-yl222.tail8083c2.ts.net/viewer/3d/ , published with Tailscale Funnel (the college network
  blocks the domain and port used by Cloudflare Tunnel). Check / stop / republish: `tailscale funnel status`,
  `tailscale funnel --https=443 off`, `tailscale funnel --bg 8787`.
- Inside the Tailscale network: http://100.84.141.116:8787/viewer/3d/ . On campus / VPN, and from outside over IPv6:
  http://ese-yl222.ese.ic.ac.uk:8787/viewer/3d/ (IPv4 inbound is firewalled).
- Sync local changes: `rsync -az --exclude .DS_Store ~/Desktop/UrbanWorldModelVisualizer/ ESE-YL222:workspace/UrbanWorldModelVisualizer/`.
- Remote viewers get roughly 20 Mbps through the Funnel; the fields play from the pre-rendered PNG frames in the scene's `physics/web/`
  (temperature / pollution / flood / sunlight at full rate, wind at about half rate because its RGB frames are ~470 KB).

## Files

- `serve.py` — local server with Range support; `start_server.sh` — detached start for the workstation
- `viewer/index.html` — redirect to the 3-D page
- `viewer/npy.js` — shared `.npy` Range reader module
- `viewer/3d/` — 3-D page (three.js); `replay.js` wraps the demo_rev02 traffic / UAV modules
- `vendor/three/examples/jsm/lines/` — three.js fat-line modules
- `south_kensington_core008_web.glb` — 3-D model
- `scenes/<id>/physics/` — field data and notes (see `README_source_run.md` and `manifest.json` inside); `solar/` and
  `temperature3d_solar/` hold only the arrays the viewer plays (the 1 m SVF / sunlit-hours / daily-irradiation maps and the
  single-time native-vs-coupled comparison stay on the workstation copy)
- `docs/` — GitHub Pages project page (`docs/index.html`, figures in `docs/media/`)
- `agents/demo_rev02/` — traffic / UAV replay package; `birds.js`, `actors/pigeon.glb` and `data/birds/` were updated from the
  `demo-rev02` branch of `UrbanWorldModel/uwm-group1` on 2026-09-12 (bird layer), the rest is still the earlier revision

## Missing-building supplement (2026-09-12)

**2026-09-13 expansion update:** three further buildings—25 Kensington Gore, 41–45 Jay Mews and 29 Exhibition Road—are integrated locally. **Building refinements · 4** compares all four refined buildings with their originals. This batch uses building/street photographs and official architectural descriptions, with estimated and artistically completed details recorded explicitly. [Batch 02 status, renders and editable files](geometry/expansion/batch02/docs/STATUS.md).

The local viewer also includes a one-building expansion pilot at **23 Kensington Gore**. **23 Kensington Gore · imagined detail** compares the new model with its original exterior; `?expansion=0` starts with the original. This retains the mapped footprint and existing entry position but artistically completes facade/roof details using neighbourhood references. See [pilot status and checks](geometry/expansion/docs/STATUS.md) and [render](geometry/expansion/output/kensington_gore_23_v1/front.png). Physics fields are unchanged. Which buildings are authored, procedural, supplemented or refined is recorded in `geometry/building_record.md` (and `.json`), not shown in the viewer.

The local viewer loads `geometry/completion/output/buildings_supplement.glb` (306 OSM footprints, 3.6 MB). Use **Added buildings · 306** to compare. The original model remains intact; the existing South Kensington detail-tile clipping also applies to the supplement. Heights and facades are estimated. The original physics fields have not been recomputed. See [audit, sources and limitations](geometry/completion/docs/STATUS.md); satellite-only omissions remain unverified. Editable supplement: `geometry/completion/output/buildings_supplement.blend`.
