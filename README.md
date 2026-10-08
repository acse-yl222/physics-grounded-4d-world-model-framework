<h1 align="center">Physics-Grounded<br>4D World Model Framework</h1>
<p align="center"><strong>Explicit geometry. Physical simulation. Evolving worlds.</strong><br>A Levistone project.</p>

<p align="center">
  <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/"><img src="https://img.shields.io/badge/Website-explore%20scenes-287D8E" alt="Website: explore scenes"></a>
  <a href="https://acse-yl222.github.io/urban-world-model-models/"><img src="https://img.shields.io/badge/Resources-browse%20assets-363634" alt="Resources: browse assets"></a>
  <a href="docs/framework/protocol-v1.md"><img src="https://img.shields.io/badge/Protocol-integration%20guide-363634" alt="Protocol: integration guide"></a>
  <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json"><img src="https://img.shields.io/badge/Viewer-try%20the%20example-363634" alt="Viewer: try the protocol example"></a>
</p>

<p align="center">
  Yueyan Li, Zhongkai Yuan, Bohan Ye, Akira Eisenbeiss, Xinyang Miao, Dingyu Xuan,<br>
  Chenxu Li, Hongyu Liu, Yiqi Zhu, Yuhang Dai, Xinran Kai, Christopher C. Pain<br>
  <em>Imperial College London, London, United Kingdom</em>
</p>

A framework for connecting 3D geometry, physical fields and moving agents in a shared, time-dependent world. Bring together scene assets and simulation outputs, preserve their spatial and temporal meaning, and explore them through interactive visualization.

Current applications span urban environments, wind farms and rotor experiments. The same integration protocol is designed to support other settings and scales, including indoor scenes. The fourth dimension is **time**.

<table align="center" width="100%">
  <tr>
    <td width="50%">
      <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=south_kensington"><img src="docs/media/hero_south_kensington_uav.jpg" width="100%" alt="South Kensington geometry with UAV routes and stations"></a><br>
      <strong>South Kensington</strong> · Geometry, UAV routes and urban activity
    </td>
    <td width="50%">
      <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=white_city"><img src="docs/media/hero_white_city_wind.jpg" width="100%" alt="White City geometry overlaid with a wind field"></a><br>
      <strong>White City</strong> · Urban geometry and wind fields
    </td>
  </tr>
</table>

<p align="center">
  <strong><a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/">Explore the interactive scenes →</a></strong><br>
  <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=south_kensington">South Kensington</a> ·
  <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=white_city">White City</a> ·
  <a href="https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/windfarm-movie/">Wind farm</a>
</p>

## How to use

1. **Explore a scene.** Open the [website](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/) to view the published city and wind-farm demonstrations.
2. **Try the shared contract.** The [synthetic example](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json) demonstrates geometry, fields and trajectories in the unified viewer.
3. **Work locally.** Install the framework to inspect scene configurations, serve available data and run a configured simulation pipeline.
4. **Add your own simulation.** Export results through the [integration protocol](docs/framework/protocol-v1.md) and connect them to visualization widgets.

Published scenes currently use their existing specialized viewers. The unified viewer supports protocol-based layers and local scene views; migration progress and validation scope are tracked in the [implementation status](docs/framework/implementation-status.md).

## Requirements

- **Python 3.11+** for the framework CLI, validation and local server.
- **A modern browser** for interactive visualization.
- **Scene inputs and solver dependencies** for real simulation runs. GPU and Blender environments are configured separately where needed.
- **Node.js** for the JavaScript development checks.

A source checkout includes small protocol examples. Large scene datasets and simulation environments are managed separately.

## Install

```sh
git clone https://github.com/acse-yl222/physics-grounded-4d-world-model-framework.git
cd physics-grounded-4d-world-model-framework
python3 -m venv cache/framework/venv
source cache/framework/venv/bin/activate
python -m pip install -e .
```

Inspect the registered scenes and start the viewer:

```sh
p4d scenes
p4d paths south_ken
p4d serve --port 8769
```

