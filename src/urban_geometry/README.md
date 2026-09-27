# Urban World Model — Integration Runner

Runs the bird flock simulation and the MFMU UAV scheduler side by side on shared city geometry, producing combined outputs for downstream visualisation or analysis.

Both repos are kept untouched. `integrate.py` sits at the project root and orchestrates everything via subprocess.

## Layout

```
uwm-group1/
├── geometry/                              shared inputs
│   ├── birds_scene.glb                    GLB for bird voxelisation
│   ├── stations.csv                       station positions and roles
│   └── requests.json                      (optional) MFMU delivery requests
├── birds/                                 bird flock simulation
├── mfmu-uwm-integration-preview/         MFMU UAV scheduler
├── traffic/                               traffic prediction model
├── integrate.py                           glue script
└── outputs/                               created on first run
    ├── manifest.json                      links all outputs with checksums
    ├── birds/sim_result.npz               bird trajectories
    ├── mfmu/
    │   ├── scenario.json                  scenario fed to the scheduler
    │   └── schedule_result.json           scheduler output
    └── traffic/
        ├── eval_output.txt                evaluation metrics (ADE, FDE)
        ├── best_model_<date>.pt           model weights (copy)
        └── eval_log_<date>.txt            evaluation log
```

## Setup

**One-time steps:**

1. Place the shared GLB and `stations.csv` in `geometry/`.

2. Install bird sim dependencies (from `birds/`):
   ```bash
   pip install -r birds/requirements.txt
   ```

3. Install the MFMU scheduler:
   ```bash
   cd mfmu-uwm-integration-preview
   pip install -e .
   cd ..
   ```

4. Install traffic model dependencies:
```bash
   cd traffic && pip install -r requirements.txt && cd ..
```

5. Train a traffic model (one-time, ~250 epochs, skip if you already have one):
```bash
   cd traffic && python train.py && cd ..
```

## Usage

```bash
# full run: voxelise GLB, run birds, run MFMU
python integrate.py

# skip voxelisation if the geometry hasn't changed
python integrate.py --skip-voxelise

# skip certain models
python integrate.py --skip-mfmu
python integrate.py --skip-birds
python integrate.py --skip-traffic

# use a real delivery-request file instead of synthetic ones
python integrate.py --requests geometry/real_requests.json

# use a specific trained model
python integrate.py --traffic-model 08-16_07-31-30

# train + evaluate in one go (slow)
python integrate.py --train-traffic

# write outputs somewhere else
python integrate.py --output my_run_01
```

Without `--requests`, the script generates synthetic COLLECTION→DROPOFF delivery requests spread across the time horizon. These exercise the scheduler but aren't meaningful scenarios — swap in a real file for that.

## Outputs

`outputs/manifest.json` ties everything together:

```json
{
  "created": "2026-09-06T15:36:13Z",
  "integrator": "integrate.py",
  "models": {
    "birds":   { "output_file": "birds/sim_result.npz", "sha256": "...", ... },
    "mfmu":    { "output_file": "mfmu/schedule_result.json", "sha256": "...", ... },
    "traffic": { "output_file": "traffic/eval_output.txt", "sha256": "...", ... }
  }
}
```

**Bird sim** (`sim_result.npz`) contains frame-by-frame positions, velocities, behavioural states, energy, and affect for every bird. Load with `np.load('outputs/birds/sim_result.npz', allow_pickle=True)`.

**MFMU scheduler** (`schedule_result.json`) contains per-request UAV assignments, complete journey segments with timing and battery state, and validation results. The scenario that was fed to the scheduler is saved alongside it for inspection.

**Traffic model** (`eval_output.txt`) contains evaluation metrics (ADE, FDE) printed by `evaluate.py`. A copy of the model weights and evaluation log are saved alongside for provenance.

## Configuration

All tuneable constants live at the top of `integrate.py`:

| Constant | What it controls |
|---|---|
| `BIRDS_GLB` | Path to the GLB used for bird voxelisation |
| `STATIONS_CSV` | Path to station positions and roles |
| `MFMU_SPEED_MPS` | UAV cruise speed (m/s), used to compute travel times |
| `MFMU_SLOT_DT_S` | Duration of one scheduler time slot (seconds) |
| `MFMU_HORIZON` | Total scheduler time slots |
| `MFMU_N_UAV` | Number of UAVs |
| `COORD_OFFSET_X/Y` | Translation if station and bird coordinates don't align |

## Adding another model

To plug in a fourth simulation (pedestrians, noise, etc.):

1. Add a `run_<model>(output_path)` function that calls it via subprocess.
2. Add an entry to `parts` in `main()` with its output path and config summary.
3. It will appear in `manifest.json` automatically.

## Known assumptions

- Bird sim and station coordinates are assumed to be in the same metre-scale frame. If they aren't, adjust `COORD_OFFSET_X/Y`.
- The MFMU battery model is frozen at the validated values (max SoC 75, 4 energy per flight slot, 2-slot swap). These are hardcoded to match the scheduler's validation contract.
- Synthetic requests pair every COLLECTION station with every DROPOFF station once. For the default city_sk geometry (3 collection × 6 dropoff) this produces 18 requests.
- The traffic model generates road networks procedurally (hardcoded centerlines in `generate_complex.py`) and does not consume the shared city geometry. Its 56×56 grid (168m × 168m at 3m/cell) is independent of the bird/UAV coordinate frame. The London verification pipeline (`traffic/verification/`) reads `roads.geojson` for real-world validation but is not wired into this integration.