# Img2City

**2D in, editable 3D city out.** An agentic pipeline that turns OpenStreetMap
footprints plus Google satellite / Street View imagery into a parametric,
fully editable Blender city model. A vision-grounded LLM agent (Claude) writes a
building *specification* over a Blender-side parts kit, renders it, judges the
render against the real photo with a checklist + pairwise judge, and refines —
per building, across a whole block. Roads, trees, vehicles, traffic, shops,
heights and building functions are deterministic layers on top.

```
img2city make-city --query "South Kensington, London" --span 400 --out data/city_sk        # quote
img2city make-city --query "South Kensington, London" --span 400 --out data/city_sk --yes  # run
```

One command; every stage is resumable; the paid (token) stages only run behind
`--yes` after a printed cost quote; the result is one packed `.blend` plus a
machine-checked `pipeline_report.json`.

## Layout

```
img2city/
  config.py      paths, endpoints, provider + models -- all from .env / environment
  agent/         llm (one front door for model calls), openai/claude transports, planner, token logging, demo harness
  judge/         deterministic scoring anchors: silhouette IoU, DreamSim, depth agreement
  imagery/       2D inputs: fetch, view selection, rescue, cleaning, facade facts, synthetic views
  building/      single building: image -> spec -> Blender model, appearance agents
  city/          block level: OSM -> LoD1 -> agent specs -> assembly -> verification; make_city
  scene/         non-building layers: roads graph, trees/green, vehicles, traffic, shops
  kit/           the Blender-side parametric parts library (runs inside Blender)
  library/       agent-driven growth of the kit (mine -> propose -> gate)
  prior/         learned image -> parameters initialiser
  webapp/        local demo site (map -> generate, viewer -> edit, photo -> model)
scripts/         overnight_refine.sh (usage-limit-aware refine driver)
tests/           unit tests for the deterministic layer (no Blender, no tokens)
docs/            architecture, design notes, parameter schema, web app, learned prior
```

`docs/architecture.md` explains the pipeline, the package map, and how the
three couplings that used to force a flat layout (bare imports, subprocess
stages, Blender-injected source) are handled now.

## Install

```bash
git clone https://github.com/MIAO121131/Img2City && cd Img2City
python -m venv .venv && source .venv/bin/activate
pip install -e ".[web,dev]"          # core + web app + tests
pip install -e ".[ml]"               # + torch stack: DreamSim, OWLv2, Grounding DINO, DeepForest, prior
pip install -e ".[gemini]"           # + Gemini image editing (synth views, facade cleaning)
```

Non-pip requirements:

