"""
Display the simulated driving trajectories of vehicles on a multi-intersection road network
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import sys
import os

from traffic.configs.default import GRID_SIZE
from traffic.data.generate_complex import (
    get_road_network, build_road_lane_centers, simulate_trajectory,
)

roads = get_road_network()
lane, drivable = build_road_lane_centers(roads)
traj, tracks = simulate_trajectory(total_steps=40, seed=0)

road_cmap = ListedColormap(['white', '#EAEAEA'])

fig, ax = plt.subplots(figsize=(10, 10))
ax.imshow(drivable[:, :, 0], cmap=road_cmap, origin='upper',
          vmin=0, vmax=1, aspect='equal')

for road in roads:
    cl = road["centerline"]
    ax.plot(cl[:, 1], cl[:, 0], color='#CCCCCC', linewidth=0.5, linestyle='--')

for vid, vt in tracks.items():
    pos = vt['positions']
    if len(pos) < 2:
        continue
    rows = [p[1] for p in pos]
    cols = [p[2] for p in pos]
    color = plt.cm.tab20(vid % 20)
    ax.plot(cols, rows, '-', color=color, linewidth=1.0, alpha=0.7)
    ax.plot(cols[0], rows[0], 'o', color=color, markersize=4) # start
    ax.plot(cols[-1], rows[-1], 'x', color=color, markersize=4)

ax.set_title(f'Traffic on multi-intersection network', fontsize=12)
ax.set_xlim(0, GRID_SIZE)
ax.set_ylim(GRID_SIZE, 0)

save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'train', 'traffic_network.png')
os.makedirs(os.path.dirname(save_path), exist_ok=True)
fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved: {save_path}")
print(f"Number of vehicles: {len(tracks)}")
lens = [len(vt['positions']) for vt in tracks.values()]
print(f"Average trajectory length: {np.mean(lens):.1f} frames, maximum {max(lens)}")
