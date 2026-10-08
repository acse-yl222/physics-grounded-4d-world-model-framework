import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from urban_planning.problem import Problem, write_json
from urban_planning.solar import panel_occlusion, reduced_energy
from urban_planning.tools import start_session, call_tool
from urban_planning.benchmark import run_policy


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.panel = dict(id='p00', x_m=0., y_m=0., z_m=2., width_m=2., depth_m=2., cost_units=1)
        phase = dict(max_panels=1, max_cost_units=1, max_winter_loss_fraction=.6,
                     excluded_ids=[], evaluation_budget=2)
        write_json(self.root/'task.json', {'candidates': [self.panel], 'phases': {'initial': phase}, 'seeds': [0]})
        arrays = {'receptors': np.array([[0., -2., 0.], [5., -2., 0.]])}
        for season in ('summer', 'winter'):
            for split in ('development', 'holdout'):
                prefix = f'{season}_{split}_'
                arrays[prefix+'direct_w_m2'] = np.ones((1, 2))*100
                arrays[prefix+'duration_s'] = np.array([3600.])
                arrays[prefix+'altitude_deg'] = np.array([45.])
                arrays[prefix+'azimuth_deg'] = np.array([0.])
        np.savez(self.root/'background.npz', **arrays)

    def test_ray_direction_and_height(self):
        # Sun north at 45 degrees: the shadow of a 2 m panel is 2 m south.
        r = np.array([[0., -2., 0.], [0., 2., 0.], [0., 0., 3.]])
        out = panel_occlusion(r, [self.panel], [45, -1], [0, 0])
        np.testing.assert_array_equal(out, [[True, False, False], [False, False, False]])

    def test_union_not_sum_and_energy_units(self):
        r = np.array([[0., -2., 0.]])
        shade = panel_occlusion(r, [self.panel, self.panel], [45], [0])
        np.testing.assert_allclose(reduced_energy(np.array([[1000.]]), [3600.], shade), [1.])

    def test_constraints_and_forbidden_site(self):
        p = Problem(self.root)
        for plan in (['unknown'], ['p00', 'p00'], ['p00', 'unknown']):
            self.assertFalse(p.evaluate(plan)['feasible'])
        p.task['phases']['initial']['excluded_ids'] = ['p00']
        self.assertFalse(p.evaluate(['p00'])['feasible'])

    def test_winter_constraint_evaluated(self):
        p = Problem(self.root)
        result = p.evaluate(['p00'])
        self.assertEqual(result['summer_reduction_fraction'], .5)
        p.task['phases']['initial']['max_winter_loss_fraction'] = .1
        self.assertFalse(p.evaluate(['p00'])['feasible'])

    def test_budget_invalid_and_duplicate_attempts_charged(self):
        start_session(self.root, 'test', 'initial', 'unit-test')
        for plan in (['unknown'], ['unknown']):
            call_tool(self.root, 'test', 'evaluate_plan', {'plan': plan})
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            call_tool(self.root, 'test', 'evaluate_plan', {'plan': []})

    def test_submission_closes_and_holdout_is_not_an_input(self):
        start_session(self.root, 'test', 'initial', 'unit-test')
        r = call_tool(self.root, 'test', 'evaluate_plan', {'plan': ['p00']})
        self.assertNotIn('holdout', r)
        result = call_tool(self.root, 'test', 'submit_plan', {'plan': ['p00']})
        self.assertIn('holdout', result)
        with self.assertRaisesRegex(ValueError, 'closed'):
            call_tool(self.root, 'test', 'evaluate_plan', {'plan': []})

    def test_input_tampering_rejected(self):
        start_session(self.root, 'test', 'initial', 'unit-test')
        with (self.root/'task.json').open('a') as f:
            f.write(' ')
        with self.assertRaisesRegex(ValueError, 'changed'):
            call_tool(self.root, 'test', 'inspect_history', {})

    def test_zero_background_no_nan_and_no_gain(self):
        p = Problem(self.root)
        p.arrays['summer_development_direct_w_m2'][:] = 0
        self.assertEqual(p.evaluate(['p00'])['summer_reduction_fraction'], 0)

    def test_baselines_respect_budget_and_find_single_site(self):
        p = Problem(self.root)
        for name in ('random_search', 'single_site_ranking', 'feasible_local_search', 'gp_constrained_ei'):
            result = run_policy(p, 'initial', name, 0)
            self.assertLessEqual(result['calls_used'], 2)
            self.assertEqual(result['development']['plan'], ['p00'])


if __name__ == '__main__':
    unittest.main()
