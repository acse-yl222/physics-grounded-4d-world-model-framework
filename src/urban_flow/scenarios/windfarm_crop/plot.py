from common.storage import Storage

"""Export standalone maps of the paired windfarm crop experiment."""
import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Storage.load().run("windfarm", "crop")
g = json.loads((root / "geometry.json").read_text())
a = json.loads((root / "control/result.json").read_text())
b = json.loads((root / "actuator/result.json").read_text())
u0 = np.load(root / a["files"][-1])[0, 0]
u1 = np.load(root / b["files"][-1])[0, 0]
ground = np.load(root / "ground.npy")
ox, oy, _ = g["origin_xyz_m"]
lx, ly, _ = g["size_xyz_m"]
extent = [ox, ox + lx, oy, oy + ly]
fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
for ax, data, title, cm, vmin, vmax in zip(
    axes.ravel(),
    [ground, u0, u1, u0 - u1],
    [
        "Terrain and 23 turbines",
        "Terrain + towers, actuator off",
        "Terrain + towers + 23 actuator disks",
        "Actuator effect: control minus actuator",
    ],
    ["terrain", "viridis", "viridis", "RdBu_r"],
    [ground.min(), 0, 0, -2],
    [ground.max(), 12, 12, 2],
):
    im = ax.imshow(data, origin="lower", extent=extent, cmap=cm, vmin=vmin, vmax=vmax)
    for t in g["turbines"]:
        x, y, z = t["hub_xyz_m"]
        ax.plot(x, y, ".", color="white", markersize=3)
    ax.set_title(title)
    ax.set_xlabel("Local x [m]")
    ax.set_ylabel("Local y [m]")
    fig.colorbar(
        im,
        ax=ax,
        label="Elevation [m]" if ax is axes[0, 0] else "Axial velocity / difference [m/s]",
    )
fig.suptitle(
    f"4 m crop | 10 s startup transient | 80 m above local terrain | not engineering validated"
)
fig.savefig(root / "comparison.png", dpi=160)
plt.close(fig)
