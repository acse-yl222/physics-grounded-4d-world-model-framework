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

All changes must pass the `E2E smoke` CI check. Use `make test-e2e` for the local
equivalent; setup, coverage and required merge-rule configuration are documented in
`docs/framework/e2e-ci.md`. Keep this check unconditional for pull requests.

Title pull requests `<type>(<scope>)!: <summary>` (Conventional Commits), at most 72
characters, with an imperative summary of the change in lower case apart from proper nouns.
Types: `feat` adds a capability, `fix` corrects wrong behaviour, `refactor` keeps behaviour,
plus `perf`, `test`, `docs`, `ci`, `build` and `chore`. The scope names the area whose
behaviour changes: `traffic`, `uav` (uav_routing), `flow` (urban_flow), `geometry`
(urban_geometry other than birds), `birds`, `pipeline` (common/pipeline), `protocol`
(protocol export and validation), `cli` (the rest of common), `viewer` (visualization) or
`scenes` (`project/` data); `ci`, `docs`, `build` and `chore` may omit it. `!` marks changes
after which existing results must be regenerated or relied-on behaviour such as exit codes or
published pages differs.

Commit messages use the same format for the subject, then a blank line and a body saying
what changed and why, grouped by change type when it covers several, wrapped at 72
characters where possible, with trailers last. Describe the change, not how it was made.
A single-commit pull request is squashed with its commit subject, so that subject must equal
the title. Squash `fixup!`/`squash!`/`amend!` commits before pushing; `Revert "..."` subjects
from `git revert` and merge commits are accepted. The `PR title and commits` check applies
`tools/check_commit_message.py` to the title and every commit of a pull request;
`pre-commit install` also installs it as a local `commit-msg` hook.
