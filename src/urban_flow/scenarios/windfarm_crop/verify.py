from common.storage import Storage

"""Verify paired crop exports and quantify their difference without asserting physical validation."""
import json
from pathlib import Path
import numpy as np

root = Storage.load().run("windfarm", "crop")
g = json.loads((root / "geometry.json").read_text())
a = json.loads((root / "control/result.json").read_text())
b = json.loads((root / "actuator/result.json").read_text())
assert len(g["turbines"]) == 23 and g["all_23_rotors_inside"]
assert (
    a["complete"]
    and b["complete"]
    and a["times"] == b["times"]
    and a["completed_steps"] == b["completed_steps"] == 400
)
mask = np.load(root / "slice_mask.npy")
valid = mask == 0
assert len(a["files"]) == len(b["files"]) == 21
for case in [a, b]:
    assert len(case["metrics"]) == 21 and all(len(m["thrust_N"]) == 23 for m in case["metrics"])
    assert all(m["cfl"] < 0.8 for m in case["metrics"])
    for f in case["files"]:
        x = np.load(root / f, mmap_mode="r")
        assert x.shape == (1, 3, 512, 1024)
        assert np.isfinite(x[0, :, valid]).all() and np.isnan(x[0, :, ~valid]).all()
np.testing.assert_array_equal(np.load(root / a["files"][0]), np.load(root / b["files"][0]))
assert all(all(t == 0 for t in m["thrust_N"]) for m in a["metrics"])
assert sum(b["metrics"][-1]["thrust_N"]) > 0
u0 = np.load(root / a["files"][-1])[0, 0]
u1 = np.load(root / b["files"][-1])[0, 0]
d = u0 - u1
v0 = np.array(a["metrics"][-1]["disk_velocity_m_s"])
v1 = np.array(b["metrics"][-1]["disk_velocity_m_s"])
report = dict(
    numerical_checks_passed=True,
    all_23_turbines_included=True,
    cell_m=4,
    shape_zyx=g["shape_zyx"],
    size_xyz_m=g["size_xyz_m"],
    steps_per_case=400,
    frames_per_case=21,
    dt_s=0.025,
    simulated_seconds=10,
    slice_agl_m=g["slice_agl_m"],
    hub_agl_range_m=g["hub_agl_range_m"],
    mean_disk_velocity_control_m_s=float(v0.mean()),
    mean_disk_velocity_actuator_m_s=float(v1.mean()),
    disk_velocity_difference_range_m_s=[float((v0 - v1).min()), float((v0 - v1).max())],
    mean_disk_velocity_reduction_percent=float((v0.mean() - v1.mean()) / v0.mean() * 100),
    slice_axial_difference_range_m_s=[float(np.nanmin(d)), float(np.nanmax(d))],
    max_cfl={c["case"]: max(m["cfl"] for m in c["metrics"]) for c in [a, b]},
    max_speed_m_s={c["case"]: max(m["max_speed_m_s"] for m in c["metrics"]) for c in [a, b]},
    gpu_peak_gib=max(m["gpu_peak_gib"] for c in [a, b] for m in c["metrics"]),
    final_divergence_rms_s_inv={
        c["case"]: c["metrics"][-1]["air_divergence_rms_s_inv"] for c in [a, b]
    },
    steady_state_verified=False,
    engineering_accuracy_validated=False,
    stopped_preliminary_run="dt=0.1 s exceeded CFL limit at step 60; retained separately. Final paired runs use dt=0.025 s.",
    limits=b["limits"],
)
(root / "report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report), flush=True)
