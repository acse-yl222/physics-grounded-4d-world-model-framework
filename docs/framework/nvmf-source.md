# NVMF runtime provenance

The scheduler under `src/uav_scheduling/_vendor/` is a namespaced copy of the
bounded FieldFleet runtime supplied as `IRP-Final Codes/scheduler`. The public
integration interface is `uav_scheduling`; the private package hierarchy retains
historical module names to make comparison with the source straightforward.

The mean-field framework originated in Professor Christopher Pain's work.
BoHan Ye developed and integrated the FieldFleet scheduling implementation and
experiments with supervision from Christopher Pain and Yueyan Li. This package
preserves the original use and redistribution notice at
[`src/uav_scheduling/NOTICE.md`](../../src/uav_scheduling/NOTICE.md). It does not
introduce a new open-source licence.

## Source identity

The source package's `PROVENANCE.md` identifies its underlying frozen authority as:

- Commit: `fa1f47994659550586748888c9d6323ac9f1fa83`.
- Branch: `feature/r3-global-multiple-update-v3r4-batch-hard-judge-v3`.
- Bundle SHA-256: `d85176bbf1c871e58352198c73e4ed53adb7c2dd684073cc305c7bde072c2c92`.

Those identifiers concern the underlying scientific source. The `mfmu_scheduler`
adapter was added separately in the source package and must not be represented as
part of the frozen scientific bundle. The exact original and imported bytes are
recorded per file in
[`SOURCE_MANIFEST.json`](../../src/uav_scheduling/SOURCE_MANIFEST.json), along with
source notice/provenance hashes and each packaging transformation.

## Packaging changes

The import includes the global controller, pair-aware readout, resource lottery,
complete-journey and battery-ledger layers, and PyTorch mean-field engine.

1. Internal absolute imports now resolve under `uav_scheduling._vendor`.
   Relative imports remain relative. No top-level `src`, `experiments`, or
   `bounded_studies` package aliases are installed and no import search path is
   mutated.
2. Historical standalone self-tests, `__main__` guards and the old plotting helper
   were removed. Their source line ranges and removed-content hashes are recorded
   in the manifest. The duplicate private CLI is excluded; the public integration
   provides its own entry point. No private experiment fixture is required.
3. The unused `CNNJacobiSolver.theta_c` property depended on a calibration module
   absent from the source package. It now explicitly raises `NotImplementedError`.
   The supported NVMF path already uses `theta_c_scalar_multi` with explicit
   `theta0` and `theta_min`; that computation is unchanged.
4. The new `_vendor/__init__.py` only marks the private package.

No active scheduling expression, hard constraint, random-number namespace,
selection rule, guidance qualification threshold, battery rule or closure
condition was changed. This integration does not include later workstation
optimisation candidates. The historical folders named `experiments` and
`bounded_studies` contain runtime code retained for provenance; experiment datasets,
run outputs, environments and repository histories are not included.

## Dependency and evidence limits

The portable backend requires NumPy; the numerical mean-field backend additionally
requires PyTorch. Scenario data and output locations are explicit inputs to the
public interface. No runtime dependency on the old IRP directory or a workstation
is installed.

The portable uniform-field backend exercises scheduling integration and hard
validation; it does not execute the numerical NVMF solver. Running the numerical
backend does not by itself demonstrate that qualified guidance was consumed or
improved scheduling. Preserve those distinctions in results. This is an offline
experimental scheduling model, not a flight controller or a collision-avoidance
system.
