# Local reproduction: wind → pollution, 5000–6000

Keep `run_local.py` beside the existing `wind_pollution_reproduction_bundle.zip`
and `SHA256SUMS.txt`. **Do not rebuild the data ZIP.** The Colab notebook remains
an optional alternative; it is not required for the commands below.

## Download the weights and data

Open the [shared Google Drive folder](https://drive.google.com/drive/folders/166itkp91W-gNv2L8Qw7hELTU0olf8PCL?usp=drive_link)
and download `wind_pollution_reproduction_bundle.zip` plus `SHA256SUMS.txt`.
Place both files beside `run_local.py`. Download the data ZIP itself; an outer ZIP
created by downloading the entire Drive folder must first be unpacked.
If Drive asks for access, contact the sender. The local runner does not require
a GitHub token or any Google account credentials after these files are downloaded.

This entry point runs the exact numerical workflow from the verified bundle.
It does not access Google Drive, authenticate to GitHub, retrain models, or
regenerate the physical spin-up. It starts from the supplied wind and C at 5000
and predicts 20 updates, producing 21 concentration states through 6000.

## Requirements

- A local workstation or server with an NVIDIA GPU and CUDA-enabled PyTorch.
  The original run used A100. Smaller GPUs are **not** guaranteed to fit the
  full-volume pollution U-Net; the runner never silently switches to tiled mode.
- Python 3.10 or newer compatible with the bundled pinned packages; prefer the
  packaging-session Python version printed by `prepare`. Use a clean environment.
- Adequate system RAM and disk: retain the ZIP, its extracted contents, another
  copy of input/reference files, and new prediction/checkpoint files. Disk space
  is checked before extraction and inference. Actual GPU memory demand is tested
  by inference, not inferred from the GPU name.
- Internet for initial Python package installation only. Once dependencies and
  the bundle are present, inference itself does not need network access.

CPU or Mac users can run `prepare` and inspect files, but this entry point does
not implement full CPU/MPS inference. `plot` can run without a GPU **after local
predictions exist**; the supplied ZIP does not include all original prediction volumes.

## Run from a terminal

Open a terminal in the shared/downloaded folder. On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python run_local.py prepare
```

On Windows, create the environment with `python -m venv .venv`, then use
`.venv\Scripts\activate.bat` in Command Prompt (or your usual environment manager).
The remaining `python` commands are the same.

Install a CUDA-enabled PyTorch build appropriate for the operating system and
NVIDIA driver using the [official PyTorch installation selector](https://pytorch.org/get-started/locally/).
The CUDA wheel choice is machine-specific, so no single CUDA installation command
is assumed here. If matching a particular older PyTorch version, use the official
[previous-version instructions](https://pytorch.org/get-started/previous-versions/).

Then run:

```bash
python -m pip install -r wind_pollution_reproduction_bundle/requirements.txt
python run_local.py check
python run_local.py run
```

`prepare` verifies and extracts the ZIP using only the standard library. It can
reuse an already verified extraction, but never overwrites an unknown non-empty
folder. If extraction was interrupted, choose a new `--bundle` folder or manually
manage the incomplete folder after checking its contents.

`check` validates all file hashes, dependencies and CUDA availability. It does
not claim that the model fits GPU memory. `run` loads the exact bundled weights,
copies immutable inputs/reference fields, and runs full-volume inference.
The original reference fields are used only for evaluation, never as future
inputs to the models. No alternative model or synthetic data are substituted.

## Paths, outputs and restart

Defaults are relative to the location of `run_local.py`, not the author's computer:

```text
wind_pollution_reproduction_bundle.zip   original shared ZIP
wind_pollution_reproduction_bundle/      verified extracted inputs/code/weights
local_results/                          new run inputs, checkpoints and results
```

Use explicit paths when needed:

```bash
python run_local.py prepare --archive /data/bundle.zip --bundle /data/bundle
python -m pip install -r /data/bundle/requirements.txt
python run_local.py run --bundle /data/bundle --output /data/my_run
```

If interrupted, rerun the same `run` command with the same environment and output
directory. Completed checkpoints are reused. A changed bundle, GPU/software
environment or numerical settings requires a **new output directory**; previous
results are preserved. If GPU memory is insufficient, the program reports the
error and stops; it does not quietly change the method.

Outputs include:

- `local_results/coupled/state_005000.h5` through `state_006000.h5` at intervals of 50;
- `local_results/coupled/metrics.csv` and restart state;
- `local_results/pollution_comparison.png` and `rmse_comparison.png`;
- `local_results/recorded_run_comparison.csv`, comparing summary metrics with the author;
- `local_results/local_environment.json`, recording this local run's environment.

To redraw figures without rerunning inference:

```bash
python run_local.py plot
```

## Interpretation and reproducibility limits

The current coupled rollout progressively underpredicts concentration. Reproducing
that result is not evidence that it is accurate. Compare with the physical
reference and the persistence baseline. Concentration has no verified PM2.5
mass-unit conversion; the time labels are indices, not an asserted 90-second interval.
Equality with Yuhang's historical training geometry and VAE remains unverified.

The exact source and file contents are checked. Some bundles were made after a
Colab disconnect: their recorded package versions/numerical flags describe the
new packaging session, **not a verified record of the original inference session**.
The local runner reports differences and records its own environment. Bitwise
agreement across GPU/library versions is not guaranteed.

Use only trusted code and model checkpoints. The bundle's existing licences and
group sharing permissions remain applicable. The local runner has been checked
with CPU-side packaging/validation tests; full-domain GPU reproduction on the
recipient's machine still needs to be performed.
