# Open-source methods for image → 3D building generation

Compiled 2026-06-29; **updated 2026-07-04** (new §F–§I below — supervisor-named tools resolved, verifier literature, city-scale pipeline). Reference for the IRP (Agentic AI for Urban 3D Asset Generation).
Grouped by relevance to *our* goal: a single reference image → an **editable**, simulation-ready 3D building.

---

## A. Single-image → 3D **mesh** generators (photoreal, but NOT editable)
These get closest to "looks like the photo" fastest, but output a **dense, non-editable mesh** — exactly the limitation our thesis argues against. Best use for us: a **baseline to compare against** (editable-but-coarse agent vs photoreal-but-dead mesh).

| Method | Who / License | Approach | Notes |
|---|---|---|---|
| **TRELLIS** | Microsoft, open | multi-view diffusion → reconstruction | Currently leads image-to-3D fidelity; production PBR assets |
| **Hunyuan3D 2.1** | Tencent, open | multi-view diffusion → recon + PBR | High-fidelity textures; closed most of the quality gap |
| **Hi3DGen** | open | normal-bridged geometry | Best *geometric* quality of the group |
| **TripoSR** | Stability + Tripo, **MIT** | single-image feed-forward | Fast (<1 s), 6–8 GB VRAM, biggest community — easiest to start |
| **Stable Fast 3D** | Stability, open | feed-forward | Real-time (<1 s) |
| **InstantMesh** | Tencent, open | multi-view diffusion → recon | Clean topology |

