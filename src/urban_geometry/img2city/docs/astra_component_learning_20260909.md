# Astra component learning and South Kensington regeneration

This experiment runs through `img2city.city.district --learn-components --reuse-refinement`. Every new language/vision model role is explicitly `gpt-6-astra`. It reuses the previous Astra district's specs, imagery and failed checklists; it does not rewrite the inherited component library from scratch.

The output directory is `data/south_kensington_astra_learning_20260909/`; logs and model receipts are in `runs/south_kensington_astra_learning_20260909/`. Learned source, dialect and typology cards are copied into the output's `library/`, selected using `IMG2CITY_LEARNED_PARTS`, `IMG2CITY_SPEC_DIALECT` and `IMG2CITY_TYPOLOGY_CARDS`. Growth is confined to this copy and its explicit regression area, preserving previous artifacts and the shared library.

The project learning planner selects one supported gap cluster from retained unmet checks. This run selected multi-storey projecting window bays on Melton Court (118710790) and Ampersand Hotel (697869266). It classified the station-house's remaining arches/material problems as existing-component usage, not evidence of a missing component. This is the agent's decision, not a manually selected component design.

The bounded workflow is: assemble a baseline; author component code; static checks; standalone Blender construction; reassemble and compare existing scene fingerprints; paired visual checks using the frozen building checklist; adopt only improved buildings; assemble/export the complete district. A failed proposal is returned to the author once with its code and validation error. Non-accepted source is rolled back from the experimental library. Final learning outcome is recorded separately from whole-district quality acceptance.

## Corrections made while connecting the flow

- The component author's conflicting JSON/Python output instructions now consistently require a fenced Python block.
- The author receives complete specs and geographic/local-frame evidence instead of a 400-character spec prefix and a fixed-front assumption. The metadata's oriented footprint is computed before passing this context.
- Component authoring and visual evaluation use independent learning/judge configuration roles; both are Astra in this run.
- Uncalibrated camera comparisons do not compute DreamSim as though viewpoints were registered.
- Smoke checks reject zero-mesh output.
- Polygon-building rendering/assembly previously dropped `extra_parts`. New learned polygon extensions declare an explicit `extra_parts_frame`, propagated to both paths. Adoption persists the exact frame used in the A/B render. Legacy polygon specs without this declaration retain their previous behaviour; this does not claim to repair all historic unframed extensions.

Source code for parts is produced by the project's model call and executed by its existing kit pipeline. Codex edits interfaces/orchestration and runs the project; it does not author the experimental building geometry. No Git commit, push or upload is part of this run.

## Results

Completed in 84.6 minutes. All 37 saved model receipts identify `gpt-6-astra`. The generated component is `storeyed_bay_frontage`; it built 226 smoke-test meshes and passed regression with all 6,782 baseline object fingerprints unchanged.

Paired results: Melton Court 0.333 → 0.333 (not adopted); Ampersand Hotel 0.250 → 0.333 (adopted). Only the latter building uses the new part in the exported district. The new dialect is retained in the experiment's library copy. This is a small measured checklist improvement, not a demonstrated broad quality gain or an Astra-versus-Claude comparison.

Exports: `south_kensington_astra_learning_20260909_textured.blend` (14,982,278 bytes), `district.glb` (68.6 MiB), and three `city_agent_*.png` previews. The GLB version/header/length check passes. Coverage remains 252 buildings including 65 unverified shells. All three independent regional votes were `insufficient_evidence`, principally for unaligned/unpaired imagery, ambiguous source references and missing object/source verification evidence. Full visual acceptance remains unestablished.

Read `component_learning_plan.json`, `component_learning_result.json`, `library_grow/*/report.json`, `district_status.json` and `district_review.json` in the output directory for current/final outcomes. Export completion alone is not a claim of whole-area visual acceptance.