- **Blender 4.x** with the [BlenderMCP](https://github.com/ahujasid/blender-mcp) addon
  (socket on `localhost:9876`) — open it before any stage that builds or renders.
- One **LLM provider** for the agent stages (chosen in `.env`, see below):
  the local Codex CLI (`codex`, ChatGPT subscription), the OpenAI Responses
  API (`openai`), the Claude Agent SDK (`claude-sdk`, `claude login` on a
  Pro/Max plan) or the Anthropic Messages API (`claude-api`).
- `GOOGLE_MAPS_API_KEY` with Static Maps, Street View Static, Geocoding and
  Places (New) enabled. `OPENAI_API_KEY` / `GEMINI_API_KEY` only for the
  image-editing models.

## Configuration (`.env`)

```bash
cp .env.example .env      # or `make env`; then edit: provider, models, keys, paths
img2city doctor           # shows what the running configuration resolves to
```

`.env` is git-ignored (so are `.env.*` variants); only the empty template
`.env.example` is committed, and `tests/test_repo_hygiene.py` fails the test
suite / CI if a key-shaped string ever lands in a file git would commit.
Subscription providers (`codex`, `claude-sdk`) need no key at all -- just the
CLI login on that machine.

`img2city/config.py` loads `.env` from the repository root on import (a
variable already exported in the shell wins; `IMG2CITY_ENV_FILE` points at
another file). Nothing in the code names a model, an endpoint or a key:
switching the AI model is an edit to `.env`.

| variable | default | meaning |
|---|---|---|
| `IMG2CITY_LLM_PROVIDER` | `codex` | `codex` \| `openai` \| `claude-sdk` \| `claude-api` |
| `IMG2CITY_MODEL` | `gpt-6-astra` | model for every agent role |
| `IMG2CITY_VISION_MODEL` / `_SPEC_MODEL` / `_JUDGE_MODEL` / `_LEARNING_MODEL` | `IMG2CITY_MODEL` | per-role override; `<provider>:<model>` pins a provider for that role |
| `IMG2CITY_PHOTO_CARD_MODEL` / `IMG2CITY_PHOTO_SPEC_MODEL` | vision / spec model | web photo-upload flow |
| `IMG2CITY_LLM_REASONING` / `IMG2CITY_LLM_TIMEOUT` | `high` / `600` | reasoning effort (OpenAI family) / per-call timeout (s) |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | — / `https://api.openai.com/v1` | provider `openai`, `openai:*` image edits |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` | — | provider `claude-api` only (leave unset for `claude-sdk`) |
| `GEMINI_API_KEY` | — | `gemini:*` image edits |
| `IMG2CITY_CODEX` / `IMG2CITY_CLAUDE_CLI` | on `PATH` | CLIs behind the subscription providers |
| `IMG2CITY_IMAGE_EDIT_MODELS` | `openai:gpt-image-2,gemini:gemini-3.1-flash-image,...` | facade cleaning / synthetic views, tried in order |
| `IMG2CITY_MODEL_LOG_DIR` | `./runs/model_calls` | one JSON receipt per model call |
| `IMG2CITY_DATA_DIR` | `./data` | generated areas |
| `IMG2CITY_RUNS_DIR` | `./runs` | demo / harness runs |
| `IMG2CITY_CACHE_DIR` | `./.cache` | web app GLBs and pick maps, DreamSim weights |
| `IMG2CITY_PRIOR_DIR` | `$IMG2CITY_DATA_DIR/prior` | learned-prior dataset + `param_model.pt` |
| `IMG2CITY_BLENDER` | `/Applications/Blender.app/Contents/MacOS/Blender` (macOS) / `blender` | headless Blender for the web app + prior |
| `IMG2CITY_TORCH_PYTHON` | current interpreter | interpreter carrying the `[ml]` stack (vehicle detection stage) |
| `IMG2CITY_MCP_HOST` / `IMG2CITY_MCP_PORT` | `localhost` / `9876` | BlenderMCP socket |
| `IMG2CITY_OVERPASS_URLS` | two public mirrors | Overpass endpoints, tried in order |

Every agent command also takes `--model` (a bare name or `<provider>:<model>`)
and `--backend <provider>` to override `.env` for one run; `sdk` / `api` are
accepted as short forms of `claude-sdk` / `claude-api`. Every model call goes
through `img2city.agent.llm`, which writes a receipt (prompt, output, usage,
image hashes -- never keys) so any result can be traced to the model that
produced it. `requirements-lock.txt` pins the exact reference environment
(`make install-lock`); `make help` lists the other shortcuts.

## Data assets (git-ignored, must exist locally)

| path | what | how to get it |
|---|---|---|
| `data/<area>/` | a generated area: `buildings.json`, per-building specs and photos, the packed `.blend` | `img2city make-city ...`, or copy an area from another machine |
| `data/prior/param_model.pt` | learned image -> parameters regressor (photo -> model in the web app) | `img2city prior-dataset` + `img2city prior-train` (see `docs/learned_prior.md`), or copy |
| `.cache/dreamsim/` | DreamSim + DINO weights (~3 GB) for the perceptual judge | downloaded automatically on first use; copy to skip the download |
| `data/<area>/lidar/` | EA LiDAR tiles for `heights` (England only) | fetched automatically from the DEFRA WCS endpoint |

Without the prior weights the photo-upload page returns an error; without any
area the web app has nothing to show. Everything else is produced by the
pipeline itself.

## Usage

Every subcommand is a module (`img2city <cmd>` ≡ `python -m img2city.<pkg>.<mod>`);
`img2city --help` lists them, each has its own `--help`.

```bash
# offline demo of the render -> evaluate -> refine loop (no Blender, no API)
img2city demo --max-iters 80

# one building: fetch imagery, then the agent builds it in live Blender
img2city fetch    --query "Queen's Tower, Imperial College London" --pitch 25 --out data/queens_tower
img2city generate --data data/queens_tower --mode assemble --max-iters 6

# a block, stage by stage (what make-city chains for you)
img2city lod1          --bbox "51.4939,-0.1764,51.4976,-0.1706" --out data/city_sk
img2city heights       --out data/city_sk --apply
img2city functions     --out data/city_sk
img2city city-generate --out data/city_sk --min-area 200 --workers 3      # agent specs (tokens)
img2city typology      --out data/city_sk
img2city road-graph    --out data/city_sk
img2city vehicles      --out data/city_sk                                 # torch
img2city traffic-sim   --out data/city_sk && img2city traffic-audit --out data/city_sk
img2city shops         --out data/city_sk
img2city facade-colors --out data/city_sk
img2city city-generate --out data/city_sk --assemble-only --min-area 0    # build the scene
img2city regress       --out data/city_sk --snapshot

# refine the worst buildings overnight, waiting out usage limits
ITERS=2 scripts/overnight_refine.sh data/city_sk 60            # model: .env, or a 3rd argument

# local web app: map -> generate, viewer -> per-building edit panel, photo -> model
img2city webapp        # http://localhost:8000
```

## Tests

```bash
python -m pytest tests -q                       # or: make test
python -m ruff check .                          # or: make lint (CI runs both)
```

The unit layer needs no Blender, keys or tokens; heavy optional imports skip
themselves. `tests/test_site_integration.py` runs only against a live
`img2city webapp` with at least one area on disk; point it at another port
with `IMG2CITY_TEST_BASE=http://localhost:8001` (or `make site-test PORT=8001`).

## Provenance

Extracted and restructured from the `agent_harness` of the Imperial College
MSc IRP *Urban World Geometry Generation with 3D Generative Models*. Report
figures, one-off experiment drivers and evaluation scripts stayed in the IRP
repository; this repository is the reproducible agent. `docs/design_notes.md`
carries the development log of the judging/generation design.

`img2city/kit/vendor/bpypolyskel` is vendored from
[prochitecture/bpypolyskel](https://github.com/prochitecture/bpypolyskel) (GPL-3.0,
see its LICENSE) and is executed inside Blender for straight-skeleton roofs.

## License

GPL-3.0-or-later (see `LICENSE`), matching the vendored bpypolyskel code and
the Blender ecosystem the kit runs inside.
