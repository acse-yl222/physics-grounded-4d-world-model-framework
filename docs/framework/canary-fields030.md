# Canary Wharf fields030

This presentation replaces the three-snapshot wind display with 100 independently decoded SCALED steps. The 1 m-trained model operates directly on a 4 m grid (1024 × 1024 × 64); interpreted time is 100 s per model step. This spatial/time scaling is a user-selected assumption, not a validated physical-similarity result. The previous 1 m computation was stopped and its partial output preserved.

Wind029 retains samples at 2, 6 and 10 m and the final full 3-D vector field. The public default is 2 m. The domain spans z = -4 to 252 m, with the bottom numerical ground layer solid. Each displayed wind frame is a recorded model step; none is interpolated from older outputs.

The companion scenarios have independent clocks:

| Field | Retained run | Grid | Recorded states | Forcing |
|---|---|---|---|---|
| Wind | canary_wharf_wind4m029 | 4 m | 100, interpreted 100–10000 s | pretrained surrogate |
| Temperature | canary_wharf_temperature030 | 32 m horizontal, 16 m vertical | 11, 0–600 s | frozen final full wind029, controlled clear sky |
| Pollution | canary_wharf_pollution030 | 4 m planar | 21, 0–600 s | frozen final 2 m wind029, arbitrary road emissions |
| Sunlight | canary_wharf_sunlight030 | 4 m | 100, 0–600 s | 21 June 2026 noon UTC clear-sky geometry model |
| Flooding | canary_wharf_flood030 | 4 m, measured terrain core only | 100, 0–600 s | 50 mm/h controlled rain |

The wind's interpreted time is not the thermal or tracer physical clock. The temperature model is not a 4 m simulation. Flood depth is valid only on measured non-water ground; the display does not infer terrain or flood conditions outside that mask. Geometry, traffic and UAV route assets are preserved.

Scientific arrays remain in retained protocol runs. Pages receives encoded image frames and masks, with explicit component/range quantization. Pollution uses log10(1+c/0.001), preserving exact zero and low-concentration contrast; older scenes retain their existing log10 decoding. Wind images use lossless WebP storage of the same RGB pixels to keep the site within its hosting budget. Export error checks compare every image to its source array, separately from browser loading/playback checks.

Reproducible entrypoints include `scaled_scene029.py`, `geometry_temperature.py`, `run_near_ground_tracer.py`, `canary_surface.py`, and `project/tower_hamlets/configs/*030.json`. `common.recorded_city_fields` assembles the selected presentation. `tools/package_city_fields_streamed.py` selects browser assets without pushing them.

Validation: wind completion and source/PNG comparisons; tracer nonnegativity and mass balance; thermal finite values and blocked-solid checks; sunlight/flood sampling and mask checks; protocol validators; browser field switching, final-frame selection, wind frame 1/50/100 and playback; PNG-transform compatibility test. The full Python suite has the five pre-existing `windfarm_resources` builder errors, unrelated to these fields.

The selected browser presentation is `canary_wharf_city_fields031` (`city_fields031.json`); its temperature image range includes all recorded values without clipping. Earlier retained presentations remain unchanged.
