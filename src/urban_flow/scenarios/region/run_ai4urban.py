"""Run the user-supplied AI4Urban stencil solver on region's actual 8 m solid grid.

The reference is loaded through AST: no original data load, large allocation, or
time loop is executed. Equations/stencils are retained; geometry and I/O adapted.
"""

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import time

import h5py
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

REFERENCE = Path(__file__).with_name("AI4Urban_reference.py")


def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False))
    tmp.replace(path)


def build_model(solid, cell, device, dt=0.5, ub=-1.0, re=0.15):
    nz, ny, nx = solid.shape
    assert nz >= 4 and nz & (nz - 1) == 0 and nx % nz == ny % nz == 0
    source = REFERENCE.read_text()
    tree = ast.parse(source)
    # Stencil block begins with bias_initializer and ends before ntime.
    selected, active = [], False
    for node in tree.body:
        names = [t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)]
        if "bias_initializer" in names:
            active = True
        if "ntime" in names:
            active = False
        if active or isinstance(node, ast.ClassDef) and node.name == "AI4Urban":
            selected.append(node)
    sigma = torch.as_tensor(solid.astype(np.float32), device=device)[None, None] * 1e8
    ns = dict(
        torch=torch,
        nn=nn,
        F=F,
        np=np,
        math=math,
        dx=cell,
        dy=cell,
        dz=cell,
        dt=dt,
        ub=ub,
        Re=re,
        sigma=sigma,
        LIBM=True,
        device=device,
        nlevel=int(math.log2(nz)) + 1,
        ratio_x=nx // nz,
        ratio_y=ny // nz,
    )
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(REFERENCE), "exec"), ns)
    ns["diag"] = float(ns["wA"][0, 0, 1, 1, 1])
    model = ns["AI4Urban"]().to(device).eval().requires_grad_(False)
    # Original inflow/outflow u ghost cells also force air through underground
    # faces on mountainous terrain. Apply the same IBM mask to those ghost faces.
    original_bc = model.boundary_condition_u
    west = torch.as_tensor(solid[:, :, 0], device=device)
    east = torch.as_tensor(solid[:, :, -1], device=device)

    def terrain_boundary(u, uu):
        original_bc(u, uu)
        uu[0, 0, 1:-1, 1:-1, 0].masked_fill_(west, 0.0)
        uu[0, 0, 1:-1, 1:-1, -1].masked_fill_(east, 0.0)
        return uu

    model.boundary_condition_u = terrain_boundary
    return model, ns


def allocate(shape, device):
    state = [torch.zeros((1, 1, *shape), device=device) for _ in range(4)]
    pads = [torch.zeros((1, 1, *(v + 2 for v in shape)), device=device) for _ in range(10)]
    return state, pads, torch.full((1, 1, *shape), 2.0, device=device)


def advance(model, state, pads, k1, dt, iterations):
    u, v, w, p = state
    uu, vv, ww, pp, bu, bv, bw, ku, kv, kw = pads
    result = model(u, uu, v, vv, w, ww, p, pp, bu, bv, bw, k1, dt, iterations, ku, kv, kw)
    return list(result[:4]), result[4], result[5]


@torch.inference_mode()
def self_test():
    mask = np.zeros((8, 16, 24), bool)
    mask[0] = True
    mask[:4, 6:10, 10:14] = True
    cpu, nc = build_model(mask, 8.0, torch.device("cpu"))
    gpu, ng = build_model(mask, 8.0, torch.device("cuda"))
    shape = mask.shape
    # Preserve and document original stencil gain/sign rather than silently
    # replacing it with a different discretization.
    z, y, x = np.indices(tuple(s + 2 for s in shape), dtype=np.float32)
    gains = []
    for operator, field in [(cpu.xadv, x * 8), (cpu.yadv, y * 8), (cpu.zadv, z * 8)]:
        value = operator(torch.from_numpy(field)[None, None])
        gains.append(float(value.mean()))
    assert np.allclose(gains, [-0.5, 0.5, 0.5], atol=2e-6), gains
    assert abs(float(nc["w1"].sum())) < 1e-7
    sc, pc, kc = allocate(shape, "cpu")
    sg, pg, kg = allocate(shape, "cuda")
    for _ in range(3):
        sc, _, _ = advance(cpu, sc, pc, kc, 0.5, 5)
        sg, _, _ = advance(gpu, sg, pg, kg, 0.5, 5)
    errors = [float((a - b.cpu()).abs().max()) for a, b in zip(sc, sg)]
    assert max(errors) < 1e-4, errors
    assert all(torch.isfinite(a).all() for a in sg)
    report = {
        "passed": True,
        "cpu_cuda_max_abs_error_uvwp": errors,
        "gradient_linear_gains_xyz": gains,
        "note": "Original half-strength gradient kernels retained. Numerical checks, not physical validation.",
    }
    print(json.dumps(report), flush=True)
    return report


