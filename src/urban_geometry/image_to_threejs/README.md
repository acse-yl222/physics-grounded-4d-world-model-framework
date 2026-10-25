# image_to_threejs

City-scale three.js model generator: real footprints, roads, land use, water and
trees from Overture Maps, rendered with procedural London facades, plus hand-built
landmark modules reconstructed from reference material. Output is a protocol v1.1
run with four GLB mesh layers (`buildings`, `landmarks`, `ground`, `trees`) for the
unified viewer.

| File                    | Role                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `fetch_overture.py`     | Downloads the scene's square domain from Overture (S3, bbox filter) |
| `prepare_scene.py`      | Resolves heights, roofs, facade styles; roads, areas, water, trees  |
| `three/`                | three.js kit, facade textures, generic buildings, ground and trees  |
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
  use the protocol's `glTF-y-up` frame. Ground is flat at z = 0 (no terrain model).
- Heights and roof shapes from Overture tags are kept. Missing values are estimated
  from storey counts, neighbouring tagged buildings or the building class, and are
  flagged per building in `inferred` in the prepared scene. Facade styles are
  London-typical guesses unless a facade material or colour is tagged.
- Tunnels and underground rail are omitted; bridges and flyovers are lifted by
  `DECK_M` per OSM layer level. Park and woodland trees beyond the mapped tree points
  are scattered deterministically and are not survey data.
- Landmark modules record their references and approximations in
  `landmarks/index.json`, copied into each run as `data/landmarks.json`.