Open [localhost:8769](http://127.0.0.1:8769/). When local scene runs are absent, the homepage links open the published scenes. You can also open the [local synthetic example](http://127.0.0.1:8769/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json) directly.

## Installed packages and workspaces

`python -m pip install -e .` supports source development. A wheel includes the
canonical schemas, small examples and static viewers. `p4d validate /path/to/manifest.json`
needs no checkout or scene workspace. Other commands accept `p4d --root /path/to/workspace ...`;
`P4D_ROOT` and the legacy `UWM_ROOT` are also supported, in that order.
An explicit workspace must be an existing directory and can initially be empty.
`p4d --root /path/to/empty-directory serve` can display the bundled synthetic viewer.

`storage.local.json` in that workspace controls `data_root` and `cache_root`.
Code and bundled resources always come from the installed package, independently
of these paths. External historical inputs are configured in `sources.local.json`
or `UWM_SOURCE_<NAME>`; defaults use the configured scene input directory.

Install optional environments with `.[birds]`, `.[traffic]`, `.[geometry]` or
`.[flow]`. PyTorch/CUDA, Blender and external SCALED/Wave PDE installations have
additional platform requirements. These extras do not supply weights or city data.
Package entrypoints include `python -m traffic.train` and
`python -m urban_geometry.birds.scripts.run_sim`. Historical research scripts outside
these maintained entrypoints retain their documented environments.

## Run a simulation

Inspect a scene pipeline first:

```sh
p4d run white_city --dry-run
```

With the scene data and solver environment available, run and retain its outputs:

```sh
p4d run --python /path/to/solver/environment/bin/python white_city --run-id my_trial --retain
```

Intermediate results go to `cache/<scene>/pipeline/<run_id>/`. Retention validates completed outputs, copies them into `project/<scene>/runs/` and refuses to overwrite an existing run. The city pipeline can export a protocol bundle and register it as a scene view.

You can also validate and retain an existing export:

```sh
p4d validate /path/to/trial/manifest.json
p4d retain /path/to/completed/trial
```

## See the results

Open the [local unified viewer](http://127.0.0.1:8769/src/visualization/viewer/) to select available protocol scenes and views. It supports **GLB geometry, NPY fields and frame sequences, JSON metadata, and sparse recorded trajectories**.

Use `p4d serve` to load scene data: its HTTP Range support allows NPY data to be read on demand. Layers retain their declared coordinates, units, masks and time samples; unavailable time ranges appear as missing data. The retained South Kensington traffic replay, for example, covers seconds **1–300**.

## Resources

The [resource catalogue](https://acse-yl222.github.io/urban-world-model-models/) provides selected published geometry and simulation assets. Its companion [repository](https://github.com/acse-yl222/urban-world-model-models) organizes them by scene, type and version:

```text
project/<scene>/<resource-type>/<version>/
```

Each registered resource includes file sizes, SHA-256 hashes and provenance. Some city fields and auxiliary assets remain on the framework's `pages` branch for compatibility. See [resource management](docs/framework/resources.md) for the publication layout and compatibility paths.

## Development

The repository separates reusable implementation, retained scene data and disposable workspaces:

```text
src/
  urban_geometry/       # Geometry processing and 3D agents
  urban_flow/           # Physical models, solvers and flow experiments
  traffic/              # Traffic training, prediction and replay
  visualization/        # Viewers, widgets and data adapters
  common/               # Storage, contracts, pipelines and HTTP serving
project/
  south_ken/            # Scene inputs, configuration and retained results
  white_city/
  windfarm/
  actuator_lab/
cache/                  # Reproducible intermediates and local environments
schemas/                # Run, scene and view contracts
examples/               # Small protocol examples
```

For new scenes, solvers or widgets, follow the [integration protocol](docs/framework/protocol-v1.md). Widgets consume declared data layers; solvers stay in their domain modules. [AGENTS.md](AGENTS.md) and the [simulation integration skill](.agents/skills/urban-simulation-contract/SKILL.md) provide the corresponding agent workflow.

Core checks:

```sh
p4d validate examples/contract-v1/manifest.json
python -m unittest discover -s tests -v
node --test tests/test_*.mjs
```

Keep separate backups of unpublished scene data and external originals. The local `.history/` directory contains migration recovery material and must not be treated as disposable cache. The `main` branch holds source and small examples; `pages` hosts the public site and previously published assets.

## Development and formatting

Use Python 3.11+ and the Node 24 version in `.nvmrc`. Install the pinned development tools once:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . -r tools/requirements-dev.txt
PUPPETEER_SKIP_DOWNLOAD=true npm ci
```

The same entry points run locally, in the commit hook and in CI:

```sh
make format        # Apply formatting to all owned files
make format-check  # Check without changing files
make test          # Both protocol examples, Python tests and all Node unit tests
pre-commit install # Optional: format staged files before each commit
pre-commit run --all-files
```

Ruff formats Python and Notebook code cells; Prettier handles JavaScript, HTML, CSS, JSON, YAML and Markdown; Taplo handles TOML; shfmt handles shell scripts. Formatting uses a 100-column width for Python, Prettier and TOML, four-space Python/TOML indentation and two-space web/shell indentation. Markdown prose is not rewrapped. Notebook output and metadata are retained. This baseline does not introduce lint fixes or import sorting.

[`tools/format.py`](tools/format.py) selects tracked files and new, non-ignored files, then applies the shared [`.prettierignore`](.prettierignore) boundary and Git exclusions. Maintained legacy code, scene configuration and view files are included. Third-party vendors, `.history/`, `cache/`, scene inputs/geometry/runs, synthetic data payloads, published snapshots and recorded provenance are excluded even when tracked. The legacy asset inventory is a generated record and stays unchanged. Unsupported binary formats are never passed to a formatter. Run the unified commands rather than formatting every JSON file recursively. After changing formatting configuration or exclusions, run `make format` and `make format-check` over the whole repository.

The synthetic browser smoke test needs Chrome but no city assets or solver environment:

```sh
npx puppeteer browsers install chrome
make test-browser
```

It starts a temporary server on a free localhost port and checks the five example layers, selection, interpolation, visibility, out-of-range hiding and disposal. Reports and screenshots stay under `cache/framework/browser/`. `CHROME_PATH` can select an existing compatible Chrome installation. Real-city browser tests and GPU/Blender simulations require their own environments and data. The base Python suite reports optional domain import tests as skipped; CI runs those tests separately with the CPU solver dependencies.

[Repository CI](.github/workflows/ci.yml) runs format checks, Python 3.11/3.12/3.14 tests and isolated wheel validation, all Node unit tests, CPU domain imports and the synthetic viewer on PRs to `main`, pushes to `main` and manual dispatch. Tool versions are pinned, npm uses its lockfile, Actions use full commit SHAs, and the workflow has read-only repository permissions. Browser artifacts contain only the synthetic report and screenshot. A repository administrator can make the successful job checks required for merging through branch protection or a ruleset.

The pure formatting commit is listed in [`.git-blame-ignore-revs`](.git-blame-ignore-revs). To hide that commit when investigating code history:

```sh
git blame --ignore-revs-file .git-blame-ignore-revs path/to/file.py
```

## About

**A Levistone project.** Developed by the authors listed above, affiliated with **Imperial College London**. Module contributions are recorded in [Contribution.md](Contribution.md).

The framework began as UrbanWorldModel and now targets geometry- and physics-grounded environments across scales. `p4d` is the primary command; `uwm` and `UWM_ROOT` remain available for compatibility. The [original project overview](docs/history/README-before-framework.md) preserves the earlier context.

### UAV routes and random flight

South Kensington now supports ground-to-ground Wave PDE routes with 30 m vertical
ascent/descent and independent random UAV animation in the integrated city viewer.
See [routing code and reproduction](src/uav_routing/README.md).
