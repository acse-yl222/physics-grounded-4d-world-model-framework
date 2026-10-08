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

    def test_formal_uniform_anisotropic_grid_preserves_domain(self):
        config=json.loads((ROOT/'project/actuator_lab/configs/formal_wind_tunnel_mm2.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'formal'
            build_case(path,config,'kOmegaSST',2500,8)
            saved=json.loads((path/'configuration.json').read_text())
            self.assertEqual(saved['grid_cells_xyz'],[364,152,61])
            for length,count,spacing in zip([12,7,2],saved['grid_cells_xyz'],saved['actual_spacing_xyz_m']):
                self.assertAlmostEqual(count*spacing,length)
            self.assertIn('(364 152 61) simpleGrading (1 1 1)',(path/'system/blockMeshDict').read_text())
            self.assertEqual(saved['hub_xyz_m'],[3.66,3.5,.8])

    def test_no_finite_history_is_rejected(self):
        for log in ('', 'PAPER_ROTOR 1 nan 10 0\n', 'PAPER_ROTOR 1 10 10 0\nPAPER_ROTOR 1 10 10 0\n'):
            with self.assertRaises(ValueError):load_history(log)

    def test_limited_scheme_preserves_momentum_and_records_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'limited'
            build_case(path,self.config()|{'turbulence_advection':'limitedLinear'},'kOmegaSST',50)
            text=(path/'system/fvSchemes').read_text()
            self.assertIn('div(phi,U) bounded Gauss linearUpwind grad(U);',text)
            for field in ('k','epsilon','omega'):
                self.assertIn(f'div(phi,{field}) bounded Gauss limitedLinear 1;',text)
            self.assertEqual(json.loads((path/'configuration.json').read_text())['turbulence_advection'],'limitedLinear')

    def test_turbulence_scheme_diagnostic_preserves_momentum_scheme(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reference'
            build_case(path,self.config()|{'turbulence_advection':'linearUpwind'},'kOmegaSST',50)
            text=(path/'system/fvSchemes').read_text()
            for field in ('U','k','epsilon','omega'):
                self.assertIn(f'div(phi,{field}) bounded Gauss linearUpwind grad({field});',text)
            invalid=Path(directory)/'invalid'
            with self.assertRaises(ValueError):
                build_case(invalid,self.config()|{'turbulence_advection':'unknown'},'kOmegaSST',50)
            self.assertFalse(invalid.exists())

    def test_finished_but_unconverged_is_not_validation(self):
        log='PAPER_ROTOR 1 10 26.3658 0\n'
        log+='\n'.join(f'Solving for {field}, Initial residual = 0.1' for field in ['p','Ux','Uy','Uz','k','omega'])
        log+='\ntime step continuity errors : sum local = 0.001, global = 0.0001\nEnd\n'
        result,_=inspect_log(log,self.config())
        self.assertFalse(result['numerical_convergence_verified'])
        self.assertFalse(result['experimental_accuracy_validated'])
        with self.assertRaises(ValueError):inspect_log(log.removesuffix('End\n'),self.config())


    def test_lf18_checks_omega_residual_not_epsilon(self):
        config=self.config();config['turbulence_model']='paperSSTLF18'
        log=''.join(f'PAPER_ROTOR {i} 6 10 0\n' for i in range(1,101))
        log+='\n'.join(f'Solving for {field}, Initial residual = 1e-8' for field in ['p','Ux','Uy','Uz','k','omega'])
        log+='\ntime step continuity errors : sum local = 1e-10, global = 1e-11\nEnd\n'
        result,_=inspect_log(log,config)
        self.assertTrue(result['numerical_convergence_verified'])
        self.assertFalse(result['experimental_accuracy_validated'])


if __name__=='__main__':unittest.main()
