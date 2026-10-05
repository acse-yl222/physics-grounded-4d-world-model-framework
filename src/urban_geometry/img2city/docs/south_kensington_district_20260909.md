# South Kensington Astra district run

## Scope and provenance

The complete district is produced by the Img2City controller, using `gpt-6-astra` for reference selection, building generation, repair planning, visual refinement and regional review. Codex is the inference transport and development environment; no district building specs or feature geometry were manually authored. The agent assembles its specs through the existing Blender kit and MCP renderer.

Output: `data/south_kensington_astra_district_20260909/`. Logs and model receipts: `runs/south_kensington_district_20260909/`. The previous Astra district supplies unchanged building/scene caches. This is an incremental complete-area run, not a from-scratch regeneration or controlled model comparison. The old thesis repository and previous deliverables are preserved; no commit or upload is performed.

## Completed inputs and refinement

- 73 previously rejected building references were revisited through Google imagery and Astra target selection. 38 received usable replacement references; subsequent generation rejected three of these. The final 252 specs comprise 187 detailed agent specs and 65 fallback shells (38 imagery failures and 27 footprints below 40 square metres).
- The agent separately planned four station infrastructure groups: platform canopy, platforms/visible tracks, cutting wall and road bridge. Their evidence, coordinates, dimensions and elevation assumptions are recorded in `district_features.json`.
- Below-grade feature footprints deterministically create ground openings. Constrained triangulation is required for overlapping rotated openings; both the actual plan and a regression test cover this case. This requires Shapely 2.1 or later.
- The agent chose six prominent buildings for three refinement iterations, with three inspector votes per checklist. Retained scores: station-house 0.750; Ismaili Centre 0.333; Melton Court 0.333; Ampersand Hotel 0.250; school block 0.000; major terrace 0.417. These are per-building checklist rates, not acceptance or inter-building quality rankings.
- Appearance and scene assembly reuse the project flow: 256 trees, 169 road ways, 16 green areas and 237 shop units on 81 buildings, plus other cached streetscape/traffic assets. These counts describe requested assembly inputs; final scene checks are separate.

## Runtime records and acceptance

Completed status: `DISTRICT_EXPORTED`. The controller took 37.3 minutes including its wait for the already-running reference recovery; first model receipt to completion spans 45.2 minutes (excluding initial preparation and the first call's latency). The complete run saved 290 model receipts. These timings include cache reuse and are not a from-scratch estimate.

Deliverables: `south_kensington_astra_district_20260909_textured.blend` (14,931,993 bytes), `district.glb` (68.08 MiB), and `city_agent_aerial.png`, `city_agent_top.png`, `city_agent_street.png`. The GLB header/length check passes; its JSON contains 6,966 nodes, 1,651 meshes and 80 animations. The traffic check reports no sampled collisions over 9,680 moving-vehicle samples. Other machine acceptance checks remain incomplete because several landmarks are fallback shells or unrefined.

All three final agent votes were `insufficient_evidence`. Major objections concern rotated/differently framed overhead imagery; no paired source photograph/identity for the street render; missing station reference/close-up and ambiguous numbered-image citations inherited from feature planning; and lack of an object-level building inventory and spatial shell mapping in the review packet. These are recorded in `district_review.json`; they do not establish a visual pass or certify the remaining geometry. The next quality iteration needs a stronger final evidence packet as well as improvements to the poorly performing building refinements.

`district_status.json` records the current stage, selected repairs and export outcome. `assembly_manifest.json` binds the assembled scene inputs to three rendered views. `district_review.json`, when completed, records the agent's independent whole-area votes. Model receipts contain the actual model, prompts, responses and image hashes.

A successful export is explicitly distinct from full visual acceptance. Only six buildings receive individual refinement in this run, several remain poor, and camera calibration is not verified. The controller must not label the whole district accepted merely because all objects exported. Refer to the final status and review rather than interpreting an intermediate successful generation count as quality approval.

## Reproduction

The controller entry point is `python -m img2city.city.district --out <district-directory> --skip-recovery --refine-limit 6 --refine-iters 3 --workers 3`. It requires the project dependencies, configured Astra transport and a live Blender MCP connection. Omitting `--skip-recovery` additionally runs reference recovery and requires the Google Maps API environment configuration.

The 2026-09-09 invocation waited for the independent 73-building recovery batch using `--wait-recovery-count 73`. Generation used `--no-assemble` so the expensive complete assembly runs once, after refinement. The current Blender scene was backed up before clearing it. Exported files use the experimental directory.
