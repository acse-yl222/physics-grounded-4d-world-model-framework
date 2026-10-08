"""Isolated non-rotating actuator-disk experiment using the supplied AI4Urban operators.
Not LES, blade-resolved CFD, or a calibrated turbine. Spatial derivative gains corrected to unit magnitude for this isolated experiment.
"""

# Compatibility for direct source-script execution.
if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from common.runtime import source_path, trial_root
from common.layout import repo_root
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
import torch
from urban_flow.scenarios.region.run_ai4urban import build_model, allocate, advance, write_json


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cell", type=float, default=0.5)
    p.add_argument("--ct", type=float, default=4 / 3)
    p.add_argument("--seconds", type=float, default=20)
    a = p.parse_args()
    torch.set_num_threads(8)
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    cell = a.cell
    dt = 0.02 * cell
    shape = tuple(int(v / cell) for v in (64, 64, 128))
    steps = round(a.seconds / dt)
    stride = round(0.5 / dt)
    name = ("disk" if a.ct else "control") + "_" + str(cell).replace(".", "p") + "m"
    root = trial_root("actuator_lab", "actuator")
    out = root / name
    out.mkdir(parents=True, exist_ok=True)
    config = dict(
        name=name,
        cell_m=cell,
        shape_zyx=shape,
        dt=dt,
        steps=steps,
        domain_xyz_m=[128, 64, 64],
        disk_xyz_m=[32, 32, 32],
        diameter_m=16,
        U0=8,
        Ct_prime=a.ct,
        rho=1.225,
        kernel_sigma_x_m=2,
        kernel_edge_width_m=1,
        force_ramp_s=2,
        solver="AI4Urban fixed convolutions + symmetric explicit actuator forcing",
        reference="https://lesgo.me.jhu.edu/actuator-disk.html",
        limitations=[
            "Non-rotating axial-force disk; no blades, torque, terrain, tower or nacelle.",
            "Slip lateral/top/bottom walls; prescribed axial velocity at both x faces and original pressure boundary.",
            "Spatial derivatives rescaled from original half gain to unit gain; this isolated variant is not the unchanged windfarm solver.",
            "Grid comparison holds physical force smoothing width constant; no claim of full grid convergence.",
        ],
    )
    write_json(out / "config.json", config)
    solid = np.zeros(shape, bool)
    model, ns = build_model(solid, cell, torch.device("cuda"), dt=dt, ub=-8.0)
    # The reference gradient is half the derivative of a linear field. Rescale
    # only this isolated experiment, so physical actuator acceleration is coupled
    # to unit-gain spatial derivatives. Keep original windfarm runs unchanged.
    for op in [model.xadv, model.yadv, model.zadv]:
        op.weight.mul_(2.0)
    zz, yy, xx = torch.meshgrid(
        *[torch.arange(6, device="cuda") * cell for _ in range(3)], indexing="ij"
    )
    gains = [
        float(op(field[None, None]).mean())
        for op, field in [(model.xadv, xx), (model.yadv, yy), (model.zadv, zz)]
    ]
    assert np.allclose(gains, [-1, 1, 1], atol=2e-6), gains
    config["gradient_linear_gains_xyz"] = gains
    # No terrain in this isolated experiment. Free-slip bottom instead of no-slip.
    old = model.boundary_condition_u

    def slip_u(u, pad):
        old(u, pad)
        pad[0, 0, 0, :, :] = pad[0, 0, 1, :, :]
        return pad

    model.boundary_condition_u = slip_u
    old_v = model.boundary_condition_v

    def slip_v(v, pad):
        old_v(v, pad)
        pad[0, 0, 0, :, :] = pad[0, 0, 1, :, :]
        return pad

    model.boundary_condition_v = slip_v
    state, pads, k1 = allocate(shape, "cuda")
    state[0].fill_(-8.0)
    z, y, x = torch.meshgrid(
        *[(torch.arange(n, device="cuda") + 0.5) * cell for n in shape], indexing="ij"
    )
    radius = torch.sqrt((y - 32) ** 2 + (z - 32) ** 2)
    kernel = torch.exp(-0.5 * ((x - 32) / 2) ** 2) * torch.sigmoid((8 - radius) / 1.0)
    kernel /= kernel.sum() * cell**3
    assert abs(float(kernel.sum() * cell**3) - 1) < 1e-5
    area = math.pi * 8**2
    rho = 1.225
    del x, y, z, radius
    metrics = []
    frames = []
    times = []
    start = time.time()

    def force(t, h):
        ud = float((-state[0][0, 0] * kernel).sum() * cell**3)
        thrust = 0.5 * rho * area * a.ct * ud * abs(ud) * min(t / 2, 1)
        # raw u has reversed x sign: positive acceleration is physical drag.
        acceleration = thrust / rho * kernel
        assert float(((-state[0][0, 0]) * (-acceleration)).sum()) <= 1e-4, "Force added flow energy"
        state[0].add_(h * acceleration[None, None])
        return ud, thrust

    def save(step, ud, thrust):
        u, v, w = state[:3]
        iz = shape[0] // 2
        plane = torch.stack([-u[0, 0, iz], v[0, 0, iz], w[0, 0, iz]]).cpu().numpy().astype("<f4")
        assert np.isfinite(plane).all()
        frames.append(plane)
        times.append(step * dt)
        div = (
            model.xadv(model.boundary_condition_u(u, pads[0]))
            + model.yadv(model.boundary_condition_v(v, pads[1]))
            + model.zadv(model.boundary_condition_w(w, pads[2]))
        )
        cfl = float((u.abs() + v.abs() + w.abs()).max()) * dt / cell
        assert cfl < 0.8 and all(torch.isfinite(s).all() for s in state), "Unstable state"
        row = dict(
            step=step,
            time=step * dt,
            disk_velocity=ud,
            thrust_N=thrust,
            cfl=cfl,
            div_rms=float(div.square().mean().sqrt()),
            u_min=float(-u.max()),
            u_max=float(-u.min()),
            gpu_peak_gib=torch.cuda.max_memory_allocated() / 2**30,
            elapsed_s=time.time() - start,
        )
        metrics.append(row)
        write_json(out / "metrics.json", metrics)
        print(json.dumps(row), flush=True)

    save(0, 8, 0)
    for step in range(1, steps + 1):
        t = (step - 0.5) * dt
        force(t, dt / 2)
        state, correction, residual = advance(model, state, pads, k1, dt, 10)
        assert torch.isfinite(correction).all() and float(correction.abs().max()) < 80000, (
            "Pressure solve diverged"
        )
        ud, thrust = force(t, dt / 2)
        if step % stride == 0 or step == steps:
            save(step, ud, thrust)
    np.save(out / "hub_uvw_tcyx.npy", np.stack(frames))
    np.save(
        out / "final_uvw_czyx.npy",
        np.stack([s[0, 0].cpu().numpy() * (-1 if i == 0 else 1) for i, s in enumerate(state[:3])]),
    )
    config.update(times=times, complete=True, metrics=metrics, file=name + "/hub_uvw_tcyx.npy")
    write_json(out / "result.json", config)
    print("COMPLETE", name, flush=True)


if __name__ == "__main__":
    main()
