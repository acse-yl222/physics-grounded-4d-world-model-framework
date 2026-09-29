"""Reference workflow gates: never confuse solver exit or iteration with validation."""
import json
from pathlib import Path
import tempfile
import unittest

from urban_flow.paper_rotor.openfoam_reference import build_case, rotor_source
from urban_flow.paper_rotor.analyze_reference import inspect_log, load_history

ROOT=Path(__file__).resolve().parents[1]


class ReferenceTests(unittest.TestCase):
    def config(self):
        value=json.loads((ROOT/'project/actuator_lab/configs/paper_rotor_10ms.json').read_text())
        return value|{'kinematic_viscosity_m2_s':1.5e-5,'turbulence_intensity':.01,
                      'turbulence_length_m':.03,'turbulence_model':'kOmegaSST'}

    def test_reference_conditions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reference'
            build_case(path,self.config(),'kOmegaSST',50,4)
            self.assertIn('type noSlip;', (path/'0/U').read_text())
            self.assertIn('type omegaWallFunction;', (path/'0/omega').read_text())
            self.assertIn('RASModel kOmegaSST;', (path/'constant/turbulenceProperties').read_text())
            self.assertIn('steady SIMPLE iteration',json.loads((path/'configuration.json').read_text())['time_semantics'])
            with self.assertRaises(FileExistsError):
                build_case(path,self.config(),'kOmegaSST',50)

    def test_invalid_configuration_does_not_create_case(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reference'
            for patch in ({'cell_m':.03},{'turbulence_intensity':0},{'ct':1.2},{'cutoff_sigma':3}):
                with self.assertRaises(ValueError):
                    build_case(path,self.config()|patch,'kOmegaSST',50)
                self.assertFalse(path.exists())

    def test_no_finite_history_is_rejected(self):
        for log in ('', 'PAPER_ROTOR 1 nan 10 0\n', 'PAPER_ROTOR 1 10 10 0\nPAPER_ROTOR 1 10 10 0\n'):
            with self.assertRaises(ValueError):load_history(log)

    def test_finished_but_unconverged_is_not_validation(self):
        log='PAPER_ROTOR 1 10 26.3658 0\n'
        log+='\n'.join(f'Solving for {field}, Initial residual = 0.1' for field in ['p','Ux','Uy','Uz','k','omega'])
        log+='\ntime step continuity errors : sum local = 0.001, global = 0.0001\nEnd\n'
        result,_=inspect_log(log,self.config())
        self.assertFalse(result['numerical_convergence_verified'])
        self.assertFalse(result['experimental_accuracy_validated'])
        with self.assertRaises(ValueError):inspect_log(log.removesuffix('End\n'),self.config())


if __name__=='__main__':unittest.main()
