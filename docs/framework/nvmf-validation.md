# NVMF integration validation

Checked on 8 October 2026 against upstream commit
`d0cd5915b475b788e30765db42eeee8988161920`.
Environment: macOS arm64, Python 3.12.13, NumPy 2.4.6 and PyTorch 2.12.0;
CPU execution with one PyTorch thread and seed 0.

## Results

- The supplied four-request example ran the actual `mean_field` backend:
  four accepted, zero rejected, zero hard violations, global closure, independent
  journey replay and dry-run/commit agreement all passed. It took two Outer rounds.
- The example recorded one qualified mean-field draw and three uniform draws.
  This is a diagnostic for this synthetic input, not a comparison showing a
  mean-field benefit, numerical fixed-point convergence, or a Shanghai result.
- Running the same input and settings through the original integration core gave
  identical assignments, journeys, validation results and guidance counts.
  This checks this input only; it does not establish full scientific port parity.
- All 17 scheduler tests passed, including real CPU mean-field, invalid inputs,
  output preservation, guidance qualification/abstention, protocol assets,
  canonical scene aliases and retaining two successive CLI runs.
- The complete framework Python suite passed before the last two exporter
  regression tests were added: 70 tests, with four existing optional-dependency
  tests skipped. The final scheduler-only run includes those two additional tests.
- All 14 JavaScript viewer/model-source/random-UAV tests passed. Protocol 1.0
  and 1.1 examples validated. No viewer code was changed.

## Installed-package independence

A wheel was built and installed without editable mode. The example inputs were
copied into a separate temporary workspace. Python isolated mode loaded the
scheduler from `site-packages`, while a Python audit hook prohibited file opens
under both the original scheduler folder and this source checkout. The numerical
CLI run, result export and protocol validation succeeded. The import search path
was unchanged and no generic top-level package aliases were installed.

The framework's `tools/check_installed.py` also passed: installed schemas,
recoverable source ownership, static viewer resources and an empty-workspace
catalogue were usable without an editable checkout.

Reproduce the behavioural checks with:

```sh
NVMF_RUN_MEAN_FIELD_TESTS=1 python -m unittest discover -s tests -p 'test_nvmf*.py' -v
python -m unittest discover -s tests -v
node --test tests/test_viewer.mjs tests/test_model_source.mjs tests/test_random_uav.mjs
```

CUDA, large-city experiments, live 3D scene alignment and browser interaction were
not tested in this integration. The new GitHub CPU job is provided but its hosted
result must be checked separately. No workstation optimisation candidate is
claimed to be included; see [source provenance](nvmf-source.md).
