from common.storage import Storage
from common.runtime import source_path, trial_root
"""Figures and summary for the 4 m Neural Physics runs, with the 2 m Triton run as reference."""
import json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

SUF=sys.argv[1] if len(sys.argv)>1 else '';root=Path.cwd();scenes=Storage.load().assets('windfarm','runs');out=trial_root('windfarm','analysis'+SUF);out.mkdir(parents=True,exist_ok=True)
C=dict(paper='#2a78d6',legacy='#eb6834',triton2m='#1baf7a')
TOP={'':'','_opentop':' · open top','_lid':' · terrain-following lid'}[SUF];LABEL=dict(paper='Neural Physics 4 m · paper kernel'+TOP,legacy='Neural Physics 4 m · legacy kernel'+TOP,triton2m='Triton 2 m · legacy kernel · closed lid')
seq=LinearSegmentedColormap.from_list('blue',['#cde2fb','#86b6ef','#3987e5','#1c5cab','#0d366b'])
div=LinearSegmentedColormap.from_list('div',['#1c5cab','#86b6ef','#f0efec','#f08a88','#b3261e'])
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#8a8a86','axes.labelcolor':'#3a3a38','xtick.color':'#5a5a57','ytick.color':'#5a5a57','axes.grid':True,'grid.color':'#e6e5e1','grid.linewidth':.6})
runs={'paper':scenes/f'np4m_paper{SUF}','legacy':scenes/f'np4m_legacy{SUF}','triton2m':scenes/'mac_2m'}
man={k:json.loads((p/'manifest.json').read_text()) for k,p in runs.items()}
geo={k:json.loads((p/'geometry.json').read_text()) for k,p in runs.items()}
g=geo['paper'];T=g['turbines'];order=np.argsort([t['hub_xyz_m'][0] for t in T]);ids=[T[i]['id'].replace('node-','')[-3:] for i in order]
def last(k):return np.load(runs[k]/man[k]['files'][-1])[0,0].astype(np.float32)
def extent(k):gg=geo[k];ox,oy,_=gg['origin_xyz_m'];nz,ny,nx=gg['shape_zyx'];h=gg['cell_m'];return [ox,ox+nx*h,oy,oy+ny*h]

# 1. Final 80 m AGL axial-velocity maps.
fig,ax=plt.subplots(4,1,figsize=(11,17),constrained_layout=True)
for a,k in zip(ax,['paper','legacy','triton2m']):
 im=a.imshow(last(k),origin='lower',extent=extent(k),cmap=seq,vmin=0,vmax=14,interpolation='nearest')
 a.set_title(f"{LABEL[k]} · t = {man[k]['times'][-1]:.0f} s",loc='left');a.set_aspect('equal');a.grid(False)
 for t in T:hx,hy,_=t['hub_xyz_m'];a.plot([hx,hx],[hy-t['radius_m'],hy+t['radius_m']],color='#fcfcfb',lw=1.2)
fig.colorbar(im,ax=ax[:3],label='u at 80 m above ground (m/s)',shrink=.6)
d=last('paper')-last('legacy');im=ax[3].imshow(d,origin='lower',extent=extent('paper'),cmap=div,vmin=-2,vmax=2,interpolation='nearest')
ax[3].set_title('Paper minus legacy kernel (same 4 m solver)',loc='left');ax[3].set_aspect('equal');ax[3].grid(False);fig.colorbar(im,ax=ax[3],label='Δu (m/s)',shrink=.8)
for a in ax:a.set_xlabel('x (m), wind from left');a.set_ylabel('y (m)')
fig.savefig(out/'slices_80m.png',dpi=130);plt.close(fig)

# 2. Per-turbine disc speed and thrust at the final time, upstream to downstream.
fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True,constrained_layout=True);w=.27;x=np.arange(len(T))
for j,k in enumerate(['paper','legacy','triton2m']):
 r=man[k]['metrics'][-1];ax[0].bar(x+(j-1)*w,np.array(r['disk_velocity_m_s'])[order],w*.9,color=C[k],label=LABEL[k])
 ax[1].bar(x+(j-1)*w,np.array(r['thrust_N'])[order]/1e3,w*.9,color=C[k])
ax[0].set_ylabel('Disc-averaged u (m/s)');ax[1].set_ylabel('Thrust (kN)');ax[1].set_xticks(x,ids,rotation=90);ax[1].set_xlabel('Turbine (id suffix), sorted upstream → downstream')
ax[0].legend(frameon=False,ncol=3,loc='upper left',bbox_to_anchor=(0,1.16));ax[0].grid(axis='x',visible=False);ax[1].grid(axis='x',visible=False)
fig.savefig(out/'turbines.png',dpi=130);plt.close(fig)

# 3. Farm totals over time.
fig,ax=plt.subplots(1,2,figsize=(11,3.8),constrained_layout=True)
for k in runs:
 t=np.array(man[k]['times']);M=man[k]['metrics']
 ax[0].plot(t,[sum(r['thrust_N'])/1e6 for r in M],color=C[k],lw=2,label=LABEL[k]);ax[1].plot(t,[np.mean(r['disk_velocity_m_s']) for r in M],color=C[k],lw=2)
ax[0].set_ylabel('Total farm thrust (MN)');ax[1].set_ylabel('Mean disc u (m/s)')
for a in ax:a.set_xlabel('Simulated time (s)')
ax[0].legend(frameon=False,fontsize=8);fig.savefig(out/'history.png',dpi=130);plt.close(fig)

