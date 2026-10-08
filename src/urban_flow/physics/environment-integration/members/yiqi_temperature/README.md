# Yi Qi - Temperature

> DIGIT wind generation was removed at user request. The DIGIT setup and generation instructions below are historical and no longer executable. Shared geometry helpers remain for temperature code. Existing temperature surrogate weights and numerical solvers are retained; supply external wind inputs for new temperature runs.

This folder contains the temperature-modelling workflow for the environment integration project. The code builds a high-resolution South Kensington urban temperature pipeline from four linked parts:

- `models/velocity_calculation/`: prepares South Kensington geometry and generates 3D velocity fields with the DIGIT velocity surrogate.
- `models/physical_model/`: runs the physics-based 3D temperature model and can generate the 48-case supervised dataset.
- `models/surrogate_modelling/`: defines, trains, and evaluates the one-step 3D U-Net temperature surrogate.
- `models/rollout_surrogate/`: fine-tunes the one-step surrogate for autoregressive rollout prediction.
- `models/additional_test/`: contains held-out and transfer-test notebooks for changed geometry or source distributions.

Generated figures, cached arrays, local virtual environments, notebook outputs, and nested Git history are intentionally excluded from this integration folder. Model checkpoint parameter files needed for direct reuse are retained.

## Environment

Use Python 3.10+ with PyTorch. From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For GPU or HPC runs, install the PyTorch build that matches the CUDA environment before running the training notebooks or scripts.

## Data and Checkpoints

The workflow keeps model parameter files required for direct inference or fine-tuning:

- DIGIT velocity checkpoint: `models/velocity_calculation/assets/digit.pth`
- One-step temperature surrogate checkpoint: `models/surrogate_modelling/output/temperature/best_temperature_3d_unet_surrogate.pt`
- Rollout temperature surrogate checkpoint: `models/rollout_surrogate/outputs/best_temperature_3d_unet_surrogate_rollout.pt`

Large generated arrays, animations, figures, and intermediate outputs are still excluded. Recreate them by running the notebooks and scripts below.

## Suggested Run Order

Run commands from `members/yiqi_temperature/` unless noted otherwise.

1. Prepare geometry and smoke-test the velocity workflow.

```bash
cd models/velocity_calculation
python run_smoke_test.py
```

For full South Kensington velocity generation, use:

```bash
jupyter lab Run_South_Kensington_Velocity.ipynb
```

2. Generate physics-based 3D temperature labels.

Use the notebook:

```bash
jupyter lab models/physical_model/Generate_Temperature_3D_Surrogate_Dataset_48.ipynb
```

or call the dataset generator from Python:

```python
from pathlib import Path
from models.physical_model.generate_temperature_3d_surrogate_dataset import generate_temperature_3d_surrogate_dataset

generate_temperature_3d_surrogate_dataset(
    Path("outputs") / "temperature_3d_surrogate_dataset_48"
)
```

The default dataset combines 4 geometry rotations, 3 velocity cases, and 4 thermal cases for 48 total cases. The thermal cases cover mild, baseline, hot sunny, and very hot urban conditions.

3. Train the one-step 3D U-Net surrogate.

```bash
jupyter lab models/surrogate_modelling/Train_Temperature_3D_UNet_Surrogate.ipynb
```

Key default settings:

- history window: 3 temperature frames
- patch size: `(8, 32, 32)` in `(z, y, x)`
- base channels: 12
- depth: 3
- input channels: temperature history, velocity components, velocity speed, and static urban/thermal fields
- output: next-step 3D temperature field

4. Evaluate the one-step surrogate on virtual geometry.

```bash
jupyter lab models/surrogate_modelling/Test_Virtual_Geometry_3D_UNet_Surrogate.ipynb
```

5. Fine-tune the autoregressive rollout surrogate.

```bash
python models/rollout_surrogate/train_rollout_temperature_surrogate.py
```

Key default settings:

- starts from the one-step 3D U-Net checkpoint
- rollout steps: 10
- long validation rollout steps: 30
- patch sizes: `(8, 32, 32)` , `(24, 16, 16)` and `(16, 32, 32)`
- base channels: 12
- learning rate: `1e-5`
- drift-aware selection score using short and long validation rollouts

6. Evaluate rollout behaviour.

```bash
jupyter lab models/rollout_surrogate/Test_South_Kensington_Rollout_Finetuned.ipynb
jupyter lab models/rollout_surrogate/Test_Virtual_Geometry_Rollout_Finetuned.ipynb
```

7. Run additional transfer tests if needed.

```bash
jupyter lab models/additional_test/Test_Teacher_Source_Distributions_Virtual_Geometry.ipynb
jupyter lab models/additional_test/Test_South_Kensington_Teacher_Source.ipynb
```

## Model Notes

### DIGIT Velocity Surrogate

The velocity stage creates 3D urban flow inputs for the temperature model. It uses South Kensington geometry, configurable model resolution, inlet flow, geometry rotation, and selected time levels. Outputs include velocity components `u`, `v`, `w`, solid masks, roof masks, height fields, and study-area masks.

### Physics-Based 3D Temperature Model

The physical model generates supervised labels using velocity fields, surface exchange, shade, radiation, ambient temperature, inflow temperature, cloud cover, and anthropogenic heat flux. The dataset generator caches velocity per geometry and inlet-flow pair, then reuses it across thermal scenarios.

### One-Step 3D U-Net Temperature Surrogate

The one-step surrogate learns `T[t-history+1:t] -> T[t+1]` on cropped 3D patches. Inputs combine recent temperature history, velocity fields, velocity speed, geometry masks, surface fields, and time-varying thermal context. Losses are masked over valid fluid cells.

### Rollout Surrogate

The rollout model fine-tunes the one-step U-Net for repeated autoregressive prediction. It can use next-step velocity channels, an implicit future-temperature guess, cool-surface channels, gradient loss, multiscale loss, and drift-bias penalties to improve long-horizon stability.

## Repository Hygiene

Keep generated outputs under local `outputs/` folders and avoid committing:

- `.venv/`, `.vendor/`, `__pycache__/`, `.pytest_cache/`
- generated `.npy`, `.npz`, `.gif`, and large `.png` files
- notebook cell outputs
- local caches and OS metadata files
