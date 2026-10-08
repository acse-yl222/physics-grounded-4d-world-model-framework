"""Single-rotor engineering-wake profiles; no power or CFD-equivalence claim."""
import json
import subprocess
from pathlib import Path
import numpy as np
import py_wake
from py_wake.site import UniformSite
from py_wake.wind_turbines import WindTurbine
from py_wake.wind_turbines.power_ct_functions import PowerCtTabular
from py_wake.literature.gaussian_models import Bastankhah_PorteAgel_2014
from py_wake.literature.noj import Jensen_1983
from py_wake.deficit_models.utils import ct2a_mom1d
from py_wake.flow_map import Points
from py_wake.rotor_avg_models import GridRotorAvg
from py_wake.superposition_models import SquaredSum
from common.storage import Storage
from common.runtime import trial_root
from common.export import write,digest
from common.provenance import snapshot_sources


def main():
    storage=Storage.load();config_path=storage.metadata('actuator_lab')/'configs/formal_wind_tunnel_mm2.json'
    c=json.loads(config_path.read_text());out=trial_root('actuator_lab','pywake_alignment');out.mkdir(parents=True)
    revision=snapshot_sources(storage.root,out/'source_snapshot.tar.gz')
    write(out/'configuration.json',c|{'pywake_version':py_wake.__version__,'ct2a':'momentum_1d','power_outputs':'discarded: zero placeholder curve','boundary_model':'UniformSite, no tunnel walls','wake_expansion_k':[.02,.04,.075]})
    write(out/'provenance.json',{'revision':revision,'config_sha256':digest(config_path),'source_snapshot_sha256':digest(out/'source_snapshot.tar.gz')})
    (out/'requirements-lock.txt').write_text(subprocess.check_output([str(Path(__import__('sys').executable)),'-m','pip','freeze'],text=True))
    D=c['rotor_diameter_m'];h=c['hub_xyz_m'][2];U=c['inlet_m_s'];rows=[]
    for model in [Jensen_1983,Bastankhah_PorteAgel_2014]:
        for ct,k in [(ct,.04) for ct in [0.,.6,.75,.95]]+[(.95,k) for k in [.02,.075]]:
            wt=WindTurbine('constant-Ct diagnostic',D,h,PowerCtTabular([0,50],[0,0],'w',[ct,ct]))
            wf=model(UniformSite([1],ti=c['turbulence_intensity'],ws=U),wt,k=k,ct2a=ct2a_mom1d)
            result=wf(x=[0],y=[0],wd=[270],ws=[U])
            for distance in [1,3,5,7,10]:
                y=np.linspace(-1.5*D,1.5*D,121)
                speed=result.flow_map(Points(np.full_like(y,distance*D),y,np.full_like(y,h))).WS_eff.values.squeeze()
                assert speed.shape==(121,) and np.isfinite(speed).all()
                if ct==0:assert np.allclose(speed,U,atol=1e-10)
                rows.append({'model':model.__name__,'ct':ct,'expansion_k':k,'x_over_D':distance,'y_over_R':(y/(D/2)).tolist(),'deficit':(1-speed/U).tolist()})
    write(out/'profiles.json',rows)
    pairs=[]
    for model in [Jensen_1983,Bastankhah_PorteAgel_2014]:
        wt=WindTurbine('constant-Ct diagnostic',D,h,PowerCtTabular([0,50],[0,0],'w',[.95,.95]))
        for resolution in (21,41,81):
            axis=(np.arange(resolution)+.5)*2/resolution-1
            xx,zz=np.meshgrid(axis,axis);inside=xx**2+zz**2<1
            avg=GridRotorAvg(xx[inside],zz[inside])
            wf=model(UniformSite([1],ti=c['turbulence_intensity'],ws=U),wt,k=.04,
                     ct2a=ct2a_mom1d,rotorAvgModel=avg,superpositionModel=SquaredSum())
            for separation in (3,5,7,10):
                for offset in (0,.5,1):
                    result=wf(x=[0,separation*D],y=[0,offset*D],wd=[270],ws=[U])
                    speeds=result.WS_eff.values.squeeze()
                    assert np.isfinite(speeds).all() and abs(speeds[0]-U)<1e-10
                    pairs.append(dict(model=model.__name__,separation_D=separation,offset_D=offset,
                                      quadrature_resolution=resolution,nodes=int(inside.sum()),
                                      upstream_m_s=float(speeds[0]),downstream_m_s=float(speeds[1])))
    write(out/'two_turbines.json',pairs)
    write(out/'status.json',{'state':'profiles_computed','zero_ct_test_passed':True,'experimental_accuracy_validated':False,'protocol_export_pending':True})
    print(out)

if __name__=='__main__':main()
