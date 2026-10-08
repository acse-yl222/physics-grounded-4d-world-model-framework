from common.storage import Storage
from common.runtime import trial_root
import json, numpy as np
from pathlib import Path

base = Storage.load().run("windfarm", "mac_2m")
out = trial_root("windfarm", "movie")
out.mkdir(parents=True, exist_ok=True)
m = json.loads((base / "manifest.json").read_text())
g = json.loads((base / "geometry.json").read_text())
frames = []
for f in m["files"]:
    a = np.load(base / f, mmap_mode="r")[0, 0]
    frames.append(a[2::4, 2::4].astype(np.float16))
np.save(out / "u.npy", np.stack(frames))
np.save(out / "ground.npy", np.load(base / "ground.npy")[2::4, 2::4])
g.update(
    times=m["times"],
    display_shape=[256, 512],
    display_cell_m=8,
    display_first_center_offset_m=5,
    solver="Independent MAC, not AI4Urban",
    simulation_cell_m=2,
    completed_steps=m["completed_steps"],
)
(out / "metadata.json").write_text(json.dumps(g))
print(len(frames), g["times"][-1])
