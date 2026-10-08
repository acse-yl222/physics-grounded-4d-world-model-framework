import copy
import unittest
from urban_planning.active_validation import Trial, BASE, SEED


class FakeProblem:
    def __init__(self):
        self.cfg = {'development_weather': [{'id': str(i)} for i in range(4)], 'evaluation_budget': 4}
        self.baselines = {'sentinel': True}
    def validate(self, plan):
        return ['bad'] if plan.get('bad') else []
    def evaluate(self, plan):
        scenario = self.cfg['development_weather'][0]['id']
        fail = plan == SEED and scenario == '2'
        return {'plan': plan, 'feasible': not fail, 'constraint': 1. if fail else -1.,
                'score': .1, 'weather': [{'weather': scenario}]}


class ActiveValidationTests(unittest.TestCase):
    def test_partial_evidence_cannot_be_submitted(self):
        trial = Trial(FakeProblem())
        self.assertFalse(trial.result(SEED)['complete'])
        self.assertFalse(trial.result(SEED)['feasible'])
        trial.query(SEED, ['2', '3'])
        self.assertTrue(trial.result(SEED)['complete'])
        self.assertFalse(trial.result(SEED)['feasible'])
        self.assertTrue(trial.result(BASE)['feasible'])

    def test_budget_charges_duplicates_and_invalid_plans(self):
        trial = Trial(FakeProblem())
        trial.query(BASE, ['0']); trial.query(BASE, ['0'])
        trial.query({'bad': True}, ['0', '1'])
        self.assertEqual(trial.used, 4)
        with self.assertRaises(ValueError): trial.query(BASE, ['0'])

    def test_private_weather_inaccessible(self):
        trial = Trial(FakeProblem())
        for ids in ([], ['final_west'], ['0', '0']):
            with self.assertRaises(ValueError): trial.query(BASE, ids)
        self.assertEqual(trial.used, 0)

    def test_evaluation_restores_configuration(self):
        problem = FakeProblem(); before = copy.deepcopy(problem.cfg)
        trial = Trial(problem); trial.query(SEED, ['2'])
        self.assertEqual(problem.cfg, before)
        self.assertEqual(problem.baselines, {'sentinel': True})


if __name__ == '__main__': unittest.main()
