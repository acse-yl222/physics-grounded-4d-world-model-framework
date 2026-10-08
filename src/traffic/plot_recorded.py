"""Plot actual recorded vehicle positions over retained road lane geometry."""
from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

def main():
 p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();O=a.run
 roads=json.loads((O/'roads.json').read_text());vertices=np.asarray(roads['positions']);triangles=np.asarray(roads['triangles']);frames=json.loads((O/'trajectories.json').read_text())['frames'];times=json.loads((O/'manifest.json').read_text())['time']['samples'];k=max(range(len(frames)),key=lambda i:len(frames[i]['ids']));points=np.asarray(frames[k]['positions'])
 fig,ax=plt.subplots(figsize=(10,10));ax.add_collection(PolyCollection(vertices[triangles,:2],facecolors='#9ca8af',edgecolors='none',alpha=.8));ax.scatter(points[:,0],points[:,1],s=12,c='#e35335',label=f'{len(points)} recorded vehicles');ax.set(xlim=(-2000,2000),ylim=(-2000,2000),aspect='equal',xlabel='East (m)',ylabel='North (m)',title=f'Canary Wharf 4 km × 4 km · simulated vehicles at t={times[k]:g} s\nActual OSM network; seeded uncalibrated passenger demand');ax.legend(loc='upper right');ax.grid(alpha=.15);fig.text(.5,.01,'OSM contributors / Geofabrik · SUMO · flat display elevation; inferred signals',ha='center',fontsize=9);fig.savefig(O/'traffic-overview.png',dpi=160,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':main()
