# UrbanWorldModel project instructions

For new simulations, scene onboarding, geometry/traffic/flow integration, visualization
widgets, or structural migration, read `.agents/skills/urban-simulation-contract/SKILL.md`
and follow `docs/framework/protocol-v1.md`. This protocol governs new integrations.
Do not automatically refactor unrelated legacy code to match it.

Target ownership: reusable code in `src/`, scene-specific inputs/configuration/results in
`project/<scene>/`, disposable intermediate artifacts in `cache/`. Widgets are presentation
adapters; simulation solvers do not belong in widgets. Use `south_ken` and `white_city` as
canonical scene IDs; translate legacy IDs at adapter boundaries.

The current tree is transitional. Existing `pipelines/`, `input/`, `configs/`, `expansion/`
and viewer assets remain legacy until individually migrated and verified. Do not assume
that the new unified viewer or simulation runner already exists. Preserve nested Git
repositories, uncommitted work, coordinate transforms and input provenance when migrating.

Validate protocol examples with `python3 tools/check_contract.py examples/contract-v1/manifest.json`.
Install its dependencies from `tools/requirements-contract.txt` if needed. Additional
behavioral checks depend on the simulation/widget being changed. Publication of future
runs or changes requires authorization for that task; this file grants none.
