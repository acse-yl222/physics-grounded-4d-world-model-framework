# Learned prior — image → editable building parameters (`img2city.prior`)

Defaults for dataset / weights live under `data/prior/` (`IMG2CITY_PRIOR_DIR`).

Adds a small, MSc-feasible **data prior** to the agent: a network that predicts a
building's editable **parameters** from a single image — Tripo-style learned prior, but
on a **parametric / editable** representation instead of a dead mesh. It's trained on
synthetic renders from the component library, so labels are free and exact.

This closes the gap the agent had: instead of the LLM *eyeballing* dimensions from the
photo, a net trained on thousands of examples predicts the parameters directly. The
agent's render→critique→refine loop then polishes, and the output stays fully editable.

## Pipeline (3 steps)

**1. Generate synthetic data** (on the Mac, with Blender + the BlenderMCP server open):

```
python -m img2city.prior.gen_dataset --n 3000 --out data/prior/dataset
```

→ `data/prior/dataset/*.png` + `labels.csv`. ~1 hr for 3000 samples. Lighting / exposure /
camera / background are randomised so the net transfers to a real model photo (modelpic).

**2. Train the image→params regressor** (Mac MPS, Colab GPU, or CPU):

```
pip install torch torchvision pillow
python -m img2city.prior.train --data data/prior/dataset --epochs 40 --out data/prior/param_model.pt
```

ResNet18 (ImageNet-pretrained) → `N_PARAMS` normalised outputs. Trains in well under an
hour on one GPU / Apple-Silicon MPS for a few thousand 320 px images.

**3. Predict for modelpic, then run the agent seeded from it:**

```
python -m img2city.prior.predict --image data/business_school/modelpic.jpeg --out data/prior/pred_desc.json
python -m img2city.building.generate --data data/business_school --ref modelpic.jpeg --view aerial \
        --mode assemble --init-desc data/prior/pred_desc.json
```

`--init-desc` makes the agent start iteration 0 from the model's prediction (no LLM guess);
the rubric critic + LLM then refine from there.

## Files

| file | role |
|------|------|
| `params.py` | fixed parameter vector ↔ `build_building` description (the editable model) |
| `gen_dataset.py` | `build_building(random params)` → render → `(image, params)` pairs |
| `train.py` | ResNet18 → `N_PARAMS` (normalised), SmoothL1, saves weights + ranges |
| `predict.py` | image → params → description JSON |
| `generate.py --init-desc` | seeds the agent's iteration 0 from the model |

## Notes

- **Why this is the right "training" to add:** it's the missing *data prior*. Tripo's
  quality comes from training on millions of 3D shapes; you can't (and needn't) replicate
  that. A small net predicting ~17 editable parameters, trained on free synthetic renders,
  gives the same *kind* of learned prior at a scale one person can actually train.
- **Sim-to-real:** training images are domain-randomised so the net generalises from
  synthetic Blender renders to modelpic. If predictions are off, generate more data or
  widen the randomisation in `gen_dataset.py`.
- **Editable, always:** the model only predicts parameters — the geometry is still built
  by the parametric library, so floors/massing/features remain editable.
- **More building types:** add archetypes to `params.py` (and the templates) and
  regenerate data to cover families beyond the tall-block-plus-wing.
