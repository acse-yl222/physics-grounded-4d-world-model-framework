import json,tempfile,unittest
from pathlib import Path
import numpy as np
from urban_flow.paper_rotor.analyze_torch_farm import analyze

class StationarityTests(unittest.TestCase):
    def make(self,p,changes):
        (p/'data').mkdir()
        rows=[]
        for i,t in enumerate((100.,200.)):
            rows.append(dict(time_s=t,rotors=[dict(thrust_N=1.,disc_speed_m_s=1.)],full_domain_change_since_previous_sample=changes))
            np.save(p/f'data/frame-{i:04d}.npy',np.ones((1,3,2,2),dtype='f4'))
        (p/'history.json').write_text(json.dumps(rows))
    def test_constant_load_alone_does_not_certify_flow_stationarity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.make(p,{})
            self.assertFalse(analyze(p)['finite_window_stationarity_screen_passed'])
    def test_turbulence_drift_fails_despite_constant_velocity_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);changes={n:dict(rms_change=0.,relative_l2_change=0.) for n in ('u','v','w','k','epsilon')}
            changes['k']=dict(rms_change=.1,relative_l2_change=.1);self.make(p,changes)
            self.assertFalse(analyze(p)['finite_window_stationarity_screen_passed'])

if __name__=='__main__':unittest.main()
