import json
from pathlib import Path
import tempfile
import unittest
from urban_flow.paper_rotor.compare_three_way import compare,KEYS

class ComparisonGates(unittest.TestCase):
    def fixture(self,root):
        t=root/'torch';f=root/'foam';p=root/'pywake'
        for d in (t,f,p):d.mkdir()
        cfg={k:1 for k in KEYS}
        (t/'configuration.json').write_text(json.dumps(cfg|{'model':'kOmegaSST'}))
        (f/'configuration.json').write_text(json.dumps(cfg|{'turbulence_model':'kOmegaSST'}))
        (t/'status.json').write_text(json.dumps({'state':'running'}))
        return t,f,p
    def test_running_solver_is_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);t,f,p=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'still running'):compare(t,f,p,root/'out')
            self.assertFalse((root/'out').exists())
    def test_input_mismatch_is_not_interpolated_away(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);t,f,p=self.fixture(root)
            q=f/'configuration.json';cfg=json.loads(q.read_text());cfg['ct']=.75;q.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'parameter mismatch: ct'):compare(t,f,p,root/'out')
            self.assertFalse((root/'out').exists())
