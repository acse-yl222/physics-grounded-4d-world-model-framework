# FieldFleet / NVMF scheduler

This branch adds the runnable scheduling core under `src/uav_scheduling/`.
It includes the PyTorch mean-field Inner, global multiple-update Outer,
collection/drop-off pairing, full journey and battery checks, qualification and
fallback policy, and independent replay. It does not require another IRP checkout,
private experiment fixtures, scene geometry or a running workstation.

## Run the small example

Use Python 3.11+ in a fresh environment from the repository root:

```sh
python3 -m venv cache/framework/venv
source cache/framework/venv/bin/activate
python -m pip install -e '.[scheduler]'
nvmf-schedule examples/nvmf/minimal_scenario.json --device cpu
```

`mean_field` is the default and actually runs the numerical solver. Work and
results go into a new `cache/nvmf_demo/uav_scheduling/<run_id>/` directory, printed
by the command. The four-request CPU example takes seconds rather than a full
research campaign. `--threads` defaults to one for this small case. For an existing
CUDA-compatible PyTorch installation, select `--device cuda` explicitly; the
command rejects unavailable devices rather than silently falling back to CPU.

For a NumPy-only integration check, install the base framework and explicitly use
`--backend portable_fail_closed`. This exercises uniform proposals, Outer and
validation; it does **not** execute mean-field. Missing PyTorch on the normal
command is an error, not an automatic switch to the uniform test mode.

Use `--output <new-file.json>` for a chosen result location. Existing files and
work directories are not overwritten. A failed closure raises an error; partial
controller records remain in the printed work directory for diagnosis.

## Python API

```python
import json
from uav_scheduling import schedule

with open('examples/nvmf/minimal_scenario.json') as stream:
    scenario = json.load(stream)
result = schedule(scenario, backend='mean_field', device='cpu', run_seed=0)
print(result['assignments'])
print(result['journeys'])
print(result['validation'])
```

The wrapper validates types before passing input to the preserved core. It rejects
fractional/bool/string slot values, nonfinite numbers, malformed identifiers and
unsupported model settings. The private vendor namespace prevents collisions with
other modules named `src`, `experiments` or `bounded_studies`. Solver formulae and
decision rules are preserved; see [source provenance](nvmf-source.md).

### Input and output

The example is a complete small input contract, `mfmu.integration.v1`:

| Input | Meaning |
| --- | --- |
| `stations` | Unique string IDs, `x`/`y` coordinates, `hub` or `station` role |
| `travel_time_slots` | Nonnegative integer square matrix, zero diagonal |
| `distance_km` or `distance_cost` | One explicit nonnegative square cost matrix |
| `fleet` | Unique IDs and initial station IDs |
| `requests` | Unique IDs, collection/drop-off stations, collection slot, optional eligible UAVs and drop-off window |
| `horizon_slots` | Currently fixed at 240, plus row 0 for the initial fleet |
| `battery` | Optional explicit confirmation of the frozen proxy values below |

The homogeneous proxy is SoC 75, four energy units per flight slot, reserve zero,
and a two-slot swap restoring SoC to 75. Each drop-off window has five slots,
beginning at collection time plus collection-to-drop-off travel time. Station
endpoints and Hub swap service have non-binding capacity in this snapshot;
UAV-time occupancy remains exclusive. These are model assumptions, not general
physical battery or charging-station capabilities.

Results contain request-to-UAV assignments, discrete journey segments, service
slots, battery states, validation receipts, and separate qualified-guidance versus
uniform-fallback counts. A safe-Hub certificate indicates reachable replenishment;
it does not itself add an executed return flight. Closure need not be possible for
every scenario within `--max-rounds` (default 32).

## Optional framework result bundle

The solver itself needs no geographic origin or seconds-per-slot conversion.
To export a protocol 1.1 bundle, provide those explicitly:

```sh
nvmf-schedule examples/nvmf/minimal_scenario.json --device cpu \
  --context examples/nvmf/minimal_context.json
p4d validate <printed-protocol-manifest-path>
p4d retain <directory-containing-that-manifest>
```

The example uses synthetic local ENU metres, no geographic reference, and 60
seconds per slot. Its station coordinates are 0, 1000, 2000 and 3000 metres;
the costs and integer travel times are synthetic inputs. For real `south_ken` or
`white_city` integration, supply the actual scene spatial declaration and time
conversion. Never reuse this synthetic context as real city coordinates.

The bundle contains the exact input, output, parameters, context, hashes and a
recoverable module source snapshot. Its existing `time_series` layer records
cumulative deliveries at actual committed drop-off events. No new viewer is added.
The discrete scheduler does not generate obstacle-aware 3D paths, so this adapter
does not invent trajectory coordinates or claim a city flight visualisation.
Results are not automatically published or registered as a city's default view.

## Validation and interpretation

See the [integration validation record](nvmf-validation.md) for checks actually run.

```sh
python -m unittest discover -s tests -p 'test_nvmf*.py' -v
NVMF_RUN_MEAN_FIELD_TESTS=1 python -m unittest discover -s tests -p 'test_nvmf_scheduler.py' -v
```

The second command requires the scheduler extra and runs the real CPU solver.
The checks cover closure/replay, strict input rejection, overwrite protection,
qualification versus abstention, canonical ID ordering, and protocol export.

This is a portable integration of the frozen API lineage identified in
`SOURCE_MANIFEST.json`, not a claim that subsequent experimental or performance
branches have been incorporated. The historical Shanghai 10K campaign did not
consume qualified mean-field guidance. Its evidence does not transfer to this new
example; results preserve `port_parity_status=NOT_ESTABLISHED` and the custom-input
scope. Running the Inner does not by itself demonstrate a guidance benefit.

No global optimality, general convergence, real-time or flight-safety claim is
made. Third-party packages are installed through the declared dependencies, not
copied environments. The scheduler's [rights notice](../../src/uav_scheduling/NOTICE.md)
is retained; this integration does not assign it a new open-source licence.
