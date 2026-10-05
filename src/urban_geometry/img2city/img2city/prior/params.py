"""img2city/prior/params.py -- fixed-length parameterisation of a building: the bridge between a
LEARNED image->parameters model and the procedural library (components.build_building).

A building is encoded as a fixed vector of N_PARAMS numbers (PARAM_RANGES). The model
regresses these from an image; vec_to_desc() turns a vector into a build_building
description. sample_vec() draws a random building (for synthetic training data);
normalize/denormalize map raw values <-> [0,1] for the regressor.

This is the data prior the agent currently lacks: instead of the LLM eyeballing
dimensions, a small net trained on synthetic renders predicts the editable parameters
directly -- Tripo-style learned prior, but on a PARAMETRIC (editable) representation.
"""
import random

FLOOR_H = 4.3

# (name, low, high, is_int)
PARAM_RANGES = [
    ("L",            60.0, 120.0, False),  # footprint long edge (X)
    ("W",            24.0,  44.0, False),  # footprint short edge (Y)
    ("tall_floors",   4.0,   8.0, True),   # tall glazed block height
    ("tall_split",   0.25,  0.45, False),  # tall block occupies x in [0, tall_split]
    ("wing_floors",   2.0,   5.0, True),   # lower wing height
    ("frame_over",    1.0,   5.0, False),  # exoskeleton above roof
    ("vault_radius",  4.0,   9.0, False),
    ("vault_span",   0.20,  0.40, False),
    ("saw_f0",       0.35,  0.50, False),  # sawtooth start (fraction of length)
    ("saw_f1",       0.80,  0.95, False),  # sawtooth end
    ("saw_count",     6.0,  14.0, True),
    ("green_a0",     0.50,  0.70, False),  # green volume along-fraction start
    ("green_a1",     0.72,  0.90, False),
    ("green_hf",     0.50,  0.90, False),  # green volume height fraction
    ("green_depth",   3.0,   6.0, False),
    ("ent_a0",       0.35,  0.50, False),  # entrance along-fraction
    ("ent_a1",       0.52,  0.65, False),
]
NAMES = [r[0] for r in PARAM_RANGES]
N_PARAMS = len(PARAM_RANGES)


def sample_vec(rng=random):
    return [rng.uniform(lo, hi) for (_, lo, hi, _) in PARAM_RANGES]


def normalize(vec):
    return [(v - lo) / (hi - lo) for v, (_, lo, hi, _) in zip(vec, PARAM_RANGES)]


def denormalize(nvec):
    out = []
    for u, (_, lo, hi, isint) in zip(nvec, PARAM_RANGES):
        u = max(0.0, min(1.0, float(u)))
        v = lo + u * (hi - lo)
        out.append(int(round(v)) if isint else v)
    return out


def vec_to_desc(vec):
    """Fixed parameter vector -> a build_building description (editable + valid)."""
    d = dict(zip(NAMES, vec))
    tf = int(round(d["tall_floors"]))
    wf = int(round(d["wing_floors"]))
    split = round(float(d["tall_split"]), 3)
    return {
        "footprint": [round(float(d["L"]), 1), round(float(d["W"]), 1)], "floor_h": FLOOR_H,
        "masses": [
            {"x": [0.0, split], "y": [0, 1], "floors": tf, "facade": "glass"},
            {"x": [split, 1.0], "y": [0, 1], "floors": wf, "facade": "glass"},
        ],
        "frame": {"x": [max(0.0, split - 0.02), 1.0], "y": [0, 1],
                  "over": round(float(d["frame_over"]), 2), "height": tf * FLOOR_H, "bays": 9},
        "roof": [
            {"type": "vault", "end": "-x", "span_frac": round(float(d["vault_span"]), 3),
             "radius": round(float(d["vault_radius"]), 2)},
            {"type": "sawtooth", "frac": [round(float(d["saw_f0"]), 3), round(float(d["saw_f1"]), 3)],
             "count": int(round(d["saw_count"]))},
            {"type": "plant", "boxes": [[round(float(d["L"]) * 0.1, 1), 4, 3, 14, 9]]},
        ],
        "volumes": [{"type": "green_glass", "side": "-y",
                     "along": [round(float(d["green_a0"]), 3), round(float(d["green_a1"]), 3)],
                     "height_frac": round(float(d["green_hf"]), 3),
                     "depth": round(float(d["green_depth"]), 2)}],
        "entrance": {"side": "-y",
                     "along": [round(float(d["ent_a0"]), 3), round(float(d["ent_a1"]), 3)]},
    }
