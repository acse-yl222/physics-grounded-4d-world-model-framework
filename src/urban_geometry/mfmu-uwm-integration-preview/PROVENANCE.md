# Provenance

## Frozen source authority

- Source commit: `fa1f47994659550586748888c9d6323ac9f1fa83`
- Source branch: `feature/r3-global-multiple-update-v3r4-batch-hard-judge-v3`
- Source bundle SHA256: `d85176bbf1c871e58352198c73e4ed53adb7c2dd684073cc305c7bde072c2c92`

The repository contains the bounded dependency closure needed for the MFMU controller, pair-aware readout, resource lottery, BatteryLedger journey layer, and PyTorch Mean-field engine. The source bundle and its historical Git metadata are not included.

## Bounded portability changes

Four flat imports in the E2 bounded-study modules were changed to package-relative imports:

- `controller.py`: `batch_judge`, `readout`, `resource_lottery`, and `rng`;
- `batch_judge.py`: the local `rng.station_identity` import;
- `inner.py`: `equiv_backend` and `rng`;
- `resource_lottery.py`: `rng`.

The eager exports in `src/ai4pde/__init__.py` and `src/core/__init__.py` were reduced to the included dependency closure, preventing imports of unrelated planner and transit modules.

Self-test fallback paths were changed from the original workstation location to a repository-relative path. The non-public E2 fixture loader itself is intentionally not included.

No algorithmic expression, decision rule, battery rule, resource lottery, readout threshold, or closure condition was changed in those source modules.

The `mfmu_scheduler/` adapter, JSON example, documentation, and lightweight tests are new integration material. They are not part of the sealed E2 evidence package.
