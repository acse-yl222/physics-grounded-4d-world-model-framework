# Design notes — the render → evaluate → refine agent

> Ported from the IRP `agent_harness` README (development log of the judging
> and generation design, 2026-06 → 2026-08). File names below refer to the old
> flat layout; see `architecture.md` for where each module lives now.


This package is the **automated loop** for the agentic-AI thesis: instead of
hand-prompting Blender edit-by-edit, a harness drives the
*reason → act → observe* loop and refines a model against a reference image until
a target score is reached — logging token usage and snapshotting every accepted
iteration along the way.

The loop it realises:

```
context (goal + history + last observation)
  → Agent.plan          LLM proposes the next edit            [tokens logged]
  → Executor.execute     apply it in Blender (MCP) or the mock
  → render
  → Evaluator.score      deterministic geometric score
     + VLMCritic.critique  natural-language guidance           [tokens logged]
  → accept / reject     keep the edit only if the score improves
  → snapshot            save every accepted iteration
loop until score ≥ threshold or max-iterations
```

## Why this matters for the project
The earlier Queen's Tower work was **manual prompting** (a human deciding each
edit). This harness is the **self-updating** version — the project's core
contribution and the start of the *Agent core* phase. It also bakes in the two
quantitative metrics the supervisor asked for: **token usage per iteration** and
**iteration count to convergence**.

## Files

**Core loop (the reason → act → observe skeleton)**

| file | role |
|------|------|
| `harness.py`    | the orchestration loop + config + CLI (start here) |
| `agent.py`      | planner: `MockAgent` (offline) and `ClaudeAgent` (live, real Claude vision); `Action`/`Context` |
| `tools.py`      | tool layer + executors: `MockExecutor` (offline) and `MCPBlenderExecutor` (Blender wiring point); `ToolRegistry` |
| `evaluator.py`  | `SilhouetteEvaluator` (deterministic score) + critics: `MockCritic` (offline), `ClaudeVLMCritic` (live) |
| `tokens.py`     | `TokenLogger` — per-iteration token CSV + plot |
| `perceptual.py` | DreamSim perceptual distance — deterministic judge anchor / tie-break (degrades to no-op if not installed) |
| `sdk_backend.py`| routes planner + critic through the Claude Agent SDK (Pro/Max subscription billing) incl. usage-limit healthcheck |

**Single-building pipeline (image → editable model)**

| file | role |
|------|------|
| `generate.py`   | the main generator: Claude looks at satellite + street view, writes bpy or a parts-library JSON spec, renders in live Blender, checklist + pairwise judge, iterates |
| `components.py` | parametric building-parts library (runs inside Blender): blocks, curtain walls, exoskeleton, barrel vault, sawtooth roofs, masonry family… the agent picks parts + parameters instead of writing raw vertices |
| `maps_fetch.py` | fetch Google satellite + Street View images for one building |
| `acquire_view.py` | auto-fetch a ring of Street View candidates and let Claude (vision) pick the shot that best shows the building |
| `synth_views.py`  | synthesize auxiliary viewpoints (back/far end) with Gemini image editing, used as WEAK references only |
| `batch_campus.py` | run the acquire_view pipeline over every building in `buildings.txt` |
| `buildings.txt`   | curated South Kensington campus building list (batch input) |

**City-block pipeline (the city pilot)**

