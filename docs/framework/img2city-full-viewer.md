# Img2City in the original South Kensington page

This is an opt-in scene configuration for the existing `legacy/viewer/3d` application, not a replacement page or a change to the default scene. No Git refs are modified. Nothing is published.

Open `/src/visualization/legacy/viewer/3d/?scene_config=/project/south_ken/runs/img2city_original_page_20261005/scene.json&lite=0&pose=campus&shot=traffic&play=0` using `p4d serve --port 8769`.

## What is connected

- Original scene camera, automatic sequence, overlay mode, playback, opacity, field readout, full/lite geometry, building/ground/tree toggles.
- Wind heat map and streamline particles; temperature heat map and isotherms; day-cycle ground/air temperature modes; pollution; flood event and maximum map.
- Solar irradiance/shadows and June/December date selection, using the Img2City CPU results.
- Original SUMO vehicles, recorded signals, lane surfaces, station/map markers, UAV schedule/flight corridors and follow views.
- Bird flock and individual follow cameras, using a new CPU simulation on the Img2City height-derived obstacle grid.

These are not all newly calculated fields. The persistent page notice and reference labels distinguish them:

| Data | Origin and limits |
| --- | --- |
| Geometry | User's retained South Kensington Img2City GLB; only a documented display-frame transform |
| Solar | Existing 4 m, 30-minute clear-sky CPU calculation on this model; display resampled to original region grid with nearest-neighbour sampling |
| Birds | Original project solver, unchanged, on Img2City solid-column geometry; 40 birds, seed 42, 120 s, saved at 0.25 s; no wind, assumed roost/forage sites, no vehicle/UAV coupling |
| Wind, temperature, day cycle, pollution, flood | Published original simulation arrays decoded from PNG; cropped to the corresponding geographical area, not recalculated or adapted to new obstacles |
| Traffic/signals | Original saved 300-second sample, looped explicitly; not a traffic observation or a new simulation |
| UAV | Original schedule replay; no new collision/path planning for Img2City buildings |

The old supplement, detail-tile and building-refinement assets are not layered on top of the replacement Img2City geometry. They would reintroduce the old buildings. White City-only transport inputs are not part of the original South Kensington scene configuration.

## Coordinate correction

The old viewer's core008 geometry and recorded fields are in the *region* frame, not the campus frame implied by the inherited project origin. `src/urban_geometry/core008/south_kensington_core008_merge.py` applies the inverse of this region-to-campus affine:

```
A = [[0.9971372878088512, 0.03850621238135248],
     [-0.03860679068166115, 0.9997417959287375]]
t = [-700.1750108416061, 238.94679349918735]
region_xy = inverse(A) @ (diag(1, 111320/110540) @ img2city_enu_xy - t)
```

The north scale converts Img2City's 110540 m/degree approximation into the inherited campus projection. glTF Z is minus north. No physical height shift is applied. Canonical source GLB and solar data stay unchanged; the legacy model transform is recorded in `scene.json`.

The resulting legacy display grid is 182 columns × 188 rows at 4 m: x0=588 m, south northing=-1008 m. Original published 768×704 frame pixels are cropped at x=556, y=119. PNG row 0 remains south. `reference-downloads.json` records source URLs, original/downloaded hashes and crop operations. No offsets are chosen by visual guesswork.

## Bird evidence

`bird_compute/img2city_birds_EVIDENCE.json` records the resolved configuration and occupancy checks. The retained run has 480 frames, no nonfinite channels, no occupied positions and no occupied segment samples or out-of-domain samples in the wrapper checks. This is evidence for this simplified 4 m obstacle run only, not exact mesh collision clearance or ecological validation. The bird grid uses a minimum 4 m ground column and opaque vegetation. Bird time loops the saved sample independently and is labelled in the stats.

The original public bird `.f32` file was absent (HTTP 404); the original metadata alone was not treated as a usable replay. The replacement is a separately identified solver output, not fabricated trajectory frames.

## Reproduction

Use a fresh bundle directory: adapter steps intentionally avoid changing an existing retained solar run. Install the project's base dependencies and `numpy>=2`, Pillow, SciPy and Shapely in a local environment. From the repository root with `PYTHONPATH=src`:

1. Run `python -m visualization.adapters.img2city_legacy project/south_ken/runs/img2city_solar_summer_20261005 project/south_ken/runs/img2city_solar_winter_20261005`.
2. Supply the recorded original scene/physics/web-index JSON files under the new bundle's `reference_source/` (their source site is recorded in the download manifest).
3. Run `python -m visualization.adapters.img2city_region_display` once. This creates `reference_crop.json` and transforms only display copies.
4. Run `python -m visualization.adapters.img2city_reference_download`. This downloads public reference frames and crops them; requires internet. It does not upload anything.
5. Run `python -m visualization.adapters.img2city_reference_config` and `python -m visualization.adapters.img2city_birds`.
6. Rebuild the manifest artifact inventory and source snapshot before retaining a new reproduction. These helper steps operate on the staging bundle; they do not assert a completed immutable run while files are being assembled.

The retained manifest preserves the canonical model/solar layers plus the full original-page configuration, reference data, bird results, audit files and source snapshot as artifacts. Use the original-page URL above to see all modules; the generic protocol viewer shows the canonical solar layers only.
