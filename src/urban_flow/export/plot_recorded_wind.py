"""Plot exact recorded horizontal wind slices; no simulated trajectories/interpolation."""
import argparse,json
from pathlib import Path
import numpy as np

def plot(raw,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    raw=Path(raw);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    metadata=json.loads((raw/'metadata.json').read_text());times=json.loads((raw/'sample_times_s.json').read_text());heights=json.loads((raw/'sample_heights.json').read_text())['actual_heights_m']
    velocity=np.load(raw/'velocity_samples.npy',mmap_mode='r');invalid=np.load(raw/'sample_invalid.npy');cell=metadata['cell_m'];ox,oy,_=metadata['origin_enu_m']
    x=ox+(np.arange(velocity.shape[-1])+.5)*cell;y=oy+(np.arange(velocity.shape[-2])+.5)*cell
    config=json.loads((raw/'configuration.json').read_text()) if (raw/'configuration.json').exists() else {}
    xmin,ymin,xmax,ymax=config.get('scene_bounds_xy_m',[-800,-550,620,620])
    selected=[int(np.argmin(abs(np.asarray(heights)-h)))for h in (20,60)]
    speeds=[np.linalg.norm(velocity[-1,:,i],axis=0)for i in selected]
    focus=(y[:,None]>=ymin)&(y[:,None]<=ymax)&(x[None,:]>=xmin)&(x[None,:]<=xmax)
    vmax=max(float(s[focus&~invalid[i].astype(bool)].max())for s,i in zip(speeds,selected))
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained');stats=[]
    for ax,idx,speed in zip(axes,selected,speeds):
        blocked=invalid[idx].astype(bool);field=np.ma.masked_where(blocked,speed)
        im=ax.imshow(field,origin='lower',extent=[ox,ox+len(x)*cell,oy,oy+len(y)*cell],vmin=0,vmax=vmax,cmap='viridis',interpolation='nearest')
        ax.imshow(np.ma.masked_where(~blocked,blocked),origin='lower',extent=[ox,ox+len(x)*cell,oy,oy+len(y)*cell],cmap='Greys',vmin=0,vmax=1,interpolation='nearest')
        xx,yy=np.meshgrid(x[::6],y[::6]);u=np.ma.masked_where(blocked[::6,::6],velocity[-1,0,idx,::6,::6]);v=np.ma.masked_where(blocked[::6,::6],velocity[-1,1,idx,::6,::6])
        ax.quiver(xx,yy,u,v,color='white',angles='xy',scale_units='xy',scale=.15,width=.0022,alpha=.8)
        ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),xlabel='East from scene origin (m)',ylabel='North from scene origin (m)',title=f'Actual cell-centre height: {heights[idx]:g} m');ax.set_aspect('equal')
        a=speed[focus&~blocked];stats.append({'height_m':heights[idx],'visible_fluid_speed_min_m_s':float(a.min()),'visible_fluid_speed_max_m_s':float(a.max()),'visible_fluid_speed_mean_m_s':float(a.mean())})
    fig.colorbar(im,ax=axes,label='3D wind speed (m/s)',shrink=.8)
    fig.suptitle(f'Canary Wharf | controlled west-to-east inflow {config.get("inlet_m_s",5):g} m/s | recorded t = {times[-1]:g} s\n{cell:g} m grid; arrows show horizontal velocity; black cells are modelled solids',fontsize=12)
    fig.savefig(out/'wind_slices.png',dpi=150);plt.close(fig)
    report={'recorded_time_s':times[-1],'samples':len(times),'heights':stats,'plot_uses_exact_final_recorded_values':True,'arrows':'Horizontal components of recorded three-dimensional velocity, sampled every6cells for display only','limitations':'Controlled coarse inviscid startup; not a weather prediction, pedestrian comfort assessment or converged steady solution.'}
    (out/'wind_plot_summary.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('raw');p.add_argument('out');a=p.parse_args();print(json.dumps(plot(a.raw,a.out),indent=2))
