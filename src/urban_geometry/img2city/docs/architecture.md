# Architecture

Img2City turns **2D inputs** — OpenStreetMap footprints plus Google satellite and
Street View imagery — into an **editable, parametric 3D city model** in Blender.
The geometry decisions are made by an LLM agent (Claude, vision-grounded) that
writes a *building specification* over a Blender-side parts kit, renders it,
judges the render against the photo, and refines. Everything non-creative
(roads, trees, vehicles, heights, functions, shops) is deterministic and cached.

```
                bbox / place name
                       │
        ┌──────────────▼──────────────┐
        │  city.lod1     OSM → footprints (placement contract) → LoD1 scene
        │  city.height_check           EA LiDAR heights (England)
        │  city.building_function      Places POI → what the building IS
        └──────────────┬──────────────┘
                       │  per building ≥ min-area
        ┌──────────────▼──────────────┐
        │  imagery.*     satellite + Street View, view selection, rescue,
        │                cleaning, OWLv2 facade facts, synthetic aux views
        │  building.typology           which dialect(s) of the kit apply
        │  building.generate           agent writes spec → kit builds it in
        │                              Blender → render → checklist + pairwise
        │                              judge (+ judge.* anchors) → refine
        │  building.facade_colors      photo-measured part colours
        │  building.glass_agent        curtain-wall look from reflections
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  scene.assets / road_graph / vehicles / traffic_sim / shops (+agent)
        │  city.generate --assemble-only   posed agent buildings + LoD1 rest
        │                                  + every scene layer → one .blend
        │  city.render_regress             fingerprint gate (no drift)
        │  city.make_city verify           roads / landmarks / coverage report
        └─────────────────────────────┘
```

`city.make_city` chains all of it, resumably, with a token quote before the
paid stages. `webapp` is a local UI over the same commands; `library` lets the
agent grow the parts kit from a region's own failures; `prior` is a learned
image → parameters initialiser.

## Package map

| package | contents | runs where |
|---|---|---|
| `img2city.config` | every machine path, endpoint, provider and model, from `.env` / env vars | host |
| `img2city.agent` | `llm` (the one front door for model calls: provider resolution, receipts, healthcheck), `openai_backend` (Codex CLI / Responses API), `claude_backend` (Agent SDK / Messages API), `planner` (Action/Context, Mock + LLM planner), `tokens` (per-call token CSV + provenance), `tools` (executors, incl. BlenderMCP), `harness` (offline demo loop) | host |
| `img2city.judge` | `evaluator` (silhouette IoU + VLM critic), `perceptual` (DreamSim), `depth_anchor` (Depth-Anything rank agreement) | host |
| `img2city.imagery` | `maps_fetch`, `acquire_view`/`acquire_view2`, `rescue_imagery`, `facade_clean`, `facade_facts`, `synth_views`, `batch_campus` | host |
| `img2city.building` | `generate` (the single-building agent loop: brief → spec → render → checklist/pairwise judge → refine), `typology` (+ `typology_cards.json`, `typology_exemplars.json`), `facade_colors`, `facade_project`, `texture_assets`, `glass_agent`, `courtyard_agent` | host → Blender via socket |
| `img2city.city` | `lod1`, `generate` (block orchestrator: specs, refine, assembly), `height_check`, `building_function`, `render_regress`, `compare_top`, `make_city` | host → Blender via socket |
| `img2city.scene` | `assets` (trees/roads/green/furniture), `road_graph`, `vehicles`, `traffic_sim`, `traffic_audit`, `shops`, `shop_agent` | host |
| `img2city.kit` | `components.py` (core parametric parts, `build_building`), `parts_learned.py` (learned dialect parts), `spec_dialect.json`, `vendor/bpypolyskel` | **inside Blender** (source-injected) |
| `img2city.library` | `learn` (mine unmet checklist demands), `grow` (agent authors a part; smoke/regress/lift gates), `audit` (manifest) | host |
| `img2city.prior` | `params`, `gen_dataset`, `headless_gen`, `train`, `predict` | host (`headless_gen` inside Blender) |
| `img2city.webapp` | FastAPI server, area registry, jobs, rebuild, `export_glb.py` / `rebuild_bpy.py` (Blender-side), `ui/` | host (+ headless Blender) |

## Three coupling mechanisms, and how the package handles them

The old flat layout existed because of three couplings. Each now has one
owner:

1. **Bare-name imports** (`from generate import _send`) → absolute package
   imports (`from img2city.building.generate import _send`). Lazy in-function
   imports are kept where they break import cycles (`city.generate` ↔
   `building.facade_colors`, `building.typology`, …).
2. **Stages as subprocesses** (`python3 height_check.py`) →
   `config.module_cmd("city.height_check", ...)`, i.e.
   `python -m img2city.city.height_check`, run from `config.PROJECT_ROOT` with
   `config.subprocess_env()` (PYTHONPATH set), so it works with or without
   `pip install -e .`. Only the torch stage may use a different interpreter
   (`IMG2CITY_TORCH_PYTHON`).
3. **Blender-side code** never imports `img2city`. `kit.load_kit_src()` is the
   single function that concatenates `components.py` + `parts_learned.py` and
   injects `_VENDOR_DIR`; `building.generate.load_components_src()` and
   `webapp.rebuild.components_src()` both delegate to it. `library.grow`
   writes learned parts through `kit.PARTS_LEARNED_PY`, and the spec-schema
   dialect lines through `kit.SPEC_DIALECT_JSON`.

## Data layout (one directory per area, `config.DATA_DIR/<area>/`)

```
buildings.json         footprints in scene metres + anchor (lat0/lon0/bbox) + per-building meta
region.json            reverse-geocoded region tag + drive side
osm_raw.json  roads_raw.json  green_raw.json  furniture_raw.json   Overpass caches
traffic.json  traffic_anim.json  vehicles.json  shops.json  trees.json   scene layers
height_check.json  lidar/                                            LiDAR heights
buildings/<osmid>/     satellite.png streetview.png pano.json  (imagery)
                       facts.json colors.json typology.json     (deterministic facts)
                       spec.json pose.json gate.json            (the agent's output)
                       refine/  checklist.json best.png result.json …
agent_placements.json  assembled scene manifest
<area>_textured.blend  the deliverable
pipeline_report.json   make_city verification
```

Nothing under `data/` is committed. `IMG2CITY_DATA_DIR` moves it elsewhere.

## Conventions

- Every value the agent reads carries provenance (`src`, `conf`); observed
  values overwrite guesses, never the reverse.
- Every stage is idempotent: it skips itself when its artefact exists and can be
  re-run after a crash.
- Paid (token) stages only run behind `--yes`; the free stages always run and
  print the quote.
- The kit is additive-only; `city.render_regress` is the gate that proves an
  extension changed nothing that already existed.