| file | role |
|------|------|
| `city_pilot.py`     | OSM footprints → local metres → LoD1 extruded block scene in live Blender; optional per-building imagery fetch |
| `city_generate.py`  | whole-block generation: runs the single-building agent per substantial building, OSM footprint as the placement contract, assembles + renders the block (resumable) |
| `compare_top.py`    | pixel-aligned satellite vs orthographic top-render comparison figure |
| `scene_assets.py`   | non-building layer: DeepForest tree detections + OSM roads (pavements, centre lines) placed in the scene |
| `texture_assets.py` | photo-derived tileable brick/stucco/slate patches per building (BOX-projected, appearance eval only) |
| `facade_facts.py`   | OWLv2 window/door counts from the street photo → deterministic facts for the BRIEF (+ pixel rows for projection alignment) |
| `facade_project.py` | street photo rectified (exact pano-camera back-projection) + mirror-tiled onto facade quads floating 0.29 m outside the wall; `--eval` = three-way DreamSim appearance eval |
| `height_check.py`   | EA LiDAR 1 m DSM/DTM vs scene heights; `--apply` writes trusted measurements back |
| `depth_anchor.py`   | Depth-Anything-V2 depth-agreement anchor (rank correlation render vs photo) |
| `overnight_refine.sh` | unattended `--refine-all` driver: waits out Opus usage-limit windows and resumes, rebuilds the scene when done |

**`learn/` — learned prior (image → building parameters)**

| file | role |
|------|------|
| `learn/params.py`       | fixed-length parameter vector encoding a building; bridge to `components.build_building` |
| `learn/gen_dataset.py`  | render a synthetic (image, params) dataset via the BlenderMCP socket |
| `learn/headless_gen.py` | same dataset generation in headless Blender (reliable at thousands of samples) |
| `learn/train.py`        | train the ResNet18 image → params regressor |
| `learn/predict.py`      | image → predicted params → build description (agent iteration-0 init) |
| `learn/README.md`       | full write-up of the learned-prior subsystem |

**Reference / vendored**

| file | role |
|------|------|
| `docs/related_work_methods.md` | research notes: image→3D methods, VLM-judge reliability, city-scale pipelines |
| `docs/building_params.md` | parameter-schema v0 design doc (Archicad-style typed params; supervisor direction 07-26) |
| `vendor/bpypolyskel/`     | vendored straight-skeleton library (hipped roofs on true polygon footprints; see its LICENSE) |

## Run the offline demo (no Blender, no API)
```bash
python -m img2city.agent.harness --demo --max-iters 80
```
A self-contained mock: the executor renders a *parametric tower silhouette*, the
agent hill-climbs its parameters toward a hidden target, and the loop keeps only
improving edits. It exists to prove the control flow + logging end-to-end. A
sample run climbed **0.39 → 0.91** over 80 iterations (35 accepted) and logged
~81k tokens. Outputs land in `runs/<timestamp>/`:
`run_log.json`, `tokens.csv`, `tokens.png`, `score_curve.png`, `snapshots/`.

> The mock tower is an abstract stand-in for the mechanism — **not** a Queen's
> Tower result. The real geometry comes from the live Blender wiring below.

## Run a live test — real Claude planner + critic (mock environment)
Puts a **real Claude** in the loop (vision-grounded planning + critique) while the
*environment* stays the offline mock — so it runs with no Blender, and
`tokens.csv` now records **real** per-iteration token usage.

```bash
export ANTHROPIC_API_KEY=...          # you set this; never paste it anywhere shared
python -m pip install --user anthropic
python -m img2city.agent.harness --live --model claude-sonnet-4-6 --max-iters 6
```
Each iteration makes two image-bearing API calls (planner + critic), so start
small (`--max-iters 5–6`): it spends real credits and grows with iterations.

### Use your Max subscription instead of API credits (`--backend sdk`)
Run the same loop through the **Claude Agent SDK**, billed against your Pro/Max
plan rather than pay-as-you-go API credits:
```bash
npm i -g @anthropic-ai/claude-code      # Claude Code CLI (the SDK uses it)
python -m pip install --user claude-agent-sdk anyio
unset ANTHROPIC_API_KEY                 # if set, the key takes precedence -> you'd pay API rates
claude login                            # choose your Pro/Max plan
python -m img2city.agent.harness --live --backend sdk --max-iters 6
```
The Agent SDK has no direct image input, so the planner/critic enable the built-in
**Read** tool to open the render + reference as vision; token usage comes from the
SDK `ResultMessage`. The single most important gotcha: **`unset ANTHROPIC_API_KEY`**
first, otherwise the key overrides your subscription and you pay API rates.

