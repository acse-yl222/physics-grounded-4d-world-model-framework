# Imperial Corridor imported presentation

The user-supplied Claude export is retained unchanged outside the code checkout.
This integration preserves its existing specialized presentation adapter. It is
not a newly generated or validated protocol simulation run. Original solver code,
SUMO network/configuration and demand-generation inputs were not supplied.

## Spatial and time semantics

Origin: longitude -0.200473, latitude 51.506427. Source coordinates are east/north
metres; renderer maps `(east, north, up)` to `(east, up, -north)`. Elevation follows
the exported road surface. Vertical datum and per-vehicle bridge levels are not
established. Do not infer a surveyed 3D trajectory from the replay.

The selected traffic exports each have 600 samples at 1 second, starting at
31800, 49800 and 64200 source clock seconds. No UTC epoch is inferred. Vehicles
are a size-limited subset of a SUMO mesoscopic model, not observed trajectories.
The source reports congestion teleports and flow around half the counted volume.
Replay corrections preserve recorded positions; they do not recalibrate SUMO.

## Changes

- Recorded positions replace inferred constant-speed lane routes and queue clamps.
- No 11-second future-window smoothing; missing/teleport intervals remain absent.
- Headings interpolate along the shortest arc; playback stops at the final sample.
- Solar direction uses geographic location and London local date/time, including
  daylight saving. Sky, clouds and light intensity are visual approximations.
  Existing high-quality mode enables shadow maps and ambient occlusion.
- Underground presentation and original assets remain unchanged.

## Rebuild and publication

`python3 tools/build_corridor_site.py EXPORT_DIR SITE_DIR/scenes/imperial_corridor`
creates a self-contained local preview. The explicit `--data-url` option packages
code only for Pages, loading the selected immutable resource revision remotely.
The builder records SHA-256 and byte size for every original data file.

Original bundle and shell are in `src/visualization/corridor/vendor`; they are
preserved as the baseline for checked, deterministic build patches. Reusable
replay/solar/lighting behavior is maintained separately. Data attribution remains
visible in the page: OpenStreetMap/Overture ODbL, DfT/BODS OGL as supplied in the
export. The original procedural models have no separately supplied license;
publication is at the owner's request, not a new blanket license declaration.

Full traffic-model repair requires the original SUMO net, demand, routes,
signals, configuration and calibration targets. Lane placement, queue storage,
intersection conflicts, teleports and counts need rerunning and validation there.
