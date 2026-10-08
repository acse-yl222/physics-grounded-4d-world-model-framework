"""Sample actual aligned fields and render explicitly illustrative frozen-flow tracers.

Stages use separate Torch and pinned PyWake environments. Retain fields with the
movie so rendering never depends on the original solver scratch directory.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator

D = .4647
HUB = np.array([3.66, 3.5, .8])
NAMES = ['PyTorch SST', 'OpenFOAM SST', 'PyWake Jensen', 'PyWake Gaussian']

def cfd(out, checkpoint, case):
    import torch
    from .sample_foam_alignment import vector_field
    from common.export import digest
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((case/'configuration.json').read_text())
    n = np.array(cfg['grid_cells_xyz']); h = np.array(cfg['actual_spacing_xyz_m'])
    x = np.linspace(.05, 8, 320); y = np.linspace(-1.5, 1.5, 144)
    xx, yy = np.meshgrid(x, y)
    pos = np.stack([HUB[0]+xx*D, HUB[1]+yy*D, np.full_like(xx, HUB[2])], -1)
    axes = [(np.arange(ni)+.5)*hi for ni, hi in zip(n[::-1], h[::-1])]
    state = torch.load(checkpoint, map_location='cpu', weights_only=False)
    u = state['faces'][0].detach().cpu().numpy().squeeze()
    ux = .5*(u[..., :-1]+u[..., 1:])
    assert ux.shape == tuple(n[::-1]), ux.shape
    fields = [RegularGridInterpolator(axes, ux)(pos[..., ::-1])]
    centres = vector_field(case/'840/C'); velocity = vector_field(case/'840/U')
    idx = np.rint(centres/h-.5).astype(int)
    assert np.allclose(centres, (idx+.5)*h, atol=1e-8, rtol=0)
    assert (idx >= 0).all() and (idx < n).all()
    assert len(np.unique(idx[:, 0]+n[0]*(idx[:, 1]+n[1]*idx[:, 2]))) == np.prod(n)
    ux = np.empty(tuple(n[::-1])); ux[idx[:,2], idx[:,1], idx[:,0]] = velocity[:,0]
    fields.append(RegularGridInterpolator(axes, ux)(pos[..., ::-1]))
    np.savez_compressed(out/'cfd.npz', x=x, y=y, fields=np.array(fields))
    meta = {'U_inlet_m_s':10, 'D_m':D, 'hub_xyz_m':HUB.tolist(), 'Ct':.95,
            'sampling':'Trilinear cell-centred Ux at hub height; face Ux averaged for PyTorch',
            'torch_time_s':float(state['time_s'] if 'time_s' in state else state['time']),
            'openfoam_iteration':840, 'physical_transient_animation':False,
            'inputs':{str(p):digest(p) for p in [checkpoint, case/'840/U', case/'840/C',case/'configuration.json']}}
    (out/'provenance.json').write_text(json.dumps(meta, indent=2))

def pywake(out):
    from py_wake.site import UniformSite
    from py_wake.wind_turbines import WindTurbine
    from py_wake.wind_turbines.power_ct_functions import PowerCtTabular
    from py_wake.literature.noj import Jensen_1983
    from py_wake.literature.gaussian_models import Bastankhah_PorteAgel_2014
    from py_wake.deficit_models.utils import ct2a_mom1d
    from py_wake.flow_map import Points
    import py_wake
    a = np.load(out/'cfd.npz'); x, y = a['x'], a['y']; xx, yy = np.meshgrid(x, y)
    site = UniformSite([1], ti=.003, ws=10)
    turbine = WindTurbine('constant-Ct diagnostic', D, .8, PowerCtTabular([0,50],[0,0],'w',[.95,.95]))
    fields = list(a['fields'])
    for cls in [Jensen_1983, Bastankhah_PorteAgel_2014]:
        model = cls(site, turbine, k=.04, ct2a=ct2a_mom1d)
        result = model(x=[0], y=[0], wd=[270], ws=[10])
        field = result.flow_map(Points((xx*D).ravel(), (yy*D).ravel(), np.full(xx.size,.8))).WS_eff.values.squeeze().reshape(xx.shape)
        fields.append(field)
    fields = np.asarray(fields); assert np.isfinite(fields).all()
    np.savez_compressed(out/'fields.npz', x=x, y=y, fields=fields)
    meta = json.loads((out/'provenance.json').read_text())
    meta.update(pywake_version=py_wake.__version__, pywake_k=.04,
        gaussian_limit='Ct=0.95 exceeds width-formula Ct limit 0.899; amplitude clipping near rotor. Extrapolative diagnostic.',
        tracers='Identical initial positions; dx/dt=Ux, dy/dt=0. Streamwise indicators, not vector pathlines.',
        playback={'fps':24,'frames':288,'advection_seconds_per_video_second':.08,'seed':42})
    (out/'provenance.json').write_text(json.dumps(meta, indent=2))

def render(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    import imageio_ffmpeg
    matplotlib.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()
    a = np.load(out/'fields.npz'); x,y,fields = a['x'],a['y'],a['fields']
    fig, axes = plt.subplots(2,2,figsize=(14,7.6),dpi=120,sharex=True,sharey=True)
    fig.subplots_adjust(left=.055,right=.91,bottom=.14,top=.86,hspace=.31,wspace=.12)
    fig.suptitle('Aligned single-rotor wake comparison | Inlet 10 m/s | Ct = 0.95',fontsize=18,y=.97)
    fig.text(.5,.91,'Frozen hub-height fields; moving dots show streamwise speed only (not transient CFD)',ha='center',fontsize=12)
    rng = np.random.default_rng(42); initial = np.column_stack([rng.uniform(x[0],x[-1],240),rng.uniform(y[0],y[-1],240)])
    points = [initial.copy() for _ in fields]; artists=[]; interps=[]
    for ax, name, field, p in zip(axes.flat,NAMES,fields,points):
        im=ax.pcolormesh(x,y,field,cmap='viridis',vmin=0,vmax=11,shading='nearest',rasterized=True)
        ax.set_title(name,fontsize=14); ax.set_xlim(x[0],x[-1]);ax.set_ylim(y[0],y[-1])
        for station in [1,3,5]: ax.axvline(station,color='white',alpha=.25,lw=.7)
        artists.append(ax.scatter(p[:,0],p[:,1],s=4,c='white',alpha=.75,linewidths=0))
        interps.append(RegularGridInterpolator((y,x),field,bounds_error=True))
        ax.set_xlabel('Downstream distance x/D');ax.set_ylabel('Lateral offset y/D')
    fig.colorbar(im,cax=fig.add_axes([.935,.20,.014,.60]),label='Streamwise velocity Ux (m/s)')
    fig.text(.055,.057,'CFD: matched SST/upwind settings. PyWake: k = 0.04; no tunnel walls or annular rotor hole.',fontsize=10)
    fig.text(.055,.029,'Gaussian: Ct exceeds width-formula range; near-rotor amplitude clipping. Engineering diagnostic, not validated prediction.',fontsize=10)
    fig.savefig(out/'comparison_poster.png')
    writer=FFMpegWriter(fps=24,codec='libx264',extra_args=['-pix_fmt','yuv420p','-crf','20','-movflags','+faststart'])
    with writer.saving(fig,str(out/'comparison.mp4'),120):
        for frame in range(288):
            for p,artist,interp in zip(points,artists,interps):
                p[:,0] += interp(p[:,::-1])*(.08/24)/D
                p[:,0] = x[0] + np.mod(p[:,0]-x[0],x[-1]-x[0])
                artist.set_offsets(p)
            writer.grab_frame()
    plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['cfd','pywake','render']);p.add_argument('out',type=Path)
    p.add_argument('--checkpoint',type=Path);p.add_argument('--case',type=Path);a=p.parse_args()
    if a.stage=='cfd': cfd(a.out,a.checkpoint,a.case)
    else: globals()[a.stage](a.out)
