# Wind-to-temperature: a new-scene transfer experiment

This package connects Zhongkai's regression1024 wind model to Yi Qi's frozen
**one-step, 15-channel 3D temperature U-Net**. It runs in a standard Jupyter
environment on a CUDA server. It does not need Colab, a GitHub token, or access
to the author's private Google Drive account.

## Run

1. Extract this whole package and open `wind_temperature_cloud.ipynb` inside it.
   Keep the notebook, `code/`, and `weights/` together.
2. Use a CUDA-enabled PyTorch environment. The notebook can install the other
   Python dependencies, but will not replace the server's PyTorch installation.
3. Download `wind_pollution_reproduction_bundle.zip` from the
   [shared data folder](https://drive.google.com/drive/folders/166itkp91W-gNv2L8Qw7hELTU0olf8PCL?usp=drive_link)
   and put it beside the notebook, or change `DATA_ARCHIVE` to its local path.
   This is the previously shared large wind/pollution dataset, not this small
   temperature package. Anonymous access to the link has not been independently
   verified; if access is requested, contact Zhongkai.
4. Set `RUN_DIR` and `ASSET_DIR` to persistent server storage. Run the notebook
   from top to bottom. Read the scenario configuration before starting GPU work.

Only four assets are extracted from the large data ZIP: the wind checkpoint,
wind VAE checkpoint, geometry, and physical-unit initial wind `W_005000.h5`.
No pollution weights, concentration fields, or pollution reference frames are
needed. Already extracted files can instead be supplied through `ASSET_OVERRIDES`.
The actual temperature weights are included here as an inference-only checkpoint;
its model tensors and statistics match Yi Qi's original checkpoint exactly.

Use only trusted checkpoints. The original wind checkpoint is loaded with
PyTorch's legacy metadata support and must not be replaced by an untrusted file.
SHA256 checks detect damage or changes; they do not establish the trust of a sender.

## What the notebook does

- Forecast the full 1024 wind field using the original 25-patch/halo assembly.
- Restore physical wind units and average each 4x4x4 block. Use conservative
  solid occupancy on the coarser grid. The temperature domain is [16,256,256]
  in [z,y,x], covering the original approximately 64x1024x1024 m extent.
- Convert wind components to the scalar solver's increasing-index convention:
  `(u,v,w)=(-raw_u,raw_v,raw_w)`. This is based on the signs of the actual NN4PDEs
  derivative stencils (tested on linear coordinate ramps), not an assumed match
  to another team member. The recurrent wind model retains its original convention.
- Define a new, constant thermal scenario: ambient 26 C, ground 30 C, roof 30 C,
  surface exchange 0.001 /s, and diffusivity 1 m^2/s. These are chosen experiment
  settings, not measurements. No original land-cover or solar reconstruction is claimed.
- Generate three initial temperature frames at -180, -90, and 0 s using a fixed
  initial wind during warmup. These are generated initial conditions, not observed
  historical temperatures and not a claim of thermal equilibrium.
- Predict five 90-second temperature increments, up to +450 s. This uses 18 wind
  forecasts of 50 CFD steps. Time adopts the explicit experimental SI interpretation
  of wind dt=0.5 and grid spacing=1: 50 wind steps =25 s, NOT 90 s. The initial wind
  index 5000 is defined as the experiment's relative time zero.
- Linearly interpolate predicted wind to each temperature input time; hold that
  frame's wind constant inside the 90-second physical integration interval, matching
  the one-step temperature conditioning convention.
- Compare recursive temperature forecasts, one-step forecasts given physical
  history, and persistence against a controlled heat solver with the SAME predicted
  wind. Only the one-step diagnostic uses future physical histories. The recursive
  branch uses just the common initial three frames and its own outputs.
- Save fluid-only MAE, RMSE, bias, ranges, 3D arrays, and plots with shared colour scales.

## Important interpretation

This is a **new-scene transfer test**, not a reproduction of Yi Qi's original
South Kensington experiment. The new domain has a lower physical top, different
geometry/forcing and different wind statistics. The model may perform poorly.
Conservative coarsening can close narrow streets and is not a divergence-preserving
velocity remap. Check the geometry preview before continuing.

The reference solver is adapted from Yi Qi's temperature-equation structure:
first-order upwind advection, central diffusion and ground heat exchange.
It has sign-aware lateral inflow/outflow, a combined stability limit, an ambient
top boundary, prescribed solid/roof temperatures and zero-gradient bottom stencil.
It is NOT an unchanged copy of Yi Qi's original physical pipeline, NOT NN4PDEs,
NOT CFD ground truth, and NOT evidence that the wind prediction is accurate.
Using the same forecast wind isolates temperature-surrogate transfer error;
wind-model accuracy needs a separate comparison with CFD-driven temperature.

Temperature inference uses the training patch size [8,32,32], overlap [4,8,8]
and arithmetic overlap averaging. GroupNorm makes this different from a single
full-volume forward pass. Predictions are not clipped or boundary-corrected to
hide errors; non-finite outputs stop the run. Solid cells are excluded from metrics.

## Restart and outputs

Reopen the notebook and rerun the cells with the same configuration and `RUN_DIR`.
Each wind update stores the full current state and random-generator states;
temperature stages save every completed frame. A partial step is rerun, not used
as a completed result. Changing assets, settings, code, or recorded environment
requires a new run directory. Keep the persistent disk after stopping the instance.

Outputs are under `RUN_DIR`: `manifest.json`, `geometry_preview.png`, `wind/`,
`temperature/metrics.json`, full temperature `.npy` arrays and `figures/`.
The complete forecast wind cache is coarse; only the latest full wind state is
kept for restart. Allow several GB beyond the downloaded archive and extracted
weights for checkpoints and outputs. The wind model is much larger than the
temperature model. Exact CUDA memory requirements have not yet been measured
for this new package; a small GPU may fail during wind inference.

## Validation status and provenance

This package has local CPU tests for the actual temperature weight loading,
15-channel interface, thermal solver, interpolation, geometry reduction, tiling,
data extraction, and restart guards. It has NOT completed the full real-data
CUDA wind-to-temperature experiment. Notebook outputs are intentionally empty.
Do not present the small synthetic unit tests as scientific results.
Run the tests with `python code/test_transfer.py` after installing dependencies.

`code/SOURCE_INFO.json` records source hashes, the pinned SCALED revision, and
the original temperature checkpoint hash. The temperature architecture is copied
unchanged from Yi Qi's source; the wind inference functions are copied unchanged
from the existing integration. Their original sources are included for review.
SCALED's bundled licence remains applicable. Team-member code/weights are supplied
for the requested academic collaboration, not as a new public licence grant.

No code is pushed to the shared main branch by building or running this package.
