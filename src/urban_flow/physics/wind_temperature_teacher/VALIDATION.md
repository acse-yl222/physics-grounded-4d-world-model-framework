# Local validation record

Engineering checks performed on 2026-09-10:

- `python code/test_transfer.py`: **16 tests passed** on CPU.
- Actual Yi Qi one-step checkpoint: strict state-dictionary loading passed.
- Exported temperature model tensors: exact equality with the original checkpoint.
- Adapter's 15 input channels: matched the original Yi Qi dataset implementation.
- NN4PDEs derivative stencils: coordinate-ramp tests verified the (-u, v, w)
  conversion into increasing array-index coordinates.
- A small artificial CPU case exercised the physical temperature solver, actual
  temperature U-Net, saving, metrics, and plotting. Its data and figures are not
  included as scientific results.
- Tests cover interpolation, solid/roof coarsening, boundary direction, bounded
  heat transport, tile coverage, restart guards, minimal ZIP extraction, and the
  absence of future-temperature leakage into recursive forecasts.
- Vendored SCALED autoencoder and wind U-Net imports passed.
- Notebook schema validation and code-cell syntax checks passed.
- Final archive CRC and file checksum verification passed.

No full real-data 1024-domain CUDA wind-to-temperature experiment has been run
locally. GPU memory requirements, real execution time and transfer accuracy are
not yet established. These tests do not replace that experiment.
