# Asset library

Every object of the South Kensington core008 world, split out of the packed city model into one file per thing and sorted by
class, so that a building, a street, a tree or a vehicle can be read, replaced or edited on its own. Built by
`tools/build_asset_library.mjs`; `index.json` is the catalogue (every file with its class, bounding box, triangle count and
source). Nothing here is loaded by the viewer, which keeps reading the packed models; this is the editable / analysable form.

```
node --experimental-loader ./geometry/completion/scripts/three-loader.mjs assets/tools/build_asset_library.mjs            # everything
node --experimental-loader ./geometry/completion/scripts/three-loader.mjs assets/tools/build_asset_library.mjs --only=refined   # one part
```

## Frame and format

All files are plain, uncompressed glTF binaries (`.glb`) in the shared model frame: X east, Y up, Z south, metres; world
transforms are baked into the vertices, so a file can be dropped into any scene without a parent transform. Model X and −Z
are EPSG:32630 minus (695238.304719173, 5709236.965026026); the 4 m physics grid is `region = model (X, −Z)` and
`domain = region + (2116, 2124)`. Each node keeps the source node's name and its `extras` (OSM id, `geometry_fidelity`,
`height_basis`, evidence fields, road tags, …). Materials are colour-only PBR; the nine textured materials of the main model
are marked `textured_in_source` and keep their base colour only.

## Layout

| Folder | What | Files |
|---|---|---|
| `buildings/<osm id>/` | one folder per building (`way-…` / `relation-…`) | `original.glb` (from the core008 model), `supplement.glb` (306 OSM footprints added by `building_completion`, ids not in the main model), `refined.glb` + `refined_front.png` + `refined_module.py` (buildings replaced by the `geometry_expansion` task), `meta.json` |
| `ground/` | site ground, campus paving, gardens, mapped paths, entry approaches, Dalby Court deck | one GLB per source node; `site_polygons/` holds the `Site \| way-…` ground polygons |
| `roads/traffic_lanes/` | the drivable-lane ribbons of the main model (`Traffic_road`), one GLB per street | grouped by street name |
| `roads/campus/` | mapped roads, perimeter roads, east road correction | one GLB per source node |
| `vegetation/trees/` | every tree (canopy + trunk), estimated planting, public-realm trees | one GLB per tree |
| `vegetation/landscape/` | mapped gardens, hedges, low planting edges | |
| `street_furniture/` | bicycle parking and other OSM street items, lamp masts, planters, the Huxley–Sherfield covered walkway | |
| `parked_vehicles/` | the aerial-photo parked cars and vans (`AERIAL-VEHICLE`) | the viewer hides the ones that sit on simulated lanes |
| `simulation_layers/` | the model's own baked animation layers (`traffic_vehicle`, `traffic_prediction`, `birds`, `bird_sites`) | one bundle each; hidden in the viewer, superseded by the replay layers |
| `actors/` | the moving-agent models: `uav/hexacopter_cargo.glb`, `birds/pigeon.glb` (+ generator), `vehicles/build_sedan.mjs` (the sedan is generated at runtime), `actor-layer.js` | copies of `agents/demo_rev02/actors` and `agents/demo_rev02/assets` |
| `unclassified/` | anything the classifier did not recognise (should be empty; check `index.json`) | |

`meta.json` per building: names, `detail_class` (`authored_detail` for the campus and landmark modules that were detailed in
the original model, `procedural_baseline` for footprint-extruded buildings, `supplement_estimated`, plus `refined` batch
information), `geometry_fidelity`, OSM tags from `geometry/completion/sources/osm_buildings.json`, bounding box, node list,
triangle counts and the source file of each GLB.

Large companions are not duplicated here; `index.json` → `classes.pointers` lists them: the packed city model, the station
detail tile (`south_kensington_current.glb`) and the traffic / UAV / bird replay data in `agents/demo_rev02/data/`.

## Provenance and limits

The geometry is exactly the packed model's, re-encoded; no simplification. Buildings marked `procedural_baseline` and
`supplement_estimated` have estimated heights and procedural facades; `refined` buildings have estimated or artistic
details recorded in their `refined_module.py` and the batch docs under `geometry/expansion/`. The physics fields in
`physics/` were computed on the packed model's voxelisation and are unaffected by anything here.

OSM data © OpenStreetMap contributors, ODbL. The library is excluded from git (`*.glb`); rebuild it with the command above.
