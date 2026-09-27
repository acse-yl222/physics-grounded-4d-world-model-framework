from common.storage import Storage
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Storage.load().run('actuator_lab','fullgradient')
cases={n:json.loads((root/n/'result.json').read_text()) for n in ['disk_1p0m','disk_0p5m','control_0p5m']}
arrays={n:np.load(root/n/'hub_uvw_tcyx.npy') for n in cases}
for n,c in cases.items():
 a=arrays[n];assert a.shape==(41,3,*c['shape_zyx'][1:]) and np.isfinite(a).all()
 assert max(m['cfl'] for m in c['metrics'])<.8
control=arrays['control_0p5m'];assert np.max(np.abs(control[:,0]-8))<1e-5 and np.max(np.abs(control[:,1:]))<1e-5
fine=arrays['disk_0p5m'];coarse=arrays['disk_1p0m']
# Match the z=32.5 m coarse plane by averaging adjacent fine planes at 32.25/32.75.
full=np.load(root/'disk_0p5m/final_uvw_czyx.npy',mmap_mode='r')
matched=full[:,64:66].mean(axis=1).reshape(3,64,2,128,2).mean(axis=(2,4))
coarse_final=coarse[-1]
profiles={}
for n,a in arrays.items():
 c=cases[n];dx=c['cell_m'];u=a[-1,0];ny,nx=u.shape;line=u[ny//2-1:ny//2+1].mean(axis=0)
 profiles[n]={str(d):float(line[min(round((32+d*16)/dx-.5),nx-1)]) for d in [0,1,2,3,4]}
report={'numerical_checks_passed':True,'frames_per_case':41,'control_max_u_error':float(np.max(np.abs(control[:,0]-8))),
 'disk_velocity_relative_grid_difference':abs(cases['disk_0p5m']['metrics'][-1]['disk_velocity']-cases['disk_1p0m']['metrics'][-1]['disk_velocity'])/cases['disk_0p5m']['metrics'][-1]['disk_velocity'],
 'hub_u_grid_comparison_rms_m_s':float(np.mean((matched[0]-coarse_final[0])**2)**.5),'centerline_velocity_at_x_over_D_downstream':profiles,
 'final_divergence_rms_s_inv':{n:c['metrics'][-1]['div_rms'] for n,c in cases.items()},'steady_state_verified':False,'engineering_accuracy_validated':False,'limitations':cases['disk_0p5m']['limitations']}
(root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
fig,axes=plt.subplots(2,1,figsize=(10,8),constrained_layout=True)
for ax,name,title in zip(axes,['control_0p5m','disk_0p5m'],['No actuator force: control','Actuator disk: 0.5 m grid, model time 20 s']):
 im=ax.imshow(arrays[name][-1,0],origin='lower',extent=[0,128,0,64],vmin=0,vmax=10,cmap='viridis');ax.plot([32,32],[24,40],color='cyan',lw=2);ax.set_title(title);ax.set_xlabel('x [m]');ax.set_ylabel('y [m]');fig.colorbar(im,ax=ax,label='Axial velocity [m/s]')
fig.savefig(root/'comparison.png',dpi=160);plt.close(fig)
