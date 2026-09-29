import unittest
import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from urban_flow.paper_rotor.scene_diagnostics import loads, analyze

class PhysicalTimeLoadsTests(unittest.TestCase):
    def test_corrector_duplicates_keep_final_evaluation(self):
        log='FARM_ROTOR 0 0.1 8 20 0\nFARM_ROTOR 1 0.1 7 15 0\nFARM_ROTOR 0 0.1 7.9 19 0\nFARM_ROTOR 1 0.1 6.9 14 0\n'
        result=loads(log,1.225,2)
        self.assertEqual(result['times'],[.1])
        self.assertEqual(result['thrust_N'],[[19,14]])
    def test_missing_rotor_and_time_reversal_are_rejected(self):
        for log in ('FARM_ROTOR 0 0.1 8 20 0\n',
                    'FARM_ROTOR 0 0.2 8 20 0\nFARM_ROTOR 1 0.1 8 20 0\n'):
            with self.assertRaises(ValueError):loads(log,1.225,2)

    def test_completed_run_still_requires_stability_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            case=Path(directory)
            (case/'configuration.json').write_text(json.dumps({'time_semantics':'physical seconds','rho_kg_m3':1.225,'target_seconds':2.}))
            (case/'status.json').write_text(json.dumps({'state':'transient_finished'}))
            rotor=''.join(f'FARM_ROTOR {i} 2 8 20 0\n' for i in range(23))
            for courant,expected in ((.4,True),(.7,False)):
                (case/'log.pimpleFoam').write_text(rotor+f'Courant Number mean: 0.1 max: {courant}\n'
                    +'time step continuity errors : sum local = 1e-8, global = 1e-9, cumulative = 1e-8\nEnd\n')
                with redirect_stdout(StringIO()):result=analyze(case)
                self.assertEqual(result['numerical_smoke_checks_passed'],expected)
                self.assertFalse(result['experimental_accuracy_validated'])