# 4. Wake profiles behind the most upstream turbine, from the final 3-D u fields.
up=T[order[0]];hx,hy,hz=up['hub_xyz_m'];D=up['diameter_m'];ox,oy,oz=g['origin_xyz_m'];h=g['cell_m']
fields={k:np.load(source_path('legacy_output',f'windfarm_neural/np4m_{k}{SUF}/u_final.npy'),mmap_mode='r') for k in ('paper','legacy')}
kz=int((hz-oz)//h);iy0=int((hy-1.5*D-oy)//h);iy1=int((hy+1.5*D-oy)//h)+1;yy=(np.arange(iy0,iy1)+.5)*h+oy
fig,ax=plt.subplots(1,5,figsize=(12,3.8),sharey=True,constrained_layout=True);prof={}
for k,u in fields.items():
 uref=float(u[kz,int((hy-oy)//h),int((hx-2*D-ox)//h)]);prof[k]=dict(u_ref_2D_upstream=uref)
 for a,xd in zip(ax,[1,3,5,8,10]):
  line=np.asarray(u[kz,iy0:iy1,int((hx+xd*D-ox)//h)],dtype=np.float32)/uref;a.plot(line,(yy-hy)/D,color=C[k],lw=2,label=LABEL[k].split(' · ')[1]);a.set_title(f'x/D = {xd}');a.set_xlabel('u / u_ref')
  prof[k][f'centreline_u_over_uref_xD{xd}']=float(line[len(line)//2])
ax[0].set_ylabel('(y − y_hub) / D');ax[0].legend(frameon=False,fontsize=8)
fig.suptitle(f"Hub-height wake of the most upstream turbine ({up['id']}), final time",x=.01,ha='left');fig.savefig(out/'wake_profiles.png',dpi=130);plt.close(fig)

summary={}
for k in runs:
 M=man[k]['metrics'];t=np.array(man[k]['times']);tot=np.array([sum(r['thrust_N']) for r in M]);late=t>=t[-1]-100
 r=M[-1];summary[k]=dict(label=LABEL[k],simulated_s=man[k]['simulated_seconds'],steps=man[k]['completed_steps'],wall_s=r['elapsed_s'],gpu_peak_gib=r['gpu_peak_gib'],cell_m=geo[k]['cell_m'],
  total_thrust_MN=float(tot[-1]/1e6),extracted_T_times_ud_MW=float(np.dot(r['thrust_N'],r['disk_velocity_m_s'])/1e6),mean_disc_u=float(np.mean(r['disk_velocity_m_s'])),min_disc_u=float(np.min(r['disk_velocity_m_s'])),max_disc_u=float(np.max(r['disk_velocity_m_s'])),
  last100s_total_thrust_rel_range=float(np.ptp(tot[late])/tot[late].mean()),final_divergence_rms=r['pressure']['divergence_rms'],
  applied_over_thrust=float(sum(r['applied_fluid_force_N'])/sum(r['thrust_N'])) if 'applied_fluid_force_N' in r else None,
  per_turbine=[dict(id=T[i]['id'],disc_u=r['disk_velocity_m_s'][i],thrust_kN=r['thrust_N'][i]/1e3) for i in order])
summary['wake_upstream_turbine']=dict(id=up['id'],diameter_m=D,**prof)
p,l=(np.array(man[k]['metrics'][-1]['disk_velocity_m_s']) for k in ('paper','legacy'))
summary['paper_vs_legacy_disc_u_rel']=dict(mean=float(np.mean(p/l-1)),min=float(np.min(p/l-1)),max=float(np.max(p/l-1)))
(out/'summary.json').write_text(json.dumps(summary,indent=1));print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='per_turbine'} for k,v in summary.items()},indent=1))

# Closed lid versus open top: 80 m AGL median speed along x (same 4 m solver, paper kernel).
if SUF:
 fig,ax=plt.subplots(figsize=(8,3.6),constrained_layout=True);gr=np.load(runs['paper']/'ground.npy');xs=np.arange(gr.shape[1])*g['cell_m']+g['origin_xyz_m'][0]+g['cell_m']/2;prof={};flux={}
 for k,lab,col in (('np4m_paper','Flat lid at 512 m','#eb6834'),('np4m_paper_opentop','Open top at 512 m','#1baf7a'),('np4m_paper_lid','Lid 700 m above smoothed ground','#2a78d6')):
  mm=json.loads((scenes/f'windfarm_{k}/manifest.json').read_text());u=np.load(scenes/f'windfarm_{k}'/mm['files'][-1])[0,0].astype(np.float32)
  prof[k]=np.nanmedian(u,axis=0)
  fu=np.load(source_path('legacy_output',f'windfarm_neural/{k}/u_final.npy'),mmap_mode='r');flux[k]=[float(np.nansum(np.asarray(fu[:,:,i],dtype=np.float32))*g['cell_m']**2) for i in (2,fu.shape[2]//2,fu.shape[2]-8)];ax.plot(xs,prof[k],color=col,lw=2,label=lab)
 ax.set_xlabel('x (m), wind from left');ax.set_ylabel('Median u at 80 m AGL (m/s)');ax.legend(frameon=False)
 a2=ax.twinx();a2.plot(xs,gr.mean(0),color='#8a8a86',lw=1,ls='--');a2.set_ylabel('Mean ground height (m), dashed',color='#5a5a57');a2.grid(False)
 fig.savefig(out/'lid_comparison.png',dpi=130);plt.close(fig)
 idx=[0,len(xs)//2,len(xs)-8];summary['lid_comparison_volume_flux_m3_s']=flux;summary['lid_comparison_median_u80']={f'x={xs[i]:.0f}':{k:float(v[i]) for k,v in prof.items()} for i in idx};(out/'summary.json').write_text(json.dumps(summary,indent=1))
 print(json.dumps(summary['lid_comparison_median_u80'],indent=1))
