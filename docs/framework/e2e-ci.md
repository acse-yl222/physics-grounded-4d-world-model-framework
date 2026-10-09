# Short E2E checks

`E2E smoke` replaces the former `Synthetic viewer` CI job. The Python matrix,
CPU domain checks, and format/JavaScript checks are retained: six jobs in total.
Every pull request runs the workflow, including stacked PRs. Pushes to `main`
and manual runs also trigger it. There is no path filter or conditional skip
on the E2E job.

## Run locally

Use Python 3.11 and the Node.js version in `.nvmrc`:

```sh
python -m pip install -e '.[geometry]'
npm ci
make test-e2e PYTHON=python
```

`CHROME_PATH` can select an existing Chromium executable. Otherwise the runner
uses Puppeteer's installed browser. No GPU, model weights, private scene data,
or external dataset download is needed. During the checks, the browser reads
assets only from the local CLI server.

## What must pass

- A generated 8 × 8 m GLB roof goes through the real CLI geometry and visualize
  stages, protocol export, retention and scene/view registration. Both stages
  must finish; an exit-zero command that skips a stage is a failure.
- Metadata, retained data and scratch output use separate temporary directories.
  The rasterized footprint and height match the input. Duplicate retention must
  fail without changing the retained run or view. After scratch deletion, the
  retained manifest must still validate and load in the browser.
- The original five JSON layer tests check picking, interpolation, visibility,
  time bounds and disposal through the actual framework server.
- The registered GLB view supports picking at the known roof height and layer
  toggles. The view selector opens a second retained view with full and per-frame
  NPY data. HTTP 206 reads, midpoint values, terrain heights, missing-value masks,
  time bounds and disposal must match the source arrays. Float comparisons use
  a tolerance of `1e-6`.

The runner saves its pass/failure summary, CLI/server logs, browser report and
screenshots in `cache/framework/e2e/`. CI uploads these even when a check fails,
with seven-day retention. The job timeout is five minutes. Dependency installation
is included in CI time; local smoke execution is typically a few seconds.

These checks protect framework integration. They do not certify the numerical
correctness of every solver or replace CUDA, training, SUMO or real-city tests.

## Make it a required merge check

Once the job has passed on GitHub, a repository administrator must configure a
rule for `main` requiring pull requests and the `E2E smoke` status check from
GitHub Actions. Require branches to be up to date before merging and apply the
rule to bypass-capable administrators if every change must pass it.

Adding workflow YAML alone does not enforce this rule. Do not enable path filters,
`continue-on-error`, or conditional skips for the required check. If a merge queue
is introduced, also add the `merge_group` trigger before using the queue.
