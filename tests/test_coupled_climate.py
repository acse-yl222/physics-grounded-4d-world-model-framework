import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from urban_planning.coupled_climate import ClimateProblem, BASE, face_centres
from urban_planning.climate_experiment import agent_episode, baseline_episode, gp_choice


class CoupledClimateTests(unittest.TestCase):
    def problem(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        cfg = {'cell_m': 8, 'receptor_boundary_buffer_m': 8, 'construction_budget': 6,
               'volume_ratio_min': .95, 'volume_ratio_max': 1.05,
               'max_sector_warming_c': .1, 'max_stagnant_increase': .05,
               'development_weather': [{'id': 'a'}, {'id': 'b'}], 'holdout_weather': [{'id': 'secret'}]}
        (root/'config.json').write_text(json.dumps(cfg))
        roof = np.zeros((16, 16)); roof[2:6, 2:6] = 24; roof[10:14, 10:14] = 24
        np.savez(root/'inputs.npz', south_ken_roof4=roof)
        with patch('common.pipeline.scene_temperature_physical.load_solver', return_value=(None, None)):
            return ClimateProblem(root)

    def test_volume_budget_and_fixed_footprints(self):
        problem = self.problem()
        self.assertFalse(problem.validate(BASE))
        self.assertTrue(problem.validate({'height_steps': [1, 0, 0, 0], 'cool_sectors': []}))
        self.assertTrue(problem.validate({'height_steps': [-1, 1, -1, 1], 'cool_sectors': [0, 1]}))
        plan = {'height_steps': [-1, 0, 0, 1], 'cool_sectors': [0]}
        self.assertFalse(problem.validate(plan))
        np.testing.assert_array_equal(problem.geometry(plan) > 0, problem.roof > 0)
        self.assertAlmostEqual(problem.geometry(plan).sum(), problem.roof.sum())

    def test_face_conversion_uses_inlet_and_impermeable_lower_faces(self):
        faces = [np.full((4, 4, 4), x) for x in (2., 4., 6.)]
        centre = face_centres(faces, np.full((4, 4), 10.))
        self.assertEqual(centre[0, 1, 1, 0], 6.)
        self.assertEqual(centre[0, 1, 1, 1], 2.)
        self.assertEqual(centre[1, 1, 0, 1], 2.)
        self.assertEqual(centre[2, 0, 1, 1], 3.)

    def test_quarter_turn_wind_directions_in_row_positive_north_grid(self):
        y, x = np.indices((8, 8))
        # Wind always travels toward increasing x in the rotated solver frame.
        # Its coordinate pulled back into ENU determines the actual wind direction.
        for rotation, expected_xy in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
            pulled_back = np.rot90(x.astype(float), -rotation)
            dy, dx = np.gradient(pulled_back)
            np.testing.assert_allclose(dx, expected_xy[0])
            np.testing.assert_allclose(dy, expected_xy[1])

    def test_worst_weather_and_local_harm_constraint(self):
        problem = self.problem(); calls = []
        def simulate(plan, weather):
            calls.append(weather['id']); baseline = plan == BASE
            return {'weather': weather['id'], 'p95_excess_c': 10 if baseline else (8 if weather['id'] == 'a' else 9),
                    'sector_mean_excess_c': [1., 1., 1., 1.] if baseline else [1.2, .5, .5, .5],
                    'stagnant_fraction': .1, 'mean_speed_m_s': 1., 'simulation_id': 'fixture'}
        problem.simulate = simulate
        result = problem.evaluate({'height_steps': [0]*4, 'cool_sectors': [0]})
        self.assertAlmostEqual(result['score'], .1)
        self.assertFalse(result['feasible'])  # Cooling cannot hide a harmed neighbourhood.
        self.assertNotIn('secret', calls)
        with self.assertRaises(ValueError): problem.evaluate(BASE, 'other')

    def test_invalid_plans_never_reach_physics(self):
        problem = self.problem()
        problem.simulate = lambda *_: self.fail('Invalid plan reached solver')
        result = problem.evaluate({'height_steps': [3, 0, 0, 0], 'cool_sectors': []})
        self.assertFalse(result['feasible'])

    def test_gp_returns_an_unseen_legal_choice_with_zero_variance_data(self):
        candidates = [{'height_steps': [0]*4, 'cool_sectors': [i]} for i in range(4)]
        observations = [{'plan': copy.deepcopy(BASE), 'score': 0., 'constraint': -1., 'feasible': True, 'cost_units': 0}]
        self.assertIn(gp_choice(observations, candidates), candidates)

    def episode_fixture(self, actions, cap):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        from types import SimpleNamespace
        def evaluate(plan):
            return {'plan': plan, 'feasible': plan['cool_sectors'] != [3],
                    'score': len(plan['cool_sectors']), 'cost_units': 2*len(plan['cool_sectors'])}
        problem = SimpleNamespace(cfg={'max_steps': len(actions), 'evaluation_budget': cap,
                                       'max_output_tokens': 100, 'model': 'fixture'},
                                  evaluate=evaluate, brief=lambda: {'fixture': True})
        iterator = iter(actions)
        provider = SimpleNamespace(
            complete=lambda *_: {'model_usage': {'fixture': {}}, 'action': next(iterator)},
            parse=lambda response: response['action'])
        return agent_episode(Path(temporary.name), problem, provider, 0)

    def test_invalid_query_is_charged_and_cap_cannot_be_bypassed(self):
        actions = [{'action': 'evaluate', 'plan': {'height_steps': [0]*4, 'cool_sectors': [3]}, 'reason': 'fixture'},
                   {'action': 'evaluate', 'plan': {'height_steps': [0]*4, 'cool_sectors': [0]}, 'reason': 'fixture'},
                   {'action': 'submit', 'plan': BASE, 'reason': 'fixture'}]
        result = self.episode_fixture(actions, 1)
        self.assertEqual(result['calls_used'], 1)
        self.assertEqual(result['development']['plan'], BASE)

    def test_unseen_submission_is_rejected_without_replacing_incumbent(self):
        evaluated = {'height_steps': [0]*4, 'cool_sectors': [0]}
        actions = [{'action': 'evaluate', 'plan': evaluated, 'reason': 'fixture'},
                   {'action': 'submit', 'plan': {'height_steps': [0]*4, 'cool_sectors': [1]}, 'reason': 'fixture'},
                   {'action': 'submit', 'plan': evaluated, 'reason': 'fixture'}]
        result = self.episode_fixture(actions, 2)
        self.assertTrue(result['submitted'])
        self.assertEqual(result['development']['plan'], evaluated)

    def test_material_control_respects_cap_and_never_changes_heights(self):
        from types import SimpleNamespace
        import itertools
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        pool = [{'height_steps': [0]*4, 'cool_sectors': list(c)} for n in range(3) for c in itertools.combinations(range(4), n)]
        pool.append({'height_steps': [-1, 1, 0, 0], 'cool_sectors': []})
        def evaluate(plan):
            self.assertEqual(plan['height_steps'], [0]*4)
            return {'plan': plan, 'feasible': True, 'score': len(plan['cool_sectors']), 'cost_units': 2*len(plan['cool_sectors'])}
        problem = SimpleNamespace(cfg={'evaluation_budget': 12}, evaluate=evaluate)
        result = baseline_episode(Path(temporary.name), problem, pool, 'materials_only', 0)
        self.assertEqual(result['calls_used'], 10)
        self.assertEqual(result['development']['score'], 2)


if __name__ == '__main__': unittest.main()
