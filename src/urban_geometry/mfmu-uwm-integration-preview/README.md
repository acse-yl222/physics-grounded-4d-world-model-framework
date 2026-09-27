# MFMU UAV Scheduler

Publicly visible research-integration preview of the **Mean-Field Multiple-Update (MFMU)** UAV scheduler for inspection and Urban World Model collaboration.

The scheduler combines:

- one whole-batch soft-field recomputation per global round;
- a qualification gate that uses Mean-field guidance only when the signal is stable and non-uniform;
- a uniform fail-closed proposal policy when guidance is not qualified;
- frozen batch proposals and resource-conflict lotteries;
- complete collection-to-drop-off journey construction;
- hard BatteryLedger validation, global closure checks, and independent replay.

This is a clean integration snapshot, not a production release and not the full IRP experiment archive. No non-public Q10000 fixture, run logs, checkpoints, internal receipts, or historical Git repository are included.

## Quick start

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python examples/run_minimal.py
```

Or use the command-line interface:

```bash
mfmu-schedule examples/minimal_scenario.json --output schedule-result.json
```

The bundled minimal example uses `portable_fail_closed`, a finite uniform field that deliberately exercises the audited non-guiding fallback. It runs without PyTorch and is intended to verify the integration contract, journey builder, batch judge, closure logic, and replay.

## Python interface

```python
import json
from mfmu_scheduler import schedule

scenario = json.load(open("examples/minimal_scenario.json"))
result = schedule(scenario, run_seed=0)

print(result["assignments"])
print(result["journeys"])
print(result["validation"])
```

Main inputs:

- station IDs, coordinates, roles, travel times, and distance costs;
- UAV IDs, initial stations, and the frozen homogeneous battery state;
- paired collection/drop-off requests and five-slot drop-off windows;
- optional explicit eligible-UAV sets and a deterministic run seed.

Main outputs:

- request-to-UAV assignments and service slots;
- complete per-request journey segments, including any Hub swap cycle;
- post-journey battery state and safe-Hub certificate;
- global-closure, hard-validation, dry-run/commit, and replay results;
- guidance provenance and controller diagnostics.

The complete JSON contract is documented in [docs/INTERFACE.md](docs/INTERFACE.md).

## Mean-field backend

The source-faithful PyTorch Mean-field engine is included. Install it as an optional dependency:

```bash
pip install -e '.[mean-field]'
```

Then call:

```python
result = schedule(
    scenario,
    backend="mean_field",
    device="cuda",
    run_seed=0,
)
```

The frozen scientific configuration is computationally substantial and was developed for CUDA. Reduced settings may be supplied through `inner_config_overrides` for mechanism-level debugging only; a reduced run is not a replacement for the sealed validation campaign.

## Validation status and claim boundary

The sealed E2 campaign from which this snapshot is derived reached global closure at `Q=10,000`: 10,000/10,000 requests were committed, the final hard-violation count was zero, and independent journey/ledger replay passed.

In that campaign, however, no final owner decision consumed qualified non-uniform Mean-field guidance. All 10,000 final owner decisions used the uniform/no-signal fallback. The result therefore establishes large-scale engineering closure, repeated Inner integration, safe abstention, and hard-validation behaviour. It does **not** establish a Mean-field-caused convergence-rate improvement, scheduling-quality improvement, global optimality, or final-owner advantage.

See [docs/VALIDATION_STATUS.md](docs/VALIDATION_STATUS.md) for the precise interpretation.

## Current integration constraints

- 240 service slots plus row 0 for the initial fleet state;
- the validated homogeneous battery proxy: `B_max=B_init=75`, four energy units per flight slot, zero additional reserve, and a two-slot swap restoring SoC to 75;
- a five-slot drop-off service window beginning at physical collection-to-drop-off arrival;
- station endpoint and Hub capacity are non-binding in this frozen research contract; UAV-time rows remain exclusive;
- serious Mean-field runs require PyTorch and are expected to use CUDA.

These constraints are explicit so an Urban World Model adapter can translate external geometry and request data without silently changing the validated scheduler semantics.

## Tests

```bash
python -m unittest discover -s tests -v
```

The lightweight test suite checks the input adapter, pair-aware readout, complete-journey construction, hard validation, exact closure, and independent replay on synthetic data. It does not reproduce the sealed Q10000 campaign.

## Provenance and use

See [PROVENANCE.md](PROVENANCE.md) for the frozen source identity and the bounded namespace changes made for this repository, and [LIMITATIONS.md](LIMITATIONS.md) before interpreting a result. This repository currently has no open-source licence; see [NOTICE.md](NOTICE.md) before redistribution.
