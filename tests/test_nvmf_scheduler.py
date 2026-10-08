"""The scheduler must work without external fixtures or flat package aliases."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from jsonschema import ValidationError

from uav_scheduling import schedule, validate_scenario
from uav_scheduling.__main__ import _publish_json

ROOT = Path(__file__).resolve().parents[1]


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads((ROOT / 'examples/nvmf/minimal_scenario.json').read_text())

    def test_uniform_control_closes_and_replays(self):
        with tempfile.TemporaryDirectory() as temp:
            result = schedule(self.scenario, backend='portable_fail_closed',
                              work_directory=Path(temp) / 'fresh')
        self.assertEqual(result['validation']['accepted'], 4)
        self.assertEqual(result['validation']['rejected'], 0)
        self.assertEqual(result['validation']['hard_violation_count'], 0)
        for key in ('committable', 'global_closure', 'independent_replay_pass', 'dry_run_equals_commit'):
            self.assertTrue(result['validation'][key])
        self.assertEqual(result['diagnostics']['mean_field_policy_consumed_count'], 0)
        self.assertEqual(result['diagnostics']['uniform_fail_closed_count'], 4)

    def test_strict_inputs_do_not_silently_truncate(self):
        for value in (1.5, True, '1', 1.0, float('nan'), float('inf'), 2**80):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.scenario)
                bad['travel_time_slots'][0][1] = value
                with self.assertRaises((ValueError, ValidationError)):
                    validate_scenario(bad)
        for value in (None, '', 17):
            bad = copy.deepcopy(self.scenario)
            bad['stations'][0]['id'] = value
            with self.assertRaises(ValidationError):
                validate_scenario(bad)

    def test_invalid_windows_or_unknown_station_rejected(self):
        for key, value in [('collection_station', 'missing'), ('dropoff_service_window', [12, 16])]:
            bad = copy.deepcopy(self.scenario)
            bad['requests'][0][key] = value
            with self.assertRaises(ValueError):
                validate_scenario(bad)

    def test_existing_work_and_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            with self.assertRaises(FileExistsError):
                schedule(self.scenario, backend='portable_fail_closed', work_directory=path)
            target = path / 'result.json'
            target.write_text('original')
            with self.assertRaises(FileExistsError):
                _publish_json(target, {'new': True})
            self.assertEqual(target.read_text(), 'original')
            self.assertEqual(list(path.iterdir()), [target])

    def test_array_order_does_not_change_assignments(self):
        reversed_scenario = copy.deepcopy(self.scenario)
        reversed_scenario['fleet'].reverse()
        reversed_scenario['requests'].reverse()
        with tempfile.TemporaryDirectory() as temp:
            a = schedule(self.scenario, backend='portable_fail_closed', run_seed=11,
                         work_directory=Path(temp) / 'a')
            b = schedule(reversed_scenario, backend='portable_fail_closed', run_seed=11,
                         work_directory=Path(temp) / 'b')
        self.assertEqual(a['assignments'], b['assignments'])

    def test_invalid_run_controls_rejected(self):
        for kwargs in ({'run_seed': True}, {'run_seed': -1}, {'max_rounds': 0},
                       {'max_rounds': 2.5}, {'backend': 'invented'}, {'device': 'mps'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                schedule(self.scenario, **kwargs)

    @unittest.skipUnless(os.environ.get('NVMF_RUN_MEAN_FIELD_TESTS') == '1'
                         and importlib.util.find_spec('torch'),
                         'Set NVMF_RUN_MEAN_FIELD_TESTS=1 with the scheduler extra')
    def test_actual_default_mean_field_solver_closes_and_replays(self):
        import torch
        previous = torch.get_num_threads()
        try:
            torch.set_num_threads(1)
            with tempfile.TemporaryDirectory() as temp:
                result = schedule(self.scenario, work_directory=Path(temp) / 'mean-field')
            self.assertEqual(result['diagnostics']['backend'], 'mean_field')
            self.assertEqual(result['validation']['accepted'], 4)
            self.assertEqual(result['validation']['hard_violation_count'], 0)
            self.assertTrue(result['validation']['global_closure'])
            self.assertTrue(result['validation']['independent_replay_pass'])
            self.assertTrue(result['validation']['dry_run_equals_commit'])
            self.assertFalse(result['evidence_scope']['q10000_claim_applies_to_this_run'])
        finally:
            torch.set_num_threads(previous)


if __name__ == '__main__':
    unittest.main()
