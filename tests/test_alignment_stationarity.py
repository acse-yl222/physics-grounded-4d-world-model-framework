import json
from pathlib import Path
import tempfile
import unittest
from urban_flow.paper_rotor.audit_alignment_stationarity import audit

class StationarityTests(unittest.TestCase):
    def fixture(self,root,drift=0):
        rows=[]
        for i in range(13):
            t=i*.1;rows.append({'time_s':t,'thrust_N':10})
            for d in (1,3,5):
                p=root/f'diagnostics/step_{i:07d}/data';p.mkdir(parents=True,exist_ok=True)
                (p/f'wake_{d}d.json').write_text(json.dumps({'time_s':t,'positions':[[d,0,0],[d,1,0]],'values':[.5+drift*t,.4]}))
        (root/'history.json').write_text(json.dumps(rows))
    def test_constant_profiles_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);self.assertTrue(audit(root)['finite_window_passed'])
    def test_stable_thrust_does_not_hide_wake_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root,.01);self.assertFalse(audit(root)['finite_window_passed'])
    def test_short_window_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);self.assertFalse(audit(root,2.4)['finite_window_passed'])
