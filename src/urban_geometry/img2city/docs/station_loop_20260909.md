# South Kensington station evidence and refinement experiment

## Scope and outcome

This is a bounded single-building experiment for OSM 101322161, driven by Img2City's reference audit, agent_spec, refine_building, kit renderer and independent reviewer. No building geometry/spec was manually authored. It is not an Astra-vs-Claude controlled comparison, a complete station-complex reconstruction, or a successful visual acceptance run.

Results live in `data/sk_station_loop_20260909/`; execution, model receipts, archived failures and evaluations are in `runs/sk_station_loop_20260909/`. Old thesis sources and the previously exported district remain unchanged. No commit or GitHub upload was performed.

## Evidence recovery

The original cached Google Street View photo showed platform canopy interiors. The first agent audit could not confidently associate that canopy with the 37.5 x 24.1 m target footprint; agent generation correctly refused to proceed. The refusal and original observations are archived, not silently replaced in the original dataset.

Using the existing Google API configuration, the experiment requested a fresh north-up satellite image and a companion image with the target OSM polygon drawn by the Static Maps API. Six panorama candidates were retrieved, and the Img2City Astra reviewer selected candidate 4, showing the red station frontage. Its recorded panorama date is 2024-09. The reviewer explicitly identified the adjoining entrance canopy as outside the target footprint. The new identity audit returned `supported`, with occlusion and roof-height uncertainty disclosed.

The source camera's panorama ID, latitude/longitude, heading, pitch and fov are recorded and bound to the image hash. Street rendering uses those request parameters rather than heuristic aiming. Camera height remains assumed (2.5 m); ground elevation, occlusions and full photogrammetric calibration are not verified. Perceptual/depth anchors and pixel-based tie-breaking are disabled without verified camera evidence. This conservative default now also applies to legacy city refinement calls without a verified audit.

The final overhead comparison uses the Static Maps request's geographic center, north direction and approximate ground extent, calculated with the existing project's map/local-coordinate conventions. It is a geographically aligned comparison, not a certified pixel-perfect registration. The surrounding real scene is absent from the isolated candidate render.

## Code corrections

- Core building construction now distinguishes missing/null masses (legacy default solid block) from explicit empty masses (open structure). The previous `or` expression recreated a block despite the open-canopy parts contract. Validation permits empty masses only with explicit structural extra_parts; the agent schema states this distinction.
- Added a reusable reference audit with file-hash invalidation and explicit target-identity verdicts. Reference audit and target-outline images reach generation/refinement; final review also receives the outline (a missing handoff found during this experiment).
- Added hash-bound recorded street camera and Static Maps top-view camera helpers.
- Refinement feedback now corresponds to the retained best candidate rather than a rejected candidate's failed checks.

The inherited heuristic standoff diagnostic can still print before the recorded camera override. The actual street render applies the recorded position/target after that heuristic. `camera_verified` remains false, so this diagnostic does not cause pixel metrics to be accepted as calibrated.

## Results

The fixed 12-check refinement sequence was 0.583, 0.750, 0.750 (7/12, 9/12, 9/12). The second candidate was retained. These rates are not comparable to earlier canopy-reference scores because the target evidence and checklist changed.

The three remaining checklist failures were: no visible rectangular roof skylight, dark rather than red frontage, and rectangular rather than the reference's large upper arched openings. Both the initial independent review and the review with complete footprint/geographic evidence returned repair in all three calls. Roof articulation and camera correspondence also remain concerns. No visual acceptance or overall quality superiority is claimed.

The recovered-reference generation/refinement/initial-review/export run took about 9.3 minutes, excluding evidence acquisition, code fixes and the later corrected-evidence review. The close oblique presentation image uses the project's existing library-growth renderer; it is separate from the comparison cameras.

Artifacts:
- `data/sk_station_loop_20260909/station_agent.blend`
- `data/sk_station_loop_20260909/station_agent.glb`
- `data/sk_station_loop_20260909/station_oblique.png`
- `runs/sk_station_loop_20260909/aligned_review.json`

## Validation and limits

93 offline tests passed, including empty-mass construction, reference invalidation, recorded heading/fov behavior, satellite center/north/extent and existing migration/acceptance tests. Real Google retrieval, Astra model calls, three refinement iterations, Blender renders and blend/GLB exports completed. Final reports retain the unmet conditions.

This does not implement autonomous indefinite learning/repair. The generator still lacks a complete geographic-to-building-local spatial explanation, its facade/material controls remain restrictive, and final acceptance still needs better artifact-level evidence for editability and provenance. Those are concrete next integration issues, not reasons to reinterpret a failed preview as a pass.