## Going fully live (Blender in the loop)
All three pieces are **implemented**: the planner (`ClaudeAgent`) and critic
(`ClaudeVLMCritic`) are used by `--live`, and `tools.MCPBlenderExecutor` drives a
live Blender through the BlenderMCP socket (localhost:9876), rebuilding from the
best accepted state each iteration so accept/reject stays deterministic.

In practice the fully-live path is **`generate.py`** (below), which owns its own
Blender socket + camera/render wrap and adds the brief / checklist / pairwise-judge
machinery on top; `harness.py --live` remains the minimal loop for demos and
token-usage experiments.

## generate.py — 2026-07-04 upgrades (feedback-loop + library)

Why: 16 logged runs plateaued at best = 0.22–0.47 with ~600k tokens/run. Diagnosis:
(1) the single-call VLM score swings ±0.1 on identical geometry, so accept/reject was
mostly noise; (2) the critique loop got stuck repeating one fix ("add the barrel
vault") because the vault rendered as an invisible dark ghost and the agent had no
memory of failed attempts; (3) the parts library capped how close any spec could get;
(4) render orientation was mirrored vs the reference. Changes:

- **Reference BRIEF** (`--no-brief` to disable): one-time structured decomposition of
  the reference (footprint ratio, storey zones, feature list) injected into every
  generation prompt, so iterations stop re-eyeballing the photo from scratch.
- **Two-phase generation** (`--phase-a-iters`, default 2): massing-only first, then the
  massing keys are LOCKED (enforced by merge, not just prompt) and only features move —
  the supervisor's "teach it step by step" put into the loop.
- **Stabilised scoring** (`--critic-k`, default 2): k rubric samples (median/mean)
  blended 0.7/0.3 with a deterministic silhouette-IoU anchor (from `evaluator.py`,
  previously unused here); near-ties are decided by a pairwise A/B judge (`--no-ab`)
  instead of noisy absolute scores.
- **Attempt history** in refine prompts (last 4 fixes + outcomes) breaks the
  repeated-fix loop.
- **Token diet**: images auto-downscaled to ≤640 px for all VLM calls.
- **Library** (`components.py`): solid light *interior core* behind glazing (glass no
  longer sees through to the black backdrop), ribbed vault with the ridge along the
  correct axis, solid white `ridge_roof` (the "fabric" roof), plaza colonnade off the
  frame, entrance tower that scales, per-mass rooftop-plant snapping, brighter palette.
- **Orientation fixed**: the aerial camera now stands at the **+x** end (matching the
  reference composition; it was mirrored before) and the spec schema states it.
- New worked example `components.BS_DESC3` / template `terraced_long_glass` — the
  hand-tuned library ceiling: silhouette IoU vs modelpic **0.78** (old library 0.51).
  See `data/business_school/claude_test/compare_library_upgrade.png`.

## generate.py — checklist + pairwise judge (default since 2026-07-04, evening)

The absolute VLM score is no longer the accept/reject signal. Literature basis:
BlenderGym (verifier is the bottleneck; scale verification, not generation),
BlenderAlchemy / GPTEval3D (VLMs are reliable at *pairwise choice*, noisy at
absolute scores), CADCodeVerify / TIFA (question-based verification). New default
`--judge checklist` (old behaviour: `--judge rubric`):

- **Checklist** — one-time, from the reference (+ BRIEF): ~12 binary YES/NO checks
  (`checklist.json`), each answerable from a render *alone*. Per iteration one call
  answers them all; score = pass-fraction; **failed checks become the targeted fix
  text** for the next refine — scoring and feedback in one call.
- **Pairwise accept** — `ab_vote`: best-so-far vs candidate judged twice with the
  presentation order swapped (position-bias control); candidate must win a strict
  majority; a split is a tie, decided by the combined score.
- **IoU veto** (`--iou-guard`, default 0.05): a pairwise win is vetoed if the
  deterministic silhouette IoU regresses by more than the guard — a persuasive but
  geometrically worse render can't displace the best.
- Logged per iteration: checklist pass-rate (in the `rubric` column), `iou`,
  combined `score` (0.5·pass + 0.5·IoU — used only for logging/stop/tie-breaks),
  `judge_why` (the vote's reasoning, kept in the agent's attempt history on reject).
- Smoke-tested on Business School data (no Blender needed): 12 sensible checks
  derived; old 0.44-scoring "best" render passes only 25% of them (not even the
  elongated massing) — confirming the old absolute scores were inflated noise.
- **Validated end-to-end** (run `gen/20260704-170553`, same settings as the 16
  rubric runs): silhouette IoU of best render **0.605 → 0.769**, checklist
  pass-rate 0.25 → 0.417, monotonic score curve 0.378 → 0.593 with one correct
  rejection. Cost: 1.10M tokens (+83% vs rubric runs — addressed below).
- **Cost + lock fixes (same day, follow-up):**
  - **Verifier cascade** — the pairwise vote is now only called on MIXED signals:
    if the checklist pass-rate strictly improves AND IoU stays within the guard,
    auto-accept with no vote; if both regress, auto-reject. In the validation run
    this would have skipped the vote on 3 of 6 decisions (~40k tokens/iter saved).
  - **`--judge-model`** — routes the PAIRWISE VOTE calls to a cheaper model, e.g.
    `--judge-model claude-haiku-4-5-20251001`. The checklist INSPECTOR stays on
    the strong model after a validation run showed why: with Haiku inspecting, the
    run "reached" 12/12 checks and stopped early, but the strong model scored the
    same render 4/12 (missing vault, rooftop plant, stone entrance...) — a lenient
    inspector inflates the score, ends the run early, and replaces real fix
    feedback with "all checks pass". Haiku IS reliable at the easier pairwise
    choice (picked the same winners as Fable in spot checks) — hence the split.
  - **Massing-lock escape hatch** (`--unlock-after`, default 2) — if a
    massing/proportions check fails 2 scored iterations in a row while the phase-A
    lock is active, the lock opens, later iterations run phase `full`, and the
    refine prompt is told massing is editable again — so the judge's complaint can
    actually be acted on.
  NOTE: the IoU anchor needs Pillow+numpy in the *same* python that runs
  `generate.py` (it fails silently to `iou=None` otherwise — now installed for
  python3.13).

### Judge v2 (2026-07-11 — from the deep-research pass, related_work_methods.md §J/§O)

Four upgrades, all defaults, driven by verified findings on VLM-judge reliability:

- **k-vote inspector** (`--inspector-k`, default 3): the checklist inspector is
  sampled k times and each check passes by per-check MAJORITY — the checklist-shaped
  version of "mean of 3 samplings" against the documented ±1-2 check flip on
  identical geometry (absolute VLM answers are stochastically inconsistent).
- **One view per question**: checks carry a `"view"` tag (derived with the
  checklist when multiple renders exist) and each inspector call carries exactly
  ONE image — a reference + multi-image panel pushed a VLM judge into answering
  purely by position (100% order flips, arXiv 2606.20364). Untagged roof checks
  route to the top view for old checklists.
- **Swap-consistent pairwise** (`ab_vote`): each vote-pair asks the comparison in
  both presentation orders and counts ONLY if the verdict survives the swap (~26%
  of raw pairwise verdicts are position-biased, arXiv 2606.18451); all-inconsistent
  = an honest tie instead of a coin flip.
- **DreamSim anchor** (`perceptual.py`, `--ds-guard` default 0.06): deterministic
  perceptual distance render↔photo (`pip install dreamsim`, ~1.2 GB weights on
  first use; degrades to None without it). It is the anchor that still works on
  street photos, where sky backgrounds break the silhouette IoU. Validated on our
  own data before being trusted (53 refined city buildings): Spearman −0.33 vs
  checklist pass-rate — a real but MODERATE signal, so it only guards pairwise
  wins and breaks ties, never scores. CLIP-similarity was considered and rejected
  (chance-level quality signal on 3D renders, arXiv 2606.18451).

City pipeline (`city_generate.py`) inherits all four via `--refine`/`--refine-all`
(`--inspector-k` there too); per-iteration `pass`/`ds` history now lands in
`refine/result.json`.

### Straight-skeleton roofs + polygon-mode refine (2026-07-11)

- **`vendor/bpypolyskel/`** (prochitecture, GPL-3.0 — the roof engine behind blosm,
  validated on ~320k OSM hipped roofs): pure-Python straight skeleton, imported
  INSIDE Blender (mathutils lives there; `load_components_src()` injects
  `_VENDOR_DIR` since exec'd source has no `__file__`).
- **`polygon_terrace` roof upgrade**: buildings on their TRUE footprint polygon
  (OBB fill < 0.72 — crescents, wedges, L-shapes) now get a pitched
  hip-and-valley slate roof following the real plan via `_skeleton_roof()`
  (`roof_form` "valley"/"gable"; `"flat"` keeps the old deck; any skeleton
  failure falls back to flat). Verified on the block's worst OBB case
  (fill 0.39, L-shape): correct valley at the inner corner, whole block
  re-rendered at zero LLM cost.
- **Polygon-mode refine path**: `--refine`/`--refine-all` no longer skip these 9
  buildings — the refine loop builds them with `polygon_terrace` in scene
  coordinates and puts the pano camera at the panorama's true scene position, so
  the loop judges exactly what the assembled scene shows. `poly_params()` is the
  single spec→polygon contract shared by assembly and refine.

## synth_views.py — synthetic auxiliary views (weak references)

With a single reference photo, the sides the camera can't see are unconstrained.
`synth_views.py` uses an image-editing model (Gemini "Nano Banana",
`gemini-3.1-flash-image`) to extrapolate the same building from other viewpoints —
the far end, the back facade, a straight front elevation:

```bash
# one-time: key from https://aistudio.google.com/apikey (free tier), then add
# `export GEMINI_API_KEY=...` to ~/.zshrc;  pip install google-genai
python -m img2city.imagery.synth_views --ref data/business_school/modelpic.jpeg \
                       --out data/business_school/synth
python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial \
    --mode assemble --backend sdk \
    --aux-refs synth/farend_aerial.png,synth/back_aerial.png,synth/front_elevation.png
```

Synthetic views are **weak references by design**: `--aux-refs` feeds them into the
BRIEF and the FIRST generation only (with a trust-the-real-reference instruction);
the checklist and all scoring stay on the real photo, so a hallucinated detail can
never become a required feature or inflate a score.

**Max-subscription alternative — `--hidden-brief`** (no image-generation key):
Claude cannot generate images, but it *can* reason about hidden geometry. The flag
adds a one-time vision call that INFERS the unseen sides (back facade, far end,
hidden roof) as structured text with per-item confidence, appended to the BRIEF for
every generation prompt and saved as `hidden_brief.json`. Same weak-reference
discipline: the checklist derives from the pre-inference brief only (an inferred
back-facade feature must never become a required check), and scoring is untouched.

## Notes
- The score (`0.5·IoU + 0.5·width-profile-corr`) is **pluggable** — swap in
  Chamfer distance / F-score (e.g. from the Faithful Contouring metrics) without
  touching the loop.
- Accept-if-improving makes the best score monotonic, so `score_curve.png` is a
  clean convergence record for the report's Evaluation section.
- Dependencies: `numpy`, `Pillow`, `matplotlib` (no scipy, no GPU for the demo).

