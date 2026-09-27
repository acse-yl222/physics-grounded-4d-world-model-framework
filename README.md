# Physics-Grounded 4D World Model Framework

A framework for representing, simulating and exploring evolving 3D environments through explicit geometry and physics. The fourth dimension is time: geometry, physical fields and agent trajectories share a scene context for simulation and visualization.

[Explore the scenes](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/) · [Browse resources](https://acse-yl222.github.io/urban-world-model-models/) · [Resource repository](https://github.com/acse-yl222/urban-world-model-models) · [Integration protocol](docs/framework/protocol-v1.md)

**Authors:** Yueyan Li, Zhongkai Yuan, Bohan Ye, Akira Eisenbeiss, Xinyang Miao, Dingyu Xuan, Chenxu Li, Hongyu Liu, Yiqi Zhu, Yuhang Dai, Xinran Kai

**Affiliation:** Imperial College London, London, United Kingdom

## Overview

The framework connects scene geometry, domain-specific solvers and visualization through a common data contract. Geometry and physical assumptions are represented explicitly; adapters expose simulation results to reusable visualization widgets.

Current applications include urban environments, wind farms and rotor experiments. The architecture is intended to accommodate other settings, including indoor environments, through the same integration protocol. Supported data include GLB geometry, NPY fields and frame sequences, JSON metadata and sparse recorded trajectories.

The framework is under active development. Published scenes retain their existing specialized viewers, while the unified viewer supports protocol-based layers and local scene views. See the [implementation status](docs/framework/implementation-status.md) for migration progress and verification scope.

## Explore online

The [scene homepage](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/) brings together the published demonstrations:

| Scene | Focus | Open |
| --- | --- | --- |
| South Kensington | Urban geometry, environmental fields, traffic and flight replays | [Scene viewer](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=south_kensington) |
| White City | A 9 km² urban scene with environmental fields and traffic information | [Scene viewer](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/3d/?scene=white_city) |
| Wind farm | Terrain, turbines, time-varying wind fields and wake-model comparisons | [Scene viewer](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/viewer/windfarm-movie/) |

The separate [unified protocol example](https://acse-yl222.github.io/physics-grounded-4d-world-model-framework/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json) uses synthetic data to demonstrate the common visualization contract.

## Project organization

Reusable code belongs in `src/`, scene-specific inputs and retained results in `project/`, and reproducible intermediate files in `cache/`.

```text
src/
  urban_geometry/       # Geometry processing, voxelization and 3D agents
  urban_flow/           # Physical models, solvers and flow experiments
  traffic/              # Traffic training, prediction and replay integration
  visualization/        # Unified viewer, widgets, adapters and legacy viewers
  common/               # Storage, contracts, pipelines and local HTTP serving
project/
  south_ken/            # South Kensington scene configuration and assets
  white_city/           # White City scene configuration and assets
  windfarm/             # Wind-farm scenes and retained experiment runs
  actuator_lab/         # Rotor experiments
cache/                  # Disposable intermediates and local dependency environments
schemas/                # Run, scene and view contracts
examples/               # Small, self-contained protocol examples
docs/                   # Integration, resource management and implementation notes
```

Scene IDs and existing domain module names remain stable as the framework expands beyond urban applications. Visualization widgets consume declared data layers; simulation solvers remain in their domain modules.

## Run locally

Use Python 3.11 or later. From the repository root, create an environment and install the framework:

```sh
python3 -m venv cache/framework/venv
source cache/framework/venv/bin/activate
python -m pip install -e .
p4d scenes
p4d paths south_ken
p4d serve --port 8769
```

Open [the local scene homepage](http://127.0.0.1:8769/). When local scene runs are absent, the scene links open the published website. The [local unified viewer](http://127.0.0.1:8769/src/visualization/viewer/) exposes available protocol scenes and views; the [synthetic example](http://127.0.0.1:8769/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json) can be opened independently.

The local server supports HTTP Range requests for reading NPY data on demand. Use `p4d serve` for scene exploration, since a generic static server may not support these requests. Cloning and installing the framework provides the code and small examples; running real simulations also requires the relevant inputs, solver dependencies and compute resources. GPU and Blender environments are configured separately.

## Run simulations and retain results

Inspect a scene pipeline before running it:

```sh
p4d run white_city --dry-run
```

With the required scene data and solver environment available:

```sh
p4d run --python /path/to/solver/environment/bin/python white_city --run-id my_trial --retain
p4d validate /path/to/trial/manifest.json
p4d retain /path/to/completed/trial
```

Runs use isolated workspaces under `cache/<scene>/pipeline/<run_id>/`. Retention validates a completed run or protocol bundle, copies it into `project/<scene>/runs/` and refuses to overwrite an existing run. The city pipeline's visualization stage can export a protocol bundle; `--retain` also registers its scene view.

Preserve recorded coordinates, units, time samples and data masks when integrating results. The viewer marks unavailable time ranges as missing data. For example, the retained South Kensington traffic replay covers seconds 1–300; metadata describing a longer simulation does not imply that all frames are available.

## Add a scene, simulation or widget

Start with the [integration protocol](docs/framework/protocol-v1.md). It defines the scene and run manifests, layer metadata and responsibilities of visualization adapters. Place reusable implementation code in `src/`, add scene configuration under `project/<scene>/`, and use `cache/` for experiments before retaining validated outputs.

For agent-assisted development, [AGENTS.md](AGENTS.md) points to the repository's [simulation integration skill](.agents/skills/urban-simulation-contract/SKILL.md). These instructions keep future integrations consistent with the same structure and contract.

Validate a protocol example and run the core checks with:

```sh
p4d validate examples/contract-v1/manifest.json
python -m unittest discover -s tests -v
node --test tests/test_viewer.mjs
```

The JavaScript checks require Node.js. Browser and domain-specific validation evidence is recorded in the implementation documentation.

## Resources and publication

The framework repository owns code, schemas, scene configuration and small examples. The companion [resource repository](https://github.com/acse-yl222/urban-world-model-models) stores selected published geometry and simulation assets, organized as:

```text
project/<scene>/<resource-type>/<version>/
```

The [resource catalogue](https://acse-yl222.github.io/urban-world-model-models/) records asset versions, file sizes, SHA-256 hashes and provenance. Its historical repository address is retained for compatibility. Some existing city fields and auxiliary assets remain on the framework's `pages` branch; see [resource management](docs/framework/resources.md) for ownership and compatibility details.

The `main` branch contains the framework source, while `pages` hosts the public website and previously published scene assets. Large local datasets are excluded from normal source publication. Keep separate backups of unpublished `project/` data, external data originals and `.history/`, which holds local migration recovery material and must not be treated as disposable cache.

## Project history

This project began as UrbanWorldModel. Its scope now covers geometry- and physics-grounded environments across scales. The package and repository are named `physics-grounded-4d-world-model-framework`; `p4d` is the primary command, with `uwm` and `UWM_ROOT` retained for compatibility.

The [original project overview](docs/history/README-before-framework.md) and [contribution record](Contribution.md) preserve the earlier context and credits.