Dominant 2026 pattern = **multi-view diffusion + feed-forward reconstruction** (TRELLIS / Hunyuan3D / InstantMesh) → cleanest topology. Feed-forward single-image (TripoSR / SF3D) → fastest.
*Note:* Hunyuan3D and Hyper3D/Rodin are also reachable directly from our Blender MCP, so we could try one on `modelpic` inside Blender (needs the service's API key / free tier).

## B. LLM / agentic **procedural** 3D (code → editable — our family)
These write code/parameters → **editable** geometry. Most relevant for *improving our agent*.

- **SceneCraft** — LLM agent → Blender Python. Models a **scene graph blueprint → numerical constraints**, then a **VLM self-critique loop** refines it; plus "library learning" (reusable script library). The closest published analogue of our loop. (arXiv 2403.01248)
- **3D-GPT** — multi-agent (dispatch / conceptualize / model) over the **Infinigen** procedural engine. Decompose → parametrize → code. (arXiv 2310.12945)
- **LL3M** — multi-agent LLM → Blender code with **BlenderRAG**: retrieval-augmented generation over Blender 4.4's Python API docs → much better-grounded code than plain code-writing agents. (arXiv 2508.08228)
- **SceneX** — procedural, controllable *large-scale* scene generation via LLMs. (arXiv 2403.15698)
- **BlenderGPT** — basic only (move asset / change texture); limited.

## C. Image → editable **parametric CAD / program** (most aligned with us)
Generate the *program* that builds the geometry → editable, like our component spec.

- **CAD-Coder** — vision-language model: image → executable **CadQuery** Python; reports **100% valid-syntax** rate. Directly relevant to "image → validated parametric code." (arXiv 2505.14646; DeCoDE Lab, MIT)
- **GenCAD** — image → a sequence of **parametric CAD operations** (editable), not a mesh. Research code; use as a reference architecture.
- **Proc3D** — LLM + **Procedural Compact Graph (PCG)**: a compact, editable graph with real-time sliders/checkboxes. Conceptually our "component library + parameters." (arXiv 2601.12234)
- Surveys/lists: *LLMs for CAD: a survey* (arXiv 2505.08137); *awesome-cad* (github.com/mlightcad/awesome-cad).

## D. Building / facade-specific reconstruction
Domain-specific, but mostly research and only reconstruct the **visible** surface (incomplete model).
- *3D Building Façade Reconstruction Using Deep Learning* — depth estimation + GAN facade segmentation. (doi.org/10.3390/ijgi9050322)
- *Image-to-3D Facade Parser for thermal 3D building models*. (arXiv 2508.04406)
- *3D building reconstruction from single street-view images*. (ScienceDirect S1569843222000619)
- NeRF-based facade parsing (dense-capture scenarios).

## E. Procedural engines / libraries (backends to build on)
- **Infinigen** (the procedural engine behind 3D-GPT) — parametric, open.
- **CadQuery / FreeCAD** — Python, B-rep parametric CAD (OpenCascade kernel); scriptable headless.

---

## What this means for our agent (recommendation)
1. **Add a mesh-generator baseline** (TRELLIS or Hunyuan3D on `modelpic`) → gives the report a clean comparison: *photoreal-but-non-editable mesh* vs *our editable-but-coarse agent*. Strengthens the "editable geometry" argument. Can try Hunyuan3D via our Blender MCP.
2. **Borrow grounding from LL3M (BlenderRAG) + CAD-Coder** → retrieve our component-library docs / Blender API into the prompt + enforce validated code, to raise geometry quality and cut errors.
3. **Borrow Proc3D's editable PCG + SceneCraft's scene-graph + VLM critique** → we already have a parts library + a critique loop; these confirm the design and suggest a graph-of-parts representation + library-learning as next steps.

---

# 2026-07-04 update — supervisor's references resolved + verifier literature + city scale

Follow-up research on the 2026-06-30 meeting actions. Items marked ✔ were verified on the web today; unmarked arXiv IDs in the sub-lists come from model knowledge and should be spot-checked before citing in the report.

## F. The supervisor's named tools, resolved

The names "Archcraft" and "FocusCAD" from the meeting do not exist verbatim; the closest real matches (confirm with supervisor next meeting):

- **"FocusCAD" → CADFusion** ✔ — Microsoft Research, arXiv 2501.19054, "Text-to-CAD Generation Through Infusing Visual Feedback in LLMs". LLM generates a *parametric CAD command sequence*; training alternates **sequential learning** (ground-truth sequences → validity) with **visual feedback** (render the output, VLM-judge the render, preference-optimize). Key lesson: the *render*, not the token sequence, is what gets judged. Code: github.com/microsoft/CADFusion.
- **"Archcraft" → ShapeCraft** ✔ (most likely) — arXiv 2510.17603, NeurIPS 2025, "ShapeCraft: LLM Agents for Structured, Textured and Interactive 3D Modeling". Multi-agent framework; represents the asset as a **Graph-based Procedural Shape (GPS)** — a structured graph of sub-tasks/parts — which agents hierarchically parse and *iteratively refine* (modeling + painting). Exactly the "graph-of-parts + step-by-step" structure the supervisor asked me to study. (Alternative candidate: SceneCraft, arXiv 2403.01248, which adds VLM self-critique + a *learned* reusable function library.)

**How these tools structure agent code** (the supervisor's actual question): all converge on the same recipe — (1) a **constrained parametric representation** (command sequence / shape-program graph / spec), never free-form mesh edits; (2) **hierarchical decomposition** into sub-tasks before any code is written; (3) **render-based feedback** looped back into generation; (4) **library/skill reuse** (SceneCraft learns new functions from successful outputs). Our JSON-spec-over-`components.py` design is the same family — what we are missing is (2) full hierarchy and (4) library learning.

## G. Verifier / scoring literature — why our score plateaus and what to do

Our observed ±0.1 noise on identical geometry is the *documented* failure mode of absolute VLM scoring:

- **BlenderGym** ✔ — arXiv 2504.01786, CVPR 2025 highlight. Benchmark of VLM systems editing Blender scenes via code, built on a **generator–verifier loop**. Headline findings: inference compute is better spent **scaling verification than generation**, and the **verifier is the bottleneck** (human verifier ≫ VLM verifier). Directly explains our plateau: 7 sequential iterations with a noisy absolute judge is the known-weak configuration.
- **BlenderAlchemy** (arXiv 2404.17672, ECCV 2024) — tree search over program edits; the VLM only ever does **pairwise selection among candidate renders**, never absolute scores; ablations show the loop's value comes from *selection*, not generation.
- **GPTEval3D** (arXiv 2401.04092, CVPR 2024) — the protocol to copy for evaluation: **pairwise comparisons on decomposed criteria** over multi-view render grids, aggregated with **Elo**; explicitly motivated by unreliable absolute VLM scores.
- **Question-based verification** (CADCodeVerify ~2410.05340; TIFA 2303.11897 lineage) — derive a checklist of **binary VQA questions** from the reference ("3 storeys? gabled roof? window grid 5×4?"), answer them against the render; score = fraction passed, failures become *targeted* edits. More stable and more actionable than a scalar.
- **MLLM-as-a-Judge** (arXiv 2402.04788, ICML 2024) — pairwise ≫ absolute for human agreement; position bias fixed by order-swap + vote.
- Failure-repetition cure: **Reflexion**-style memory of (edit → measured outcome) + always branching from the best state (we added both on 07-04; keep them).

## H. City-scale direction (supervisor's OSM plan) — prior art + feasibility

- **UrbanWorld** ✔ — arXiv 2407.11965. OSM-conditioned 3D city generation: extrudes real OSM footprints in Blender, then an urban MLLM + texture diffusion paints and iteratively refines. Closest published analogue of the supervisor's plan — but geometry stays LoD1 extrusion and facades are *painted, not modeled*; no real per-building street-view grounding.
- **RAISECity** ✔ — arXiv 2511.18005 (Tsinghua FIB lab). Multimodal *agent* framework for "reality-aligned" city-scale 3D worlds; iterative self-reflection + tool invocation; >90% win-rate on perceptual quality vs baselines. Newest and closest competitor — must cite and differentiate (our differentiators: per-building parametric editability + simulation-readiness + real satellite/street-view grounding).
- Others in the family: **CityX** (2407.17572, multi-agent LLM orchestrating PCG plugins in Blender), **CityCraft** (~2406.04983), **SceneX** (2403.15698). Neural-representation cities (**CityDreamer** 2309.00610, GaussianCity, Sat2Scene) produce no editable/watertight meshes — cite as contrast, same argument we already make against splats.
- Tooling for our pipeline: **OSMnx / Overpass API** for footprints + `height`/`building:levels`/`roof:shape` tags (cleaner than the Blosm addon for an agent pipeline: we control the projection); **pyproj** EPSG:4326→27700, subtract a scene-origin anchor → local metric coords (Blosm's own convention; avoids float precision issues); UK **Environment Agency LiDAR** (free 1 m DSM−DTM) for per-footprint height ground truth; **City4CFD** (TU Delft) as the canonical citation for watertight simulation-ready city geometry (our airflow link); **HoliCity** (London street-view panoramas registered to a CAD model) as a possible evaluation set — it is literally our city.
- **Gap statement for the thesis:** no published system does per-building, real-photo-grounded (satellite + street view), agent-generated *parametric editable* models assembled at true geocoordinates for simulation use. That is the contribution.

## I. Decided next steps (ranked by expected impact)

1. **Replace absolute scoring with pairwise selection + binary rubric.** VLM judges only "render A vs render B vs photo" (order-swapped, k-vote), plus a fixed checklist of binary VQA questions derived from the BRIEF; keep silhouette-IoU as the deterministic anchor; accept only if pairwise win AND anchor does not regress. (BlenderGym / BlenderAlchemy / GPTEval3D / CADCodeVerify.)
2. **Breadth over depth:** generate 3–4 candidate specs per iteration and let the verifier select, instead of 7 sequential single-candidate iterations — better results at *lower* token cost since bad branches die early. (BlenderGym's verification-scaling result.)
3. **Library learning:** when a spec fragment scores well and recurs, have the agent abstract it into a new parametric component appended to a learned extension of `components.py`. (SceneCraft / ShapeCraft.)
4. **City pilot with the footprint as the contract:** bounded ~500 m London area → OSMnx footprints → LoD1 extrusion baseline → per-building agent fills parameters (height, roof type, facade grid) judged against per-building satellite/street-view crops → assemble at real coordinates; watertight by construction (closed footprint + parametric roof). Evaluate height error vs EA LiDAR.
5. **Report metrics package:** parameter MAE on synthetic GT (the `learn/` test set), silhouette IoU + rubric pass-rate on real photos, storey/roof accuracy, and a small pairwise-Elo study; demote the raw VLM score to secondary. The prior-init vs scratch-init ablation (iterations-to-threshold, tokens) is the cleanest novelty table.

## Sources (2026-07-04, verified)
- CADFusion: https://arxiv.org/abs/2501.19054 , https://github.com/microsoft/CADFusion
- ShapeCraft: https://arxiv.org/abs/2510.17603 , https://sanbingyouyong.github.io/shapecraft/
- BlenderGym: https://arxiv.org/abs/2504.01786 , https://blendergym.github.io/
- UrbanWorld: https://arxiv.org/abs/2407.11965
- RAISECity: https://arxiv.org/abs/2511.18005

## Sources
- Image-to-3D comparison: https://trellis2.app/blog/best-image-to-3d-models-huggingface , https://www.3daistudio.com/blog/best-3d-model-generation-apis-2026
- Hunyuan3D 2.1: https://arxiv.org/pdf/2506.15442
- SceneCraft: https://arxiv.org/abs/2403.01248
- 3D-GPT: https://arxiv.org/abs/2310.12945
- LL3M: https://arxiv.org/html/2508.08228
- SceneX: https://arxiv.org/html/2403.15698v1
- CAD-Coder: https://arxiv.org/html/2505.14646v1
- Proc3D: https://arxiv.org/pdf/2601.12234
- GenCAD: https://pickuma.com/for-dev/gencad-parametric-cad-from-images/
- LLMs for CAD survey: https://arxiv.org/pdf/2505.08137
- Facade DL: https://doi.org/10.3390/ijgi9050322 , https://arxiv.org/html/2508.04406v1
- awesome-cad: https://github.com/mlightcad/awesome-cad

---

# 2026-07-11 update — deep-research pass on the five 0.426 bottlenecks

Motivation: mean best pass-rate 0.426 on the 62-building block (07-07 refine-all) and the judgement that per-building quality was not yet good enough. Ran a fan-out deep-research workflow (5 search angles → ~15 primary sources fetched → 3-vote adversarial verification per claim; 18 claims survived, several popular claims were *refuted* — noted below, they matter). Items marked ✔ were verified against primary sources on 2026-07-11.

## J. Bottleneck 1 — the judge, not the geometry, caps measurable progress

The verification pass produced a **nuanced** answer, not the fashionable one:

- ✔ Absolute VLM scoring is confirmed-noisy: SOTA VLM judges reach only **32–34% exact agreement** with human ratings on 5-point scales; conformal intervals span 40–70% of the score range (arXiv 2604.25235, "VLM Judges Can Rank but Cannot Score", code: github.com/divake/VLM-Judge-Uncertainty). Judges also over-score bad outputs (+0.9 to +2.0 bias at GT=1).
- ✔ Pairwise + Elo aligns far better with humans: Spearman **0.86 vs 0.36** for pointwise (GenArena, arXiv 2602.06013, Apache-2.0 code: github.com/ruihanglix/genarena). Caveats found by verification: n=7 models, judge-model confound, gains are benchmark-dependent (+25pp best case, +4.5pp worst).
- **✘ REFUTED: "abandon checklists for pairwise."** Adversarial verification killed this claim twice. Binary checklist *decomposition* is itself a documented fix for absolute-scoring noise: CheckEval (EMNLP 2025, arXiv 2403.18771) improves cross-evaluator agreement by **+0.45** vs Likert; TICK (arXiv 2410.03608) raises LLM–human exact agreement 46.4%→52.2%. Pairwise has its own diseases: position bias, intransitivity (arXiv 2406.07791, 2606.17634). **What the literature actually supports is exactly our current hybrid** — binary photo-derived checks for *targeting* edits, pairwise only for A/B *selection* between candidates — with the fixes below.
- ✔ Position bias is large and must be handled: **~26% of raw pairwise verdicts flip** when presentation order is swapped; swap-and-keep-consistent correction moved agreement 0.333→0.714 (arXiv 2606.18451). Query both orders, discard inconsistent verdicts (they double as a "no real difference" signal).
- ✔ Multi-image judging can backfire: a reference + 7-image panel made Qwen2.5-VL answer **purely by position** (100% order flips); fix was two-image single comparisons (arXiv 2606.20364). Relevant to our dual-reference + dual-render prompts: keep per-question image count minimal, route each check to the one view that answers it.
- ✔ A cross-model reliability check is cheap: two independent judge families (e.g. different vendors/architectures) agreeing at κ≈0.66 on swap-consistent pairs is achievable; disagreement flags unreliable checks (arXiv 2606.18451).
- ✔ Normal-map / matcap render montages make geometric defects legible to VLM judges where beauty renders hide them (arXiv 2606.20364) — cheap to add as a third render style for geometry-facing checks.
- **Perceptual metric verdict**: ✔ CLIP render-similarity carries **no usable quality signal** (chance-level 0.48 agreement with a validated judge; negative Bradley-Terry weight — arXiv 2606.18451). ✔ PSNR/SSIM unsuitable for render-vs-photo (arXiv 2506.12563). ✔ **DreamSim** is the defensible pick: ensemble of CLIP+OpenCLIP+DINO fine-tuned on 20k human triplet judgements, beats LPIPS/CLIP/DINO on human alignment (NeurIPS 2023), recommended over LPIPS/SSIM/PSNR for render-vs-real comparison by the NVS metric benchmark (arXiv 2506.12563), `pip install dreamsim`, MIT, two-line API. Verification caveats: never tested specifically on *untextured* archviz-vs-photo; documented foreground-clarity bias. Use as a **deterministic anchor alongside** the checklist (replacing silhouette-IoU where street photos break it), validated on a few of our own pairs first.

## K. Bottleneck 2 — growing the component library instead of hand-feeding it knobs

- **ShapeLib** (arXiv 2502.08884, Jones et al., TOG; v3 2026-05) ✔ — LLM authors a library of parametric shape-abstraction functions from ~20 seed shapes + text descriptions of desired functions, four stages (interface → application proposal → implementation proposal → validation), plus a recognition network mapping geometry → programs. Beats ShapeCoder: F-score 54.0 vs 40.9, voxel IoU 50.0 vs 32.3, fewer functions per shape; edits judged more plausible 75% of cases. No code release; furniture domains — the *recipe* transfers: our terrace-kit v1→v3 growth was exactly this done by hand, and the report can frame a semi-automated version (agent proposes a new `components.py` part + validator when critiques repeatedly name an inexpressible feature).
- **Facade parsing → grammar parameters** (deterministic BRIEF enrichment, no LLM guessing of window counts):
  - Hu et al., ISPRS 2022 (arXiv 2201.08977) ✔ — CNNs classify window type + regress grammar parameters from facade patches, assembled into procedural grammar; semi-supervised adversarial training: +10% type accuracy, +50% parameter estimation. Project page vrlab.org.cn/~hanhu/projects/windows/ (code reported MIT, verify before relying).
  - **RTFP** (Adv. Eng. Informatics 2024, code: github.com/wbw520/RTFP) ✔ — ViT facade segmentation + line-based revision (LAFR) that snaps window/door masks to straight architectural edges; front-end for extracting window-grid counts/spacing from street-view crops (needs a small mask→grid step).
  - FaçAID (SIGGRAPH Asia 2024) — transformer neuro-symbolic facade→split-grammar; newer alternative surfaced during verification.
  - Pro-DG (arXiv 2504.01571) — facade image → split-grammar induction (output is imagery, but the induction stage is the relevant part). GLNet dataset (624 high-res facades, 43k windows) for benchmarking.
- BuildingBlock (Tencent, SIGGRAPH 2025, github.com/Tencent/BuildingBlock) — recent open-source code-based building generation; worth a look for kit patterns.

## L. Bottleneck 3 — arbitrary footprints (crescents, wedges, L-shapes)

- **bpypolyskel** (github.com/prochitecture/bpypolyskel) ✔ — pure-Python straight-skeleton **hipped-roof generator for Blender**, by the blosm authors, built for OSM footprints: `polygonize(footprint, holes) → roof faces + vertex heights`. Tested on **all ~320k hipped roofs in OSM, 99.99% success**, holes supported, only dependency `mathutils`. GPL-3.0 (fine for a research repo). This is the drop-in replacement for our OBB roof on true polygons — M-roof/valley forms can be built from offset strips of the skeleton.
- **CGAL 5.6 straight-skeleton extrusion** (unverified this pass — agents hit the usage cap — but documented at cgal.org/2023/05/09/improved_straight_skeleton/): weighted skeletons (per-edge pitch), direct extrusion to a **closed 2-manifold roof mesh**, max-height truncation (→ mansards). Python access via **scikit-geometry** ✔ (`create_interior_straight_skeleton`, `offset_polygons`; vertex "time" = the roof height field). pyclipper as the light pure-offsetting alternative for parapet rings/setbacks on polygons (our current per-edge parapet code would collapse to one offset call).
- Sat2LoD2 (arXiv 2204.04139, open software) — the rectangulation route: decompose an irregular footprint into packed rectangles, fit a parametric primitive per rectangle. Keeps our rectangular kit untouched; good fallback where the skeleton route fights the terrace kit.

## M. Bottleneck 4 — whole-scene composition (the 07-07 supervisor direction)

- **DeepForest** (github.com/weecology/DeepForest, MIT, v2.1.0 Feb 2026) ✔ — pip-installable pretrained tree-crown detector on aerial RGB → per-tree positions from the satellite tile we already fetch; instantiate parametric trees at real coordinates. Lowest-effort item in this whole report.
- **Blosm** ✔ — imports OSM roads/paths/railways as Blender curves with width profiles, water/forest as polygons; GPL, study-not-vendor. Roads: our own Overpass fetch + swept curve profile is likely simpler and license-clean.
- **CityCraft** (arXiv 2406.04983, code + HF weights) ✔ — DiT layout + LLM per-building planning (function/style/floors as structured output) + Blender asset retrieval. Its *LLM-planning stage* is the useful pattern (ours, but for non-building assets); its layout is generated, not real-OSM — cite and differentiate.
- SceneWeaver (NeurIPS 2025, code) — extensible self-reflective scene-synthesis agent; the "agent refines connections between scene parts" reference the supervisor asked for. SimWorld (arXiv 2512.01078), Proc-GS (CVPRW 2025) — newer road/street-furniture and procedural+splat hybrids. Index: github.com/hzxie/Awesome-3D-Scene-Generation (survey arXiv 2505.05474).

## N. Bottleneck 5 — appearance: texture the parametric geometry, keep it editable

- **UrbanWorld** (github.com/Urban-World/UrbanWorld) ✔ — open end-to-end: OSM scene split into buildings/terrain/others, then **UV-space ControlNet** (weights on HF) textures untextured urban geometry; run_osm.sh entry point. Closest to "make our block read as London brick" without touching geometry. Integration cost: pinned Blender 3.2.2 / Python 3.7+3.8 + Kaolin stack.
- **Paint3D** (CVPR 2024, Apache-2.0, github.com/OpenTexture/Paint3D) ✔ — 2K **lighting-less** UV textures for arbitrary untextured meshes from text/image; relightable, so it preserves the simulation-ready story. Per-building batch over our 62 saved specs is conceptually clean; heavy diffusion/PyTorch3D stack.
- **PUT** (3DV 2021, github.com/ygeorg01/PUT) ✔ — projective texturing from street-view *panoramas* onto urban meshes, **trained on London imagery**; older, but input-matched to our data (we already store pano positions per building).
- Hybrid mesh-gen + editability: a 2026 pipeline (arXiv ~2603/2606 building-generation line) runs TRELLIS → Grounded-SAM component masks → OBB-fitted retrieval **replacement** of doors/windows ✔ — evidence that component-level editability must be *added onto* mesh generators (TRELLIS output is a single unified mesh, no part labels ✔). Keeps our thesis differentiator intact: we get editability by construction. TRELLIS (MIT) remains the photoreal-but-dead-mesh **baseline** to render next to ours (§A recommendation stands, now with verified license/limits). GeoTexBuild (arXiv 2504.08419) ✔ — footprint→ControlNet height map→mesh; no code, cite as related footprint-grounded work.

## O. What actually changes in our pipeline (ranked, impact × effort)

1. **Judge v2 (cheap, unblocks everything else):** keep the binary checklist for targeting; make every pairwise call order-swapped two-image, k-vote, discard inconsistent verdicts; add DreamSim (`pip install dreamsim`) as the deterministic anchor on both street and top views (replaces IoU where street photos broke it); report scores as mean of 3 samplings. Optional: normal-map montage for geometry checks; a second judge family as a reliability probe.
2. **True-polygon massing + skeleton roofs:** bpypolyskel for hipped/valley roofs on real footprints + offset-based parapets (scikit-geometry/pyclipper); rectangulation fallback (Sat2LoD2 style). Kills the OBB-flattening failure class (crescent, wedges) that refine-all could not fix.
3. **Facade-grammar BRIEF enrichment:** run a facade parser (RTFP or Hu et al.) on the street-view crop → window grid counts/spacing/type into the BRIEF as *facts*, like OSM dims — removes the checks the agent chronically misjudges by eye.
4. **Scene layer (supervisor ask):** DeepForest tree positions from our satellite tile + OSM roads as swept curves + railings/street furniture from the existing kit; agent handles connections (SceneWeaver as the citation).
5. **Texture pass (biggest "looks like the photo" jump, heaviest):** Paint3D or UrbanWorld UV-ControlNet over the 62 saved specs (geometry untouched → editability argument intact); PUT if we want photo-projective rather than generative.
6. **Library learning (report narrative + light automation):** frame terrace-kit v1→v3 as manual ShapeLib/SceneCraft-style library learning; add the semi-automated loop (agent proposes a new component when critiques repeat an inexpressible feature).

## Sources (2026-07-11, verified unless noted)
- VLM judging: arxiv.org/abs/2604.25235 , arxiv.org/abs/2602.06013 + github.com/ruihanglix/genarena , arxiv.org/abs/2606.18451 , arxiv.org/abs/2606.20364 , CheckEval arxiv.org/abs/2403.18771 , TICK arxiv.org/abs/2410.03608 , position bias arxiv.org/abs/2406.07791
- Metrics: github.com/ssundaram21/dreamsim , arxiv.org/abs/2506.12563 , arxiv.org/abs/2306.09344
- Library learning / facades: arxiv.org/abs/2502.08884 (ShapeLib) , arxiv.org/abs/2201.08977 + vrlab.org.cn/~hanhu/projects/windows/ , github.com/wbw520/RTFP , arxiv.org/abs/2504.01571 (Pro-DG) , FaçAID dl.acm.org/doi/10.1145/3680528.3687657 , github.com/Tencent/BuildingBlock
- Footprints/roofs: github.com/prochitecture/bpypolyskel , cgal.org/2023/05/09/improved_straight_skeleton/ (unverified) , scikit-geometry.github.io , arxiv.org/abs/2204.04139 (Sat2LoD2)
- Scene: github.com/weecology/DeepForest , github.com/vvoovv/blosm , github.com/djFatNerd/CityCraft , SceneWeaver (NeurIPS 2025) , github.com/hzxie/Awesome-3D-Scene-Generation
- Texture/hybrid: github.com/Urban-World/UrbanWorld , github.com/OpenTexture/Paint3D , github.com/ygeorg01/PUT , github.com/microsoft/TRELLIS , arxiv.org/abs/2504.08419 (GeoTexBuild)

---

# 2026-07-15 update — deep-research pass on the fidelity ceiling (§P)

Motivation: v3/v4 showed pass-rates saturating ~0.36 and DreamSim ~0.69 with facade facts contributing nothing — the ceiling is detail geometry + untextured renders. Fan-out research (5 angles → 104 agents → 3-vote adversarial verification; ran across three usage-cap windows). All items below survived verification (votes noted).

## P. Findings (verified 2026-07-15)

**Detail geometry (angle 1) — no open library ships facade ornament; harvest parts, build ornament in-house:**
- **building_tools** (github.com/ranjian0/building_tools, MIT, v1.0.13 May 2025, Blender 4.0) ✔3-0 — parametric bpy operators for floorplans/floors/doors/windows/multigroup/roofs/stairs/balconies; NO cornice/molding/reveal/ornament, no textures. "Parametric" = redo-panel operators on destructive meshes.
- **Infinigen** (princeton-vl, BSD-3) ✔3-0 — officially supports Mac ARM, CUDA optional (terrain speedup only). Verified parametric factories: WindowFactory, 4 door factories, 6 staircases, walls/floors/ceilings (Indoors). Full-repo search: ZERO exterior ornament generators. Harvest windows/doors (real reveals/frames) as kit upgrades.
- outerreaches/blender-building-generator (GPL-3, young) ✔2-1 — pilasters/parapets/storefronts via direct mesh construction; copyleft caveat.
- **BCGA** (vvoovv/bcga) ✔3-0 — the RIGHT abstraction (CGA facade grammar: footprint→facades→floors→window sections) but license=null, dead since 2021, Blender 2.80 — design reference only. Claims of live-editable UI params were REFUTED 0-3.
- Procedural Building Generator 1.3 (Gumroad, paid) ✔3-0 — only verified geometry-nodes "massing→detailed building" fitter; outputs CC BY 4.0 shippable, generator NOT redistributable; Blender 3.2-era.
- Retrieval-fitting angle overall: NO verified, licensed, maintained open solution — the main open gap.

**Texture in the judge loop (angle 2) — verdict: do NOT texture the judge renders; split the judge into two channels:**
- Colored (splat) renders HID geometry defects from a VLM judge (~50/50 on obvious defects); untextured normal-map 2x2 montages were the documented fix (arXiv 2606.20364) ✔3-0.
- Gen3DEval (CVPR 2025, arXiv 2504.08125) scores geometry on NORMAL-MAP renders with appearance stripped, appearance separately on RGB ✔3-0 — the dual-channel design is published precedent.
- BUT appearance carries human-aligned signal: ablation PLCC 0.79→0.62 without the color branch ✔ — so appearance deserves its own channel, not deletion.
- Swap-consistency (our judge v2 design) re-corroborated ✔3-0; caveat: on near-identical pairs it can discard up to ~94% of verdicts (coverage-for-reliability tradeoff).
- VLM3D (ICML 2026, Apache-2.0, github.com/ai4imaging/VLM3D) ✔3-0 — Yes/No log-odds (z_yes − z_no) dual query over multi-view renders; a continuous, calibration-free scalar alternative to our binary checks.

**Monocular priors on Mac (angle 3) — Depth Anything V2 is verified TWO ways, essentially free:**
- Apple publishes official Core ML DA-V2-Small (huggingface.co/apple/coreml-depth-anything-v2-small, Apache-2.0, ungated): 24.6-33.9 ms at 518², Apple Neural Engine ✔3-0.
- Official PyTorch repo auto-selects MPS; a verifier REPRODUCED inference on Apple Silicon (~1.0 s/image, PyTorch 2.12) ✔3-0.
- Uses: depth-map agreement (photo vs render) as a deterministic massing/relief anchor; facade relief extraction.

**Fundamental ceiling (angle 5) — the DreamSim 0.69 plateau is partly a METRIC FLOOR:**
- DreamSim = CLIP+OpenCLIP+DINO embeddings finetuned on human judgments; the paper documents sensitivity to color/semantic content/style ✔3-0 — an untextured gray render carries an irreducible appearance penalty vs a photo REGARDLESS of geometric detail. The claim that DreamSim "rewards structure over texture realism" was REFUTED 1-2 — do not assume texture-invariance.
- Implication: report geometry progress on the texture-free channel (normal-map checks, depth agreement); use DreamSim on TEXTURED renders for the appearance channel.

## Q. What changes in our pipeline (ranked, impact × effort)

1. **Dual-channel judge**: add a NORMAL-MAP render channel; route geometry/massing checklist checks to it (textured/beauty renders judged only for appearance). Directly addresses the documented VLM blindness. Cheap (a matcap/normal render per iteration).
2. **Depth anchor**: Depth Anything V2 (MPS or CoreML) on photo vs render → depth-agreement score as a second deterministic anchor beside DreamSim; also validates massing where silhouette IoU fails on street photos.
3. **Texture the EVAL, not the judge**: measure DreamSim photo-vs-TEXTURED-render (we already have the block texture layer) as the appearance metric; keep the refine loop's accept/reject on the texture-free channel.
4. **Kit upgrades from Infinigen** (BSD-3, Mac-native): harvest WindowFactory/door factories for real window reveals/frames — the single most-cited missing detail tier — and continue in-house ornament parts (cornice profiles via curve-sweep is a small deterministic part).
5. **Facade-grammar layer** (BCGA as design reference only): footprint→facade→floor→bay subdivision as a spec-level structure, enabling per-bay variation the flat masonry mass can't express.

------

# 2026-08-10 update — §R: region-driven library growth (the generality requirement)

## R. The requirement and where the literature lands

User requirement (08-10): the agent must be GENERAL — dropped into a region it uses that region's part vocabulary; dropped into a NEW region it extends the library itself from the imagery (Google APIs), **without changing what existing regions render**. The literature converges on one recipe with three roles, and we already own most of the parts:

- **ShapeLib** (arXiv 2502.08884, §K) ✔ — the closest prior art: LLM authors a library of parametric shape functions from a seed set + text descriptions of *desired functions*, staged as interface → application proposal → implementation → validation. Our twist: the "desired functions" text is not hand-written — it is MINED from the region's own refine failures (`library_learn.py`), so design intent comes from measured demand.
- **Voyager** (arXiv 2305.16291) ✔ — the skill-library discipline: skills are *executable code*, stored only after iterative prompting with environment feedback + self-verification passes. Maps 1:1 onto our part contract: a part is bpy code, the environment feedback is the Blender render + checklist judge, and a part lands in the library only after verified lift.
- **DreamCoder / LILO / REGAL** family — wake-sleep abstraction learning: collect failed/verbose programs, compress recurring structure into named abstractions, guard against library bloat. Our `unmet` corpus is the wake phase; the MISSING/tuning split in the miner is the bloat guard (never author what an existing knob can express).
- 2026 agent-skill ecosystem work (SkillOps arXiv 2605.13716, SkillCorpus arXiv 2607.15557, survey arXiv 2602.12430) — treats skill libraries as *self-maintaining software ecosystems* with ingest-time curation; supports framing the library as versioned, provenance-tagged, regression-gated software rather than a prompt blob.
- Building-domain LLM+PCG (BuildingBlock arXiv 2505.04051, Proc3D arXiv 2601.12234, CityGenAgent arXiv 2602.05362) — none condition the vocabulary on REGION or guarantee old-region stability. That combination (regional dialects + a measured no-regression property) is our contribution niche.

## R.1 The loop, mapped onto what exists in this repo

1. **Mine demand** (built 08-10, zero-LLM): refine now persists per-iteration `failed` + final `unmet` (the demands surviving refinement = inexpressible, vs not-yet-tuned); `library_learn.py --backfill` recovers the corpus for the 224 pre-change buildings from checklist.json + best.png; `--mine` ranks terms across regions, splitting MISSING (no part/knob names this) from tuning (kit has it) — colour is classified expressible because facade_colors owns appearance.
2. **Propose a part** (to build: `library_grow.py`): agent receives the top MISSING cluster, the reference photos of the buildings that demanded it, components.py conventions (box()/MAT/default-off knobs), and the part contract. It authors: a SIBLING part function (never edits an existing one), a default-off knob, a dialect schema line for SPEC_LINES, validator ranges, and the list of demanding buildings to re-spec. ShapeLib stages 2–3; Voyager skill authoring.
3. **Verify — a three-gate ladder, all three gates already exist:**
   - *smoke*: the part renders standalone without error (existing render path);
   - *no-regression*: reassemble city_sk, `render_regress.py --check` must be CLEAN — geometry fingerprint (verts/faces/dims/materials per object, 6276 objects) byte-stable against the pre-change baseline. This is the gate ShapeLib does not have: they validate the new function works, not that old outputs are untouched. It is the measured form of "existing areas must keep rendering identically".
   - *paired lift*: re-spec + re-render the demanding buildings; checklist pass-rate must improve vs the recorded best (same judge stack, k=3). Crucially the checklist was derived from the photos BEFORE the part existed, so the proposer cannot game the test.
4. **Integrate with provenance**: the schema line lands region-tagged in `SPEC_LINES` (built 08-10: core + dialect assembly, byte-identical for city_sk); the part carries `learned_from: <region>`. Promotion rule: a dialect line moves to core when a SECOND region's mining independently demands it — the objective criterion, no taste involved.

## R.2 Why the isolation claim holds by construction + measurement

Contamination has exactly three channels. (1) Geometry, additive: new part + default-off knob → old specs never mention the key → byte-identical output, enforced by the fingerprint gate. (2) Geometry, edits to existing parts: banned by contract (sibling parts only). (3) The prompt: the flat SPEC_SCHEMA was the real leak — every region's agent saw every region's vocabulary; per-region assembly closes it (a Kensington building never sees a canal-gable line). Channels 1+3 are machine-checked; channel 2 is a one-line rule backed by the same fingerprint gate (an edited part changes old objects → DRIFT → reject).

## R.3 Dry-run before any new region

The city_sk backfill already surfaced a MISSING cluster with a known ground truth: "translucent glazed roof / exposed steel lattice / wedge-tip footprint" — the South Kensington station shed, which we hand-built as STATION_BUILD on 07-27. Running the growth loop on THIS cluster first is a controlled experiment: the loop should independently author what we already know the right answer looks like, with the hand-built version as reference. Only then point it at a genuinely new region (stage 1: Barbican, brutalist; the London dialect should mostly idle and the miner should surface access decks / exposed frame / deep balcony bands).

## Sources (2026-08-10, §R — what each one contributed)

Core recipe (read, verified ✔):
- **ShapeLib** — Jones, Ritchie et al., *ShapeLib: designing a library of programmatic 3D shape abstractions with Large Language Models*, arXiv 2502.08884 ✔ (first surveyed 07-11, §K). **Referenced for:** the staged propose→implement→validate workflow for LLM-AUTHORED parametric part functions — the template for `library_grow.py`'s propose step. **Our two departures:** (1) their "desired functions" arrive as hand-written text; ours are MINED from the region's refine failures (`unmet` → `library_learn.py`); (2) their validation checks the new function works — it never checks that OLD outputs are untouched; our `render_regress.py` fingerprint gate adds exactly that property.
- **ShapeCoder** — Jones et al., *Discovering abstractions for visual programs from unstructured primitives*, SIGGRAPH Asia 2023 / TOG (arXiv 2305.05661) ✔ — ShapeLib's predecessor and its evaluation baseline; cited for the abstraction-discovery lineage.
- **Voyager** — Wang et al., *Voyager: an open-ended embodied agent with large language models*, arXiv 2305.16291 ✔. **Referenced for:** the skill-library discipline — skills are EXECUTABLE CODE, admitted to the library only after iterative prompting with environment feedback + self-verification. Maps 1:1 onto our part contract: part = bpy code; environment feedback = Blender render + checklist judge; admission = the three-gate ladder (smoke → regress CLEAN → paired lift).
- **DreamCoder** — Ellis et al., *Bootstrapping inductive program synthesis with wake-sleep library learning*, PLDI 2021 (arXiv 2006.08381) ✔. **Referenced for:** the wake-sleep framing — collect failure/usage evidence in the wake phase, compress recurring structure into named abstractions in the sleep phase. Our `unmet` corpus IS the wake phase; `--mine` is a deterministic stand-in for the sleep phase.
- **LILO** — Grand et al., *Learning interpretable libraries by compressing and documenting code*, ICLR 2024 (arXiv 2310.19791) ✔. **Referenced for:** LLM-guided library growth with explicit BLOAT CONTROL — the reason the miner splits MISSING from tuning (never author a part for a demand an existing knob already expresses).
- **ReGAL** — Stengel-Eskin, Prasad, Bansal, *Refactoring programs to discover generalizable abstractions*, ICML 2024 (arXiv 2401.16467) ✔. **Referenced for:** discovering shared abstractions from recurring structure across programs — supports mining across BUILDINGS (a demand seen on 10 buildings is a part; on 1 building it is that building's problem).

Framing support (surfaced by 08-10 search, snippet-verified only — read before citing in the report):
- **SkillOps** — arXiv 2605.13716, *Managing LLM agent skill libraries as self-maintaining software ecosystems*. **Referenced for:** treating the library as versioned, provenance-tagged, regression-gated SOFTWARE — the framing behind `learned_from` tags + the regress gate as CI.
- **SkillCorpus** — arXiv 2607.15557. **Referenced for:** ingest-time curation (verify before admitting a skill), the same position our three-gate ladder takes.
- **Agent-skills survey** — arXiv 2602.12430. **Referenced for:** skills as composable, dynamically LOADABLE modules — the per-region `spec_schema(region)` assembly is exactly load-what-this-context-needs.

Contrast set — the niche claim (building-domain LLM+PCG, none region-conditioned, none with an old-output stability guarantee):
- **BuildingBlock** — Tencent, SIGGRAPH 2025 (arXiv 2505.04051, github.com/Tencent/BuildingBlock) ✔ §K.
- **Proc3D** — arXiv 2601.12234, LLM procedural generation + parametric editing of shapes (snippet-verified).
- **CityGenAgent** — arXiv 2602.05362, agentic procedural city generation (snippet-verified).

Also load-bearing for §R but internal: the three hand-run library rounds (logbook 07-14 / 07-19 / 07-20) and the 07-26 schema-growth loop — the empirical evidence that mine→implement→re-score converges in THIS pipeline, which none of the external work can show for us.

------

# 2026-08-10 update — §S: the world has more than two styles (open-set typology discovery)

## S. Why enumeration fails, and what the literature actually offers

User question: the world is not offices + terraces — there are countless styles; how can a typology library cover it? Checked both candidate foundations:

- **No authoritative facade-vocabulary taxonomy exists.** Every established scheme is purpose-built for something else: **LCZ** (Stewart & Oke; 10 urban + 7 natural classes) classifies URBAN FORM for climate modelling — its global maps (essd.copernicus 2022, So2Sat LCZ42 arXiv 1912.12171) prove a SMALL class set covers the world's built form, but its classes (compact midrise...) say nothing about window grammar; **TABULA/EPISCOPE** types EU residential stock by size+age for ENERGY retrofits; art-historical style datasets (~25 classes) cover canonical styles only; OSM `building=` values are a folksonomy. Conclusion: enumerate-the-world-upfront is not a viable design.
- **VLM zero-shot architectural classification is established practice**: GPT-4 zero-shot building AGE classification from facades (ISPRS Archives 2024); urban-scale facade MATERIAL mapping from street view with VLMs (Sci Reports 2026, s41598-026-51028-6); open-vocabulary detectors evaluated for architectural typology on heritage buildings (Heritage 2026, 9050206). The VLM's pretrained prior over world architecture is the world coverage we do not have to build ourselves.

## S.1 Design: typologies are DISCOVERED, not enumerated — the grow loop lifted one level

The part library already answers this question one level down: we never enumerated parts either — demand mining discovers them. Same mechanism for typologies:

1. **Dialect card.** Every dialect carries a card: name, one-paragraph description, discriminative visual cues, 2-3 exemplar photos from where it was learned, demand-term profile (from the miner). Authored by the agent when the dialect is born; cards are text — cheap.
2. **Per-building zero-shot selection.** At spec time the building's photo + function + dims are matched against the card deck (VLM zero-shot, the ISPRS/SciReports-validated task) → top 1-2 dialects or **"none fits"**. Schema = core + matched dialects. Misclassification cost stays bounded: cards add OPTIONS, the photo+judge still decide (see 08-10 discussion: the flat schema exposed every SK terrace to tower vocabulary for a month with zero style bleed).
3. **"None fits" IS the discovery signal.** Such buildings run on core alone; their unmet demands accumulate; when a cluster of none-fits buildings shares a demand profile, the grow loop authors a NEW dialect + its card. The taxonomy grows exactly where the world disagrees with the library — demand-first, like every part before it.
4. **Convergence controls** (the library must converge, not fragment): *reuse-before-author* — a new cluster is matched against existing cards' demand profiles first, and gate-3 tries ADOPTING the existing dialect before writing parts; *promotion* — a dialect adopted by buildings in a second region graduates toward core; *merge* — two dialects whose demand profiles overlap heavily are candidates for unification (flagged by the miner, decided by the same paired-lift evidence).
5. **Seed deck, not seed taxonomy**: ~15-20 coarse cards (victorian_terrace, cbd_tower, canal_house, machiya, brutalist_estate, gothic_church, industrial_shed, shophouse, panel_housing, courtyard_vernacular, ...) written up-front as TEXT ONLY — no parts until a region demands them. Cuts cold-start misclassification without pretending to enumerate the world.

## S.2 Why the scale argument survives "countless styles"

The head is fat and the tail is long but thin: LCZ covers global urban form in 17 classes; building-stock archetype work (TABULA) covers national stocks with dozens of types; the countless remaining styles are LOCAL — each one is a small dialect learned once from the region that demands it, at the measured cost of one grow-loop run (~150k propose + gates). The scaling claim to plot in the report: **new parts authored per new region should DECAY as the deck fills** — the library converges to O(head typologies) + a pay-as-you-go tail. If that curve does not decay, the thesis claim is falsified — it is a measurable commitment, not hand-waving.
