from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
out=Path('output/paper_rotor');meta=json.loads((out/'comparison.json').read_text())
a=np.load(out/'torch_paper.npz');b=np.load(out/'torch_legacy.npz');c=np.load(out/'triton_paper.npz')
errors=dict(final_velocity_max_abs_m_s=float(np.max(np.abs(a['u']-c['u']))),final_velocity_rms_m_s=float(np.sqrt(np.mean((a['u']-c['u'])**2))))
ref=out/'refined/torch_paper.npz'
if ref.exists():
 r=np.load(ref);errors['refinement_disc_speed_change_percent']=float(100*(r['history'][-1,1]/a['history'][-1,1]-1))
(out/'metrics.json').write_text(json.dumps(errors,indent=2))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
for ax,d,label in zip(axes[0],[a,b],['Paper rotor kernel / PyTorch','Legacy smooth rotor kernel / PyTorch']):
 im=ax.imshow(d['frames'][-1],origin='lower',extent=[0,9.6,0,3.2],vmin=0,vmax=2.5,cmap='viridis',aspect='equal');ax.plot([2.4,2.4],[1.2,2.0],color='white',lw=2);ax.set(title=label,xlabel='x (m)',ylabel='y (m)')
fig.colorbar(im,ax=axes[0],label='Axial velocity (m/s)',shrink=.75)
y=(np.arange(32)+.5)*.1
for d,label,style in [(a,'Paper / PyTorch','-'),(b,'Legacy / PyTorch','--'),(c,'Paper / Triton',':')]:
 axes[1,0].plot((y-1.6)/.8,1-d['u'][16,:,int((2.4+3*.8)/.1)]/2,style,label=label)
 axes[1,1].plot(d['history'][:,0],d['history'][:,2],style,label=label)
if ref.exists():axes[1,1].plot(r['history'][:,0],r['history'][:,2],label='Paper / PyTorch / 0.05 m',alpha=.7)
axes[1,0].set(title='Wake at 3D downstream, t = 10 s',xlabel='Cross-stream distance / D',ylabel='Velocity deficit 1-u/U')
axes[1,1].set(title='Thrust history',xlabel='Physical time (s)',ylabel='Thrust (N)')
for ax in axes[1]:ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.suptitle('Controlled rotor comparison - single-phase pilot, not full paper reproduction',fontsize=14)
fig.savefig(out/'comparison.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained');ims=[]
for ax,label in zip(axes,['Paper Gaussian + hard radial edge','Legacy Gaussian + smooth radial edge']):
 ims.append(ax.imshow(a['frames'][0],origin='lower',extent=[0,9.6,0,3.2],vmin=0,vmax=2.5,cmap='viridis',aspect='equal'));ax.set(title=label,ylabel='y (m)');ax.plot([2.4,2.4],[1.2,2],color='white',lw=2)
axes[-1].set_xlabel('x (m)');fig.colorbar(ims[0],ax=axes,label='u (m/s)',shrink=.8);title=fig.suptitle('')
def frame(i):
 for im,d in zip(ims,[a,b]):im.set_data(d['frames'][i])
 title.set_text(f"PyTorch CFD pilot | t = {a['history'][i,0]:.2f} s | 0.1 m grid")
 return ims+[title]
FuncAnimation(fig,frame,frames=len(a['frames']),interval=100).save(out/'wake.gif',writer=PillowWriter(fps=10));plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4),layout='constrained');v=np.linspace(-2,4,121)
ax.plot(v,np.ones_like(v),label='Old stationary hub assumption');ax.plot(v,(8-v)**2/64,label='Paper relative inflow law')
ax.set(xlabel='Prescribed hub velocity along wind (m/s)',ylabel='Thrust / stationary thrust',title='Same imposed local wind 8 m/s; analytic load-law comparison')
ax.legend();ax.grid(alpha=.2);fig.savefig(out/'relative_inflow.png',dpi=150)
print(json.dumps(errors,indent=2))
