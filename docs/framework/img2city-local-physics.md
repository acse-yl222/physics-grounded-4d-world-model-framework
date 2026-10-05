# Img2City local CPU physics

The retained summer and winter runs recalculate solar fields from the transformed South Kensington Img2City GLB triangles. They do not reuse the published scene physics arrays. The original default view remains unchanged.

## View results

Start `p4d serve --port 8769`, then open `/src/visualization/viewer/?manifest=/project/south_ken/runs/img2city_solar_summer_20261005/manifest.json` (2026-06-21), or replace `summer` with `winter` (2026-12-21). Enable one scalar layer at a time: irradiance (W/m²), shadow (1 = shaded), sky view factor (0–1), or daily sunlit hours. The timeline uses UTC; London summer local time is UTC+1. Playback defaults to 900 simulated seconds per real second. Layers are drawn above the sampled ground and rooftop surfaces.

## Reproduce

Install optional dependencies with `python -m pip install -e '.[solar]'`. From the repository root:

```sh
python -m urban_geometry.img2city_solar project/south_ken/runs/img2city_sk_20261005 --date 2026-06-21 --cell 4 --interval 30 --run-id img2city_solar_custom
```

Use a new run ID for each calculation. This adds a retained local run and named view, without committing or pushing. Each output includes input hashes, source snapshot, assumptions, scalar arrays, and sampled solar positions.

## Interpretation and limits

The existing ShadowNet, HorizonNet and clear-sky irradiance implementation run on CPU. The model is rasterized into a 179×174 grid at 4 m spacing, using the top triangle intersection in each cell. There are 49 time samples at 30-minute spacing. Daily sunlit hours are integrated numerically. This is a 2.5-D horizontal surface approximation, not facade irradiance or full ray tracing. Vehicles and road markings are excluded; static vegetation and glass are opaque. Unmodelled cells are masked; missing surrounding obstacles can underestimate shadow near boundaries. Thin geometry and overhangs are not resolved. Weather, measured terrain and materials are not calibrated: results are clear-sky model estimates, not observed conditions.

## Other project capabilities

| Capability | Current status for this model |
| --- | --- |
| Solar / shadow / sky view / sunlit hours | Recalculated locally on CPU; two seasonal runs retained |
| Wind | Existing pipeline requires CUDA plus SCALED code and model weights; not recalculated |
| Temperature / pollutant transport | Need adapted wind results and boundary/source conditions; not recalculated |
| Flood | Underlying solver can target CPU, but requires terrain, rain and drainage assumptions; not recalculated |
| Traffic | Requires SUMO installation and corresponding road network, demand and signals; not simulated |
| UAV | Display assets are not a flight simulation; routes, timing and collision constraints need adaptation |
| Birds | Requires obstacle/environment and flock/roost inputs; not simulated for this model |

The displayed scalar fields therefore establish the CPU solar path only; they do not imply that every project solver has been connected.
