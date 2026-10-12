# south_kensington_core008

Merged city geometry: the coarse 5.8 km² Kensington/South Kensington OSM region
(`cache/south_kensington/exports/review-003`) with its central core replaced by the
detailed "008" model (central-preview-007 + Natural History Museum polish, web-light asset).

| file                                | use                                                                                 |
| ----------------------------------- | ----------------------------------------------------------------------------------- |
| `south_kensington_core008.glb`      | plain GLB (1.43 GB, 20.9 M tris). Blender / trimesh / `birds/scripts/glb_to_geo.py` |
| `south_kensington_core008_web.glb`  | meshopt + quantized (262 MB). three.js / web viewers only                           |
| `south_kensington_core008.json`     | provenance, transform, removed objects, checks                                      |
| `south_kensington_core008_merge.py` | the Blender script that produced it                                                 |
| `renders_core008/`                  | visual seam checks (textured Workbench renders)                                     |

Frame: region local EPSG:32630 frame (X east, Y north, Z up, metres; origin as in
`cache/south_kensington/geometry.json`). The 008 core was moved from the campus frame with the
inverse of `expansion/coordinate_contract.json` and lifted 5 cm to avoid z-fighting.
`stations.csv` and `birds_scene.glb` in this folder use their own local frame (origin not
documented; stations cluster around South Kensington station, so it is neither the campus nor the
region frame). Determine the offset before mixing them with this file.
