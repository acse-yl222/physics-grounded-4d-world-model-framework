---
name: urban-simulation-contract
description: Integrate UrbanWorldModel simulations, scenes and visualization widgets using the repository's src/project/cache layout and versioned result contract. Use for new geometry, urban flow or traffic modules, scene onboarding, and migrations into this framework.
---

# Urban simulation integration

Find the project root containing `AGENTS.md` and `docs/framework/protocol-v1.md`.
Read [the protocol](../../../docs/framework/protocol-v1.md) before choosing paths or
interfaces. Read [the manifest schema](../../../schemas/run-manifest-v1.schema.json)
and [the example](../../../examples/contract-v1/manifest.json) when exporting results.
These repository files are the source of truth; keep the skill with the repository.

For each integration:

1. Identify the simulation module, canonical scene ID, source data, spatial transform,
   time semantics and existing callers. Reuse a compatible widget/data layer before
   adding a specialized renderer.
2. Put reusable computation in `src/<domain>/`; scene configuration in `project/<scene>/`;
   disposable work in `cache/<scene>/<simulation>/<run_id>/`. Preserve originals and
   manual edits. Inspect old manifests/configs rather than inferring units or axes.
3. Export a run manifest and relative assets according to protocol v1. A complete run
   must be reproducible from recorded input/configuration/code identities and must not
   rely on cache files. Use a small synthetic fixture for public examples.
4. Integrate the widget with the shared scene, camera, timeline and selection contract.
   Explicitly declare capabilities and unsupported data formats. Do not create a separate
   viewer per simulation or claim that proposed interfaces are already implemented.
5. Run `python3 tools/check_contract.py <manifest>` and the relevant solver/widget checks.
   Check asset loading, alignment against known scene coordinates, temporal sampling,
   visibility, selection and disposal where supported. Report which checks ran and which
   need a browser or real data.
6. Describe migration and publication scope. Keep data storage configuration local and
   credentials out of manifests. Preserve other contributors' changes and independent
   repository histories. Do not publish datasets merely because their code is public.

For a new data representation, extend the protocol/schema and add a valid example plus
an invalid case that exercises the changed invariant. Increment the major version for
incompatible changes; reject unknown major versions in readers.

## Implemented entrypoints and validation

- `uwm run <scene> --dry-run` inspects a pipeline without computation. Actual runs write
  `cache/<scene>/pipeline/<run_id>`; visualize packages protocol runs, and `--retain`
  copies the bundle into retained runs and registers its named view.
- Use `Storage.load().assets(scene, category)` for data and `Storage.scratch`/`trial_root`
  for intermediates. Local storage/source configuration is ignored by Git. Never restore
  the removed output or input/region symlinks.
- V1.1 supports GLB, NPY, per-frame NPY, terrain heights, explicit invalid masks and sparse
  recorded trajectories. Preserve absent data and original timestamps. Follow protocol
  section 9 and examples/contract-v1.1; do not invent missing geography or replay frames.
- Declare any retained logs/checkpoints/source snapshots in artifacts. Dirty complete runs
  require a source_snapshot with SHA-256. Unknown historical provenance must remain unknown.
- Run `python3 -m unittest discover -s tests -v` and `node --test tests/test_viewer.mjs`.
  Browser tests are `tests/browser_contract.cjs`, `browser_city.cjs`, and
  `browser_experiments.cjs`; real-data tests require the local datasets.
- `pages` is the static deployment branch. `tools/build_public_site.py <site-checkout>`
  overlays public viewer assets onto the previously published site. Never upload local
  project datasets, sources.local.json, storage.local.json, cache, or .history by default.
