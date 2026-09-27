# Scenes

One folder per site. The viewer (`viewer/3d/`) reads `scenes/index.json` for the list and `scenes/<id>/scene.json` for
everything site-specific; `?scene=<id>` on the viewer URL (or the selector in the page's top-left corner) switches scene.

```
scenes/
├── index.json                 the scene list and the default
├── tools/export_web_frames.py pre-renders a scene's field frames into physics/web/ (PNG, ~100 KB per frame)
├── south_kensington/
│   ├── scene.json
│   ├── models/                south_kensington_core008_web.glb (254 MB, meshopt), buildings_supplement.glb, station tile
│   └── physics/               4 m grid: masks/, wind/, temperature2d/, pollution/, solar/, temperature3d_solar/, flood/, web/, manifest.json
└── white_city/
    ├── scene.json
    ├── georef.json            fit of the GLB frame to WGS84 (939 named OSM buildings, median residual 1.6 m)
    ├── models/                white_city_9km2.glb (191 MB, meshopt; from the uploaded Draco GLB via gltf-transform)
    ├── physics/               2 m / 8 m grids: masks/, wind/, temperature/, pollution/, solar/, flood/, web/, manifest.json
    ├── transport/             transport.json (TfL network in model coordinates) and raw/ (the TfL API snapshot)
    ├── traffic/               SUMO run: white_city.net.xml (OSM -> netconvert), roads.json, signal_layer.json, replay/ (cars once a second, signal states)
    └── tools/                 export_from_run.py (workstation run output -> physics/), fetch_tfl.py + build_transport.py (TfL), run_sumo.py + build_traffic.py (SUMO)
```

The big arrays (`.npy`, `.glb`) are git-ignored; the masks the viewer needs, the PNG frames, the manifests and the
transport files are tracked. The South Kensington replay (traffic / UAVs / birds) still lives in `agents/demo_rev02/`
and the building refinements in `geometry/`; the scene file only switches them on.

## scene.json

| key | meaning |
|---|---|
| `id`, `title`, `description`, `limits[]` | page chrome; the limits are listed at the foot of the layer panel |
| `grid` | the base field grid: `cell_m`, `cols`, `rows`; `x0` = model X of column 0's west edge, `z_south` = model Z of row 0's south edge (row 0 = south); `domain_origin_xy_m` and `origin_label` for the hover readout |
| `model` | `url` (scene-relative), `bytes`, `compression` (`meshopt` or `draco`); optional `parts_manifest` (GitHub Pages copy fetched in parts), `supplement`, `tile` + `tile_bytes`, `expansion`, `demo_filter`, `plate_color` |
| `lite` | footprint + roof-height masks and their cell size for the voxel proxy city (phones, `?lite=1`) |
| `masks` | `footprint` by cell size (each layer is masked at its own resolution), `solid_wind` (file + layer index), optional `study_area` |
| `focus` | `box` [[x, z], [x, z]] of the area the tour orbits, `orbit_m`, `label` |
| `replay` | `"demo_rev02"` switches on the South Kensington traffic / UAV / bird replay and its tabs |
| `transport` | `file` (transport.json), `label`, `attribution`: the TfL layer and its tab |
| `traffic` | `dir` (traffic/), `label`: a SUMO replay (roads.json, signal_layer.json, replay/) drawn with demo_rev02's car, signal and lane modules; its Traffic tab and panel block |
| `timeline` | `step_s`, `steps`: the wind run's clock, shared by the layers that map onto it |
| `phase_order` | the field tabs and their sequence |
| `layers` | one entry per field type: `wind`, `temp`, `solar`, `diurnal`, `poll`, `flood` (any subset) |

Layer entries: `file` (scene-relative .npy, `[frames, rows, cols]` or `[frames, 3, rows, cols]` for wind), `cell_m`,
`frames`, `t0_s` + `step_s` (time of frame 0 and the frame spacing, to map the shared timeline onto the layer), or
`own_clock: true` for layers that play their own frames in sequence mode (flood, day cycle; flood shows its static `max`
map in overlay mode), `rate` (fixed frames per second in sequence mode), `range` (display range), `web_range` (encoding
range of the PNG frames), `y` (height of the plane), `label` / `title` / `legend` (panel text). Sunlight has `dates`
(per day: `ghi` frames and `shadow` mask), `shadow_cell_m`, `shadow_packed` (numpy packbits rows), `ghi_rate` /
`shadow_rate`. The day cycle has `files` per display mode and `series` (the manifest key with the hourly ambient
temperatures). The `manifest.json` in `physics/` carries per-array frame times (`time_s`, `time_local`, `altitude_deg`,
`azimuth_deg`, `rain_mm_h`) that the time label uses.

## Adding a scene

1. Put the city model in `scenes/<id>/models/` (meshopt GLB: `npx @gltf-transform/cli optimize in.glb out.glb --compress meshopt --join false --simplify false --instance false --texture-compress false`).
2. Export the field arrays into `scenes/<id>/physics/` (float16 `[frames, rows, cols]`, row 0 = south) with a
   `manifest.json`; see `white_city/tools/export_from_run.py` for the White City run.
3. Write `scene.json` (copy `white_city/scene.json`), add the scene to `index.json`.
4. `uv run --with numpy,pillow python3 scenes/tools/export_web_frames.py <id>` for the PNG frames (optional locally, required for
   the GitHub Pages copy, which cannot Range-read the arrays).
5. Optional: a TfL transport layer needs a georeference (`georef.json`, see `white_city/tools/build_transport.py`).

## Traffic (SUMO)

`white_city/tools/run_sumo.py` (`uv run --with eclipse-sumo,numpy`) builds random trips on `traffic/white_city.net.xml` (OSM highways ->
`netconvert --tls.guess-signals --tls.default-type actuated`, UTM) and records one hour through TraCI; `build_traffic.py`
(`--with eclipse-sumo,numpy,pyproj`) writes the viewer files in the model frame through `georef.json`. Synthetic demand and signal
timings, not observed traffic; the A40 Westway runs at ground level in SUMO while the model has the flyover.
