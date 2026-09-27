# south_kensington_core008

Merged city geometry: the coarse 5.8 km² Kensington/South Kensington OSM region
(`cache/south_kensington/exports/review-003`) with its central core replaced by the
detailed "008" model (central-preview-007 + Natural History Museum polish, web-light asset).

| file | use |
|---|---|
| `south_kensington_core008.glb` | plain GLB (1.43 GB, 20.9 M tris). Blender / trimesh / `birds/scripts/glb_to_geo.py` |
| `south_kensington_core008_web.glb` | meshopt + quantized (262 MB). three.js / web viewers only |
| `south_kensington_core008.json` | provenance, transform, removed objects, checks |
| `south_kensington_core008_merge.py` | the Blender script that produced it |
| `renders_core008/` | visual seam checks (textured Workbench renders) |

Frame: region local EPSG:32630 frame (X east, Y north, Z up, metres; origin as in
`cache/south_kensington/geometry.json`). The 008 core was moved from the campus frame with the
inverse of `expansion/coordinate_contract.json` and lifted 5 cm to avoid z-fighting.
`stations.csv` and `birds_scene.glb` in this folder use their own local frame (origin not
documented; stations cluster around South Kensington station, so it is neither the campus nor the
region frame). Determine the offset before mixing them with this file.

## Revisions (2026-09-10)

- v2: region ground/path/road/park meshes re-materialed with the 008 authored stone (4.8 m), asphalt (2.4 m) and grass (6 m) tiles using world-XY UVs, so the core and its surroundings share one ground look; 008 plinth recoloured to the stone mean.
- v3: the 208 sparse simplified trees of the 008 core were replaced by solid low-poly trees (tapered 8-segment trunk + 12x8 ellipsoid canopy, sized from each original tree's bounds, 6 broadleaf shades and bark material kept, original OSM/planting extras copied). 221 objects / 542 k tris -> 416 objects / 41 k tris.
- v4: traffic layer embedded (collection "Traffic | OSM roads and simulated vehicles"). 75 OSM road ways from `pipelines/geometry/traffic/verification/roads.geojson` as 1.6 m centreline bands 20 cm above the road, coloured by highway class, with osm_id/name/highway/lanes/maxspeed/oneway/drivable/length plus simulated occupancy as glTF extras; 32 simulated vehicles (IDM + signals on the 7 main roads, 80 s at 2 Hz) as animated boxes, one glTF animation per vehicle (0-80 s, linear). Sources and region-frame JSON in `traffic/`. Simulated, not observed traffic.
- v5: trained-model prediction sub-layer. `traffic/train_reduced.py` trained the ParticleTrafficModel (reduced: 120/20 procedural trajectories, 60 epochs, best val loss 0.0039; weights `pipelines/geometry/traffic/train/best_model_09-10_core008.pt`). `traffic_predict.py` re-runs the same seeded scene and predicts 3 s ahead every 5 s (15 windows, 480 predictions, ADE 2.21 m vs the simulator). Ribbons "Traffic prediction | sim-NNN | t=..s" appear only during their horizon when the animation plays.
- v6: (1) road attribute layer extended from 75 to all 1815 drivable OSM ways in the region (`traffic/region_roads_all.json`); `lanes` comes from the OSM tag for 425 ways and is estimated from the highway class for 1390 (flagged `lanes_basis`). (2) Bird flock layer: `birds/voxelise_for_birds.py` rasterises buildings + solid trees of this GLB into the sim's 128x128x64 grid (8 m / 1 m, origin (200,-700,0) so the core + museum quarter are covered), `birds/run_birds_core008.py` runs `pipelines/geometry/birds` (300 starlings, 120 s, seed 1, spawn (620,220,40) above the park north of the Albert Hall) without editing its config (overrides via a SimConfig subclass); 300 animated birds + roost/forage markers embedded, full 20 Hz output in `birds/birds_core008.npz`.
