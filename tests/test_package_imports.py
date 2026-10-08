"""Public modules must coexist without flat aliases or import-time output."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('scipy'),
                     'Install traffic and birds extras for package integration checks')
class PackageImportTests(unittest.TestCase):
    def run_isolated(self, script, *args):
        env = dict(os.environ)
        env.pop('P4D_ROOT', None)
        env.pop('UWM_ROOT', None)
        env.pop('PYTHONPATH', None)
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, '-I', '-c', script, str(ROOT / 'src'), *args],
                                    cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_coexisting_modules_have_one_identity_and_no_path_or_output_changes(self):
        self.run_isolated('''
import importlib, os, sys
sys.path.insert(0, sys.argv[1])
import torch, scipy
before = list(sys.path)
modules = [
    'traffic.train', 'traffic.evaluate', 'traffic.data.generate_complex',
    'traffic.verification.export_prediction',
    'urban_geometry.birds.sim.integrator', 'urban_geometry.birds.scripts.run_sim',
    'urban_flow.physics.wind.scaled_latent',
    'urban_flow.paper_rotor.compare', 'urban_flow.paper_rotor.render',
    'uav_routing.compute',
    'urban_flow.scenarios.actuator_lab.run', 'urban_flow.scenarios.windfarm_neural.run',
    'urban_flow.scenarios.windfarm_2m.run', 'common.pipeline.run_scene',
    'common.pipeline.scene_scaled_latent',
]
for name in modules:
    importlib.import_module(name)
from traffic.models.particle_mlp import ParticleTrafficModel
from traffic.train import ParticleTrafficModel as UsedModel
assert ParticleTrafficModel is UsedModel
from urban_flow.solvers.rotor import WeightedRotor
from urban_flow.paper_rotor.rotor import WeightedRotor as LegacyRotor
assert WeightedRotor is LegacyRotor
assert not any(name in sys.modules for name in ['configs', 'models', 'data', 'sim', 'rotor', 'mac_torch'])
assert sys.path == before, sys.path
assert not os.listdir('.'), os.listdir('.')
''')

    def test_direct_and_module_bird_help_work_outside_checkout(self):
        # Help must not require input data or instantiate the simulation configuration.
        self.run_isolated('''
import runpy, sys
sys.path.insert(0, sys.argv[1])
sys.argv = [sys.argv[2], '--help']
runpy.run_path(sys.argv[0], run_name='__main__')
''', str(ROOT / 'src/urban_geometry/birds/scripts/run_sim.py'))
        self.run_isolated('''
import runpy, sys
sys.path.insert(0, sys.argv[1])
sys.argv = ['birds', '--help']
runpy.run_module('urban_geometry.birds.scripts.run_sim', run_name='__main__')
''')

    def test_traffic_help_does_not_start_training(self):
        self.run_isolated('''
import runpy, sys
sys.path.insert(0, sys.argv[1])
sys.argv = ['traffic', '--help']
runpy.run_module('traffic.train', run_name='__main__')
''')


if __name__ == '__main__':
    unittest.main()