@torch.inference_mode()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--save-every", type=int, default=10)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dense-every", type=int, default=0)
    ap.add_argument("--checkpoint-every", type=int, default=100)
    ap.add_argument("--run-name", default="ai4urban")
    args = ap.parse_args()
    torch.set_num_threads(8)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    if args.self_test:
        self_test()
        return
    root = Path.cwd()
    geom = root / "output/region/geometry/voxel_8m"
    assert args.run_name.replace("_", "").isalnum(), "Invalid run name"
    out = root / "output/region/physics" / args.run_name
    web = root / "visualizer/scenes/region" / f"{args.run_name}_wind"
    out.mkdir(parents=True, exist_ok=True)
    web.mkdir(parents=True, exist_ok=True)
    report = self_test()
    write_json(out / "solver_check.json", report)
    torch.cuda.empty_cache()
    solid = np.load(geom / "solid.npy")
    meta = json.loads((geom / "metadata.json").read_text())
    nz, ny, nx = solid.shape
    cell = 8.0
    dt = 0.5
    iterations = 5
    config = {
        "solver": "AI4Urban fixed convolution PDE solver (user supplied), not SCALED",
        "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_sha256": hashlib.sha256((geom / "solid.npy").read_bytes()).hexdigest(),
        "shape_zyx": list(solid.shape),
        "cell_m": cell,
        "dt_s": dt,
        "Re_code_multiplier": 0.15,
        "ub_raw": -1.0,
        "mg_iterations": iterations,
        "initial_velocity": "zero",
        "initial_pressure": "zero",
        "axes": "solid[z,y,x] in local frame; no legacy South Kensington transpose or flip. Viewer (u,v,w)=(-raw_u,raw_w,-raw_v).",
        "boundary_change": "Zero x-face u ghost values where adjacent terrain/obstacles are solid.",
        "precision": "float32, TF32 disabled",
        "original_gradient_gain": [-0.5, 0.5, 0.5],
        "limits": [
            "Startup transient; no steady-flow claim.",
            "Re is the supplied PG multiplier, not an independently specified Reynolds-number calibration.",
            "Original pressure/gradient discretization and fixed 5 MG iterations retained; monitor divergence.",
            "No measured weather, turbine rotor forcing, actuator disk or power model.",
        ],
    }
    config_file = out / "run_config.json"
    if config_file.exists():
        previous = json.loads(config_file.read_text())
        # I/O-only adapter updates may resume; all physics and geometry must match.
        if {k: v for k, v in previous.items() if k != "adapter_sha256"} != {
            k: v for k, v in config.items() if k != "adapter_sha256"
        }:
            raise RuntimeError(
                "Physics inputs changed; preserve this run and use a new output directory."
            )
        write_json(out / f"run_config_adapter_{previous['adapter_sha256'][:12]}.json", previous)
    write_json(config_file, config)
    model, ns = build_model(solid, cell, torch.device("cuda"))
    state, pads, k1 = allocate(solid.shape, "cuda")
    first = 0
    checkpoint = out / "checkpoint.h5"
    if checkpoint.exists():
        with h5py.File(checkpoint, "r") as f:
            first = int(f.attrs["step"])
            state = [
                torch.as_tensor(f[k][:], device="cuda")[None, None] for k in ["u", "v", "w", "p"]
            ]
    fluid = torch.as_tensor(~solid, device="cuda")
    near = F.max_pool3d(
        F.pad(
            torch.as_tensor(solid.astype(np.float32), device="cuda")[None, None],
            (1, 1, 1, 1, 1, 1),
            value=1,
        ),
        3,
        stride=1,
    )[0, 0]
    interior = near == 0
    del near
    ground = np.load(geom / "ground_mesh_m_yx.npy")
    study = np.load(geom / "study_area_8m_yx.npy")
    dense = None
    if args.dense_every:
        from export_ai4urban_series import DenseSeries

        dense = DenseSeries(
            root, solid, ground, study, dt, args.steps, reset=first == 0, prefix=args.run_name
        )
    yy, xx = np.meshgrid(np.arange(4, ny, 8), np.arange(4, nx, 8), indexing="ij")
    xx = xx.ravel()
    yy = yy.ravel()
    ox, oy, _ = meta["source_region_origin_xyz_m"]
    samples = []
    for agl in [40, 80, 120]:
        zz = np.floor((ground[yy, xx] + agl) / cell).astype(int)
        valid = study[yy, xx] & (zz >= 0) & (zz < nz)
        valid &= ~solid[np.clip(zz, 0, nz - 1), yy, xx]
        x, y, z = xx[valid], yy[valid], zz[valid]
        pos = np.column_stack(
            (ox + (x + 0.5) * cell, (z + 0.5) * cell, -oy - (y + 0.5) * cell)
        ).astype("<f4")
        samples.append((agl, x, y, z, pos, [torch.as_tensor(a, device="cuda") for a in (z, y, x)]))
    rows = json.loads((out / "metrics.json").read_text()) if (out / "metrics.json").exists() else []
    rows = [r for r in rows if r["step"] <= first]
    history = {a: [] for a, *_ in samples}
    steps = []
    oldmanifest = web / "manifest.json"
    if first and oldmanifest.exists():
        old = json.loads(oldmanifest.read_text())
        steps = [s for s in old["step_indices"] if s <= first]
        for agl, x, y, z, pos, indices in samples:
            oldlevel = next(l for l in old["levels"] if l["agl_m"] == agl)
            stored = np.fromfile(web / oldlevel["vectors"], dtype="<f4").reshape(
                old["frames"], len(x), 3
            )
            history[agl] = list(stored[: len(steps)])

    def save_web(step):
        if steps and step <= steps[-1]:
            return
        steps.append(step)
        levels = []
        for agl, x, y, z, pos, indices in samples:
            iz, iy, ix = indices
            u, v, w = [s[0, 0, iz, iy, ix].cpu().numpy() for s in state[:3]]
            vec = np.column_stack((-u, w, -v)).astype("<f4")
            assert np.isfinite(vec).all()
            history[agl].append(vec)
            all_vectors = np.stack(history[agl])
            speed = np.linalg.norm(all_vectors, axis=-1)
            # Version filenames keep a reader from combining a new manifest with
            # old-length arrays, and avoid the viewer server's immutable cache.
            pf = f"positions_{agl}.f32"
            vf = f"vectors_{agl}_s{step:06d}.f32"
            if not (web / pf).exists():
                pos.tofile(web / pf)
            all_vectors.tofile(web / vf)
            levels.append(
                {
                    "agl_m": agl,
                    "count": len(x),
                    "positions": pf,
                    "vectors": vf,
                    "mean_speed_by_step": speed.mean(axis=1).tolist(),
                    "max_speed_by_step": speed.max(axis=1).tolist(),
                }
            )
        write_json(
            web / "manifest.json",
            {
                "source": config["solver"],
                "frames": len(steps),
                "step_indices": steps,
                "time_seconds": [s * dt for s in steps],
                "cell_m": 8,
                "horizontal_sample_spacing_m": 64,
                "levels": levels,
                "limits": config["limits"],
                "complete": step == args.steps,
                "target_steps": args.steps,
            },
        )

    def save_checkpoint(step):
        tmp = out / "checkpoint.tmp.h5"
        with h5py.File(tmp, "w") as f:
            f.attrs["step"] = step
            f.attrs["time_seconds"] = step * dt
            for key, s in zip(["u", "v", "w", "p"], state):
                f.create_dataset(key, data=s[0, 0].cpu().numpy())
        tmp.replace(checkpoint)

    def diagnostics(step, elapsed, p_error, r_error):
        assert all(torch.isfinite(s).all().item() for s in state), "Non-finite solver state"
        u, v, w, p = state
        speed = torch.sqrt(u.square() + v.square() + w.square())[0, 0]
        div = (
            model.xadv(model.boundary_condition_u(u, pads[0]))
            + model.yadv(model.boundary_condition_v(v, pads[1]))
            + model.zadv(model.boundary_condition_w(w, pads[2]))
        )[0, 0]
        row = {
            "step": step,
            "time_seconds": step * dt,
            "elapsed_s": elapsed,
            "fluid_mean_speed": float(speed[fluid].mean()),
            "fluid_max_speed": float(speed[fluid].max()),
            "solid_max_speed": float(speed[~fluid].max()),
            "fluid_interior_divergence_rms_s_inv": float(div[interior].square().mean().sqrt()),
            "fluid_divergence_rms_s_inv": float(div[fluid].square().mean().sqrt()),
            "pressure_correction_max": p_error,
            "coarsest_pressure_residual_max": r_error,
            "advective_cfl_sum_max": float((u.abs() + v.abs() + w.abs()).max()) * dt / cell,
            "gpu_peak_gib": torch.cuda.max_memory_allocated() / 1024**3,
        }
        assert row["advective_cfl_sum_max"] < 1.0, "CFL >= 1: stop and inspect timestep"
        assert row["solid_max_speed"] < 1e-4, "IBM leakage above diagnostic tolerance"
        rows.append(row)
        write_json(out / "metrics.json", rows)
        write_json(
            out / "status.json",
            {
                "solver": "AI4Urban",
                "completed_steps": step,
                "target_steps": args.steps,
                "simulated_seconds": step * dt,
                "complete": step == args.steps,
                "finite": True,
                "last_diagnostics": row,
                "steady_state_verified": False,
            },
        )
        print(json.dumps(row), flush=True)

    started = time.time()
    print(f"AI4Urban: {solid.shape}, 8 m, resume {first}, target {args.steps}", flush=True)
    if not steps:
        save_web(first)
    if dense:
        dense.save(first, state)
    for step in range(first + 1, args.steps + 1):
        state, correction, residual = advance(model, state, pads, k1, dt, iterations)
        pe = float(correction.abs().max())
        re = float(residual.abs().max())
        del correction, residual
        if not math.isfinite(pe) or pe > 80000 or not math.isfinite(re):
            raise RuntimeError("Pressure solve diverged")
        if step <= 3 or step % args.save_every == 0 or step == args.steps:
            diagnostics(step, time.time() - started, pe, re)
            save_web(step)
        if dense and (step % args.dense_every == 0 or step == args.steps):
            dense.save(step, state)
        if step % args.checkpoint_every == 0 or step == args.steps:
            save_checkpoint(step)
    if args.steps > first:
        with h5py.File(out / f"uvw_{args.steps:06d}.h5", "w") as f:
            a = f.create_dataset(
                "uvw",
                (3, nz, ny, nx),
                dtype="f2",
                chunks=(1, 8, 64, 64),
                compression="gzip",
                compression_opts=1,
            )
            for i, s in enumerate(state[:3]):
                a[i] = s[0, 0].cpu().numpy().astype(np.float16)
            f.attrs["step"] = args.steps
            f.attrs["dt_s"] = dt
            f.attrs["cell_m"] = cell
            f.attrs["components"] = "raw NN4PDEs u,v,w; local Cartesian velocity = (-u,v,w)"
    print("AI4Urban trial complete; fresh fixed-operator PDE solution saved.", flush=True)


if __name__ == "__main__":
    main()
