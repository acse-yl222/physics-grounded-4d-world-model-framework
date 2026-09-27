# Physics-Grounded 4D World Model Framework project instructions

For new simulations, scene onboarding, geometry/traffic/flow integration, visualization
widgets, or structural migration, read `.agents/skills/urban-simulation-contract/SKILL.md`
and follow `docs/framework/protocol-v1.md`. This protocol governs new integrations.
Do not automatically refactor unrelated legacy code to match it.

Target ownership: reusable code in `src/`, scene-specific inputs/configuration/results in
`project/<scene>/`, disposable intermediate artifacts in `cache/`. Widgets are presentation
adapters; simulation solvers do not belong in widgets. Use `south_ken` and `white_city` as
canonical scene IDs; translate legacy IDs at adapter boundaries.

Main source directories have moved into `src/`; scene assets are under `project/`.
The legacy `pipelines/`, `input/`, `configs/`, `expansion/`, and `visualizer/` roots no
longer exist. Read `docs/framework/implementation-status.md` for remaining migrations.
Original repository histories, status records and patches are retained under `.history/`;
this is recovery material, not disposable cache. Do not publish it or discard it.
The canonical viewer supports GLB, NPY, JSON and sparse recorded trajectories.
Preserve coordinate transforms and provenance; never invent missing traffic frames.

Validate protocol examples with `python3 tools/check_contract.py examples/contract-v1/manifest.json`.
Install its dependencies from `tools/requirements-contract.txt` if needed. Additional
behavioral checks depend on the simulation/widget being changed. Publication of future
runs or changes requires authorization for that task; this file grants none.
