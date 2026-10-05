# Agent acceptance, 2026-09-09

## Responsibility and scope

Img2City owns generation, rendering and review. The configured Astra transport only returns inference responses; this implementation does not use Codex to author district geometry or manually approve buildings. The original thesis repository and prior district results were not changed by this work.

The thesis describes reference-derived checks, repeated judgments, matched views and documented exclusions. Its reported aggregate result is not a universal acceptance cutoff. The existing `make_city.verify` is a machine/completeness check, not a visual quality decision: a landmark with any refinement result previously satisfied its refinement-presence test.

## Implemented

`img2city quality --out <experimental-area>` performs independent agent acceptance. `make-city --yes` invokes it automatically after assembly/export. A run that skips paid visual acceptance or export returns nonzero, even if machine checks pass. Consumers must use `quality/latest.json`, not the machine report's `ok`, as the visual verdict.

The agent defines a contract without seeing candidate images/scores and saves it in `quality/contract.json`. Subsequent reviews reuse that contract. Every eligible building is freshly rendered using the production spec rendering context, with street, top and normal views, optional second street and textured appearance views. The agent compares these with source references. Three independent calls provide verdicts, explanations and categorized issues. Two passing votes are necessary; any major/critical objection or insufficient-evidence vote blocks acceptance. This conservative veto can reject a good candidate because of reviewer noise; three samples of one model are not three independent model families.

The region gets a separate three-call review against the satellite image, all building results, machine checks and explicit fallback-shell disclosures. A fallback shell is never counted as visually verified. The reviewer must accept the disclosed limitations before `PASS_WITH_LIMITATIONS` is possible; an all-shell district cannot pass. Missing specs, layers, machine-check failures, render failures or malformed model responses fail closed. There is no fixed mean-score acceptance threshold.

Assembly records hashes of its scene inputs and output views. Acceptance rejects absent/stale manifests or changed images, and checks inputs again after review. Old assembled regions require reassembly before this acceptance command can evaluate them. The manifest is evidence of the assembly inputs/renders, not yet a hash-based certification of the exported `.blend` or every external dependency. Per-building review records include reference/candidate hashes and current spec hash.

`quality/latest.json` is invalidated at review start; timestamped reports and fresh images remain available for audit. Existing checklist and pairwise refinement methods remain in place. The final acceptance review is a new cross-view evaluation, distinct from the thesis's per-view checklist scoring.

## Still required before claiming unattended convergence

This change implements acceptance, not the complete acceptance-to-repair controller. Categorized actions (`refine`, `imagery`, `learn`, `scene`) are recorded, but the new reviewer does not yet dispatch them automatically. Existing fixed-round refinement happens before acceptance. The learning pipeline must gain transactional rollback/isolation before it can safely be invoked automatically: it currently installs a candidate before validation and can leave it installed after failure. Automated evidence recovery, repair scheduling, bounded retries and final artifact provenance remain to be connected/tested.

No full South Kensington regeneration or paid acceptance benchmark was started for this change. Earlier 4–8 hour estimates covered fixed-round generation/refinement, not time until this new acceptance contract is met. Completion time to acceptance needs a representative closed-loop pilot; nonconvergence must remain an explicit incomplete result.

## Offline validation

The unit suite passed 82 tests after the initial acceptance implementation. Subsequent focused tests passed 28 tests (11 acceptance-policy tests plus 17 migration regression tests), covering serious-objection vetoes, missing evidence, malformed decisions, frozen contracts, stale assembly/images, complete coverage, all-shell rejection and input changes during review. No Blender, model tokens or network access were required by these tests. Live rendering/model acceptance and complete unattended regeneration remain unverified.
