# image_to_threejs

City-scale three.js model generator: real footprints, roads, land use, water and
trees from Overture Maps, rendered with procedural London facades, plus hand-built
landmark modules reconstructed from reference material. Output is a protocol v1.1
run with GLB mesh layers (`buildings`, `landmarks`, `ground`, `trees`,
`street_furniture`, plus `terrain` for scenes with a DEM) for the unified viewer.

| File                    | Role                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `fetch_overture.py`     | Downloads the scene's square domain from Overture (S3, bbox filter) |
| `fetch_terrain.py`      | Terrain tiles -> scene ENU DEM (`input/terrain/dem.npy`, index)     |
| `terrain.py`            | Compact scene terrain grid, building ground and water levels        |
| `prepare_scene.py`      | Resolves heights, roofs, facade styles; roads, areas, water, trees  |
| `resolve_conflicts.py`  | Fits roads, pavements and trees around footprints and water         |
| `check_conflicts.py`    | Reports remaining overlaps in a prepared scene (needs `shapely`)    |
| `three/`                | three.js kit, facade textures, generic buildings, ground and trees  |
| `three/terrain.mjs`     | `elevation(scene, x, y)`: bilinear terrain height (0 when flat)     |
| `landmarks/<id>.mjs`    | One module per landmark (see [AUTHORING.md](AUTHORING.md))          |
| `collect_landmarks.mjs` | Validates modules and writes `landmarks/index.json` (`--check`)     |
| `studio.html`           | Preview / export page; `render.cjs` drives it in headless Chromium  |
| `find_buildings.py`     | Footprint lookup by name or position for landmark authoring         |
| `build_run.py`          | Full pipeline to a retainable bundle in `cache/`                    |

## Run

```sh
PYTHONPATH=src python3 -m urban_geometry.image_to_threejs.build_run imperial_corridor
p4d retain cache/imperial_corridor/image_to_threejs/<run_id>/bundle
p4d serve   # open ?scene=imperial_corridor
```

Requirements: `pyarrow` and `shapely` (fetch), Node.js with Playwright's Chromium
(export), and network access to `overturemaps-us-west-2.s3.us-west-2.amazonaws.com`
and the npm registry (`@gltf-transform/cli` for Meshopt compression). Overture data
lands in `project/<scene>/input/overture/` (not committed); `cache/` holds the
prepared scene and raw exports.

## Data semantics

- Coordinates are scene ENU metres from `configs/image_to_threejs.json`; GLB layers
  use the protocol's `glTF-y-up` frame. Without a `terrain` block the ground is flat
  at z = 0 and the output is unchanged.
- Terrain (optional `terrain` block: `zoom`, `half_m`, `dem_m`, `scene_grid_m`):
  `fetch_terrain.py` downloads AWS Terrain Tiles (Tilezen Joerd, Terrarium PNG,
  `R*256 + G + B/256 - 32768` m; tiles cached in `cache/<scene>/terrain/`) and
  resamples them bilinearly to an ENU grid in `project/<scene>/input/terrain/`
  (`dem.npy` float32 rows south->north + `index.json` with grid, projection,
  vertical reference, attribution and SHA-256 of every tile). In Great Britain the
  tiles come from the Environment Agency LIDAR Composite DTM (bare earth, metres
  above ODN); attribution: "© Environment Agency copyright and/or database right 2015. All rights reserved." ([attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)).
  `prepare_scene.py --terrain` stores a 10 m grid as `scene.terrain` (int16 cm above
  `base_m`, base64, ~1.8 MB for 8.2 km), `ground_z` / `ground_max` (lowest / highest
  terrain over each footprint) and a flat `level` per connected water body (10th
  percentile of the DEM inside it); heights stay relative to the ground. The
  builders apply it at render time: a heightfield `terrain` layer (lowered under
  water), draped land use, roads, rails, walls and junctions (edges split to
  `DRAPE_M`), buildings standing on `ground_z` with walls `FOOT_M` lower (long
  footprints on an even slope, e.g. terraces, are sheared onto `ground_plane`), landmarks
  lifted as a whole (claimed footprints' lowest ground; bridges over water to the
  bank level) with their base extended down where the terrain falls away, decks
  interpolated between the terrain at their ends, and trees / furniture at the
  sampled elevation. Railway cuttings are part of the DTM, so a few footprints over
  or beside them span several metres of ground.
- Heights and roof shapes from Overture tags are kept. Missing values are estimated
  from storey counts, neighbouring tagged buildings or the building class, and are
  flagged per building in `inferred` in the prepared scene. Facade styles are
  London-typical guesses unless a facade material or colour is tagged.
- Tunnels and underground rail are omitted; bridges and flyovers are lifted by
  `DECK_M` per OSM layer level. Park and woodland trees beyond the mapped tree points
  are scattered deterministically and are not survey data.
- Overture roads are centrelines with class widths, so `resolve_conflicts.py`
  narrows each side of a carriageway and pavement to clear the nearest footprint,
  hides segments that pass under a building, adds parapets where a way crosses water
  without a mapped bridge, draws houseboats and small unnamed footprints in water as
  moored vessels, and drops or moves mapped trees inside buildings, in water or on
  carriageways. Counts are recorded in the scene's `source.conflicts_resolved`;
  `check_conflicts.py <scene.json>` lists what is left.
- Viewers may animate water with `three/water.mjs` (`studio.html?water=animate`);
  exported GLBs keep the static water material.
- Landmark modules record their references and approximations in
  `landmarks/index.json`, copied into each run as `data/landmarks.json`.
