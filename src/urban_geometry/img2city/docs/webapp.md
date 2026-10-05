# webapp — local demo site for the parametric city pipeline

```bash
img2city webapp        # or: python -m img2city.webapp.server          # -> http://localhost:8000
```

Requirements: `pip install -e ".[web]"` (plus `[ml]` for the photo prior), Blender 4.5
(path via `IMG2CITY_BLENDER`), and
`GOOGLE_MAPS_API_KEY` exported in the launching shell if you want new-area
generation. No node/npm — the frontend is plain ES modules with vendored libs
(`ui/vendor/`).

## Pages

| page | what it does |
|---|---|
| `/` | generated areas (`data/*` with a packed blend); click → first visit exports a cached glb (~2 min) |
| `/viewer.html?area=X` | three.js scene; click a building → parameter panel; **Apply** rebuilds just that building headlessly (~5 s) and hot-swaps it |
| `/map.html` | drag centre + width/height → bbox; existing area opens instantly, new bbox runs `img2city make-city` (free quote stage → explicit token confirmation → full run) |
| `/upload.html` | photo → `img2city.prior.predict` prior → editable model (~3 s); optional agent refine (full `img2city.building.generate` loop, tokens) |
| `/jobs.html` | every generation/refine job with stage progress, current activity (live log line), confirm/cancel/resume; active-job badge in every page's topbar |

Jobs persist to `.cache/webapp/jobs/*.json` and survive server restarts: a live process
is re-adopted by pid, a dead one is repaired from disk artifacts, and an
interrupted generate job can resume (make_city stages are all resumable).
Areas can carry a human display name (`display.json` in the area dir, set via
the ✏️ button or at generation time) — the directory itself is never renamed.
The site is bilingual (zh/en, topbar toggle).

## Files

- `server.py` — FastAPI routes + static hosting
- `areas.py` — area registry, bbox matching, cached headless glb export
- `export_glb.py` — bpy: BOX-projection textures → real UVs (KHR_texture_transform), procedural → flat colour, pick map (`Agent_<osmid>`/`Bldg_<osmid>`)
- `schema.py` — typed edit-form schema (the spec vocabulary from SPEC_LINES/poly_params)
- `rebuild.py` + `rebuild_bpy.py` — single-building rebuild: refresh the `agent_placements.json` entry, headless delete+rebuild in the packed blend (blend saved = deliverable current), mini-glb out; `spec.json` backed up once as `.web.bak`
- `jobs.py` — background jobs (make_city two-phase, photo refine); auto-launches Blender+MCP for stages that need :9876
- `photo.py` (+ `rebuild_bpy.py --desc`) — upload flow (prior → headless build → glb)
- `.cache/webapp/` (config.CACHE_DIR) — exported glbs, job logs (git-ignored)

Rebuilding a building updates its `spec.json` and the packed `*_textured.blend`
in place, so the whole-area glb cache goes stale and re-exports on the next
viewer load. Footprints are never editable from the web (OSM/OBB contract).

## Tests

Unit layer (no server needed): `python -m pytest tests -q`.
Full integration sweep against a LIVE server (pages, i18n coverage, pick-map
consistency, the preview/save/undo edit loop on the real Blender worker, photo
flow, input guards): start `img2city webapp`, then
`python -m pytest tests/test_site_integration.py -v`.
The integration module skips itself entirely when the server is not running,
so CI and clean checkouts stay green.
