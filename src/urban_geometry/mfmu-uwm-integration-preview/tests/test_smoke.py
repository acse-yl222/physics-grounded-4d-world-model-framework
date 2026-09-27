import copy
import json
import tempfile
import unittest
from pathlib import Path

from mfmu_scheduler import schedule
from mfmu_scheduler.scenario import ScenarioError, build_runtime


ROOT = Path(__file__).resolve().parents[1]


class SchedulerSmokeTest(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads((ROOT / "examples" / "minimal_scenario.json").read_text())

    def test_portable_controller_closes_and_replays(self):
        with tempfile.TemporaryDirectory() as work:
            result = schedule(self.scenario, run_seed=7, work_directory=work)
        self.assertEqual(result["validation"]["accepted"], 4)
        self.assertEqual(result["validation"]["rejected"], 0)
        self.assertEqual(result["validation"]["hard_violation_count"], 0)
        self.assertTrue(result["validation"]["global_closure"])
        self.assertTrue(result["validation"]["independent_replay_pass"])
        self.assertTrue(result["validation"]["dry_run_equals_commit"])
        self.assertEqual(result["diagnostics"]["mean_field_policy_consumed_count"], 0)
        self.assertEqual(result["diagnostics"]["uniform_fail_closed_count"], 4)

    def test_adapter_preserves_external_ids(self):
        fx, _auth, _policy, maps = build_runtime(self.scenario)
        self.assertEqual(fx["N"], 4)
        self.assertEqual(fx["M"], 4)
        self.assertEqual(maps.uav_external[0], "uav-01")
        self.assertEqual(maps.order_external[-1], "request-004")

    def test_rejects_non_frozen_dropoff_window(self):
        self.scenario["requests"][0]["dropoff_service_window"] = [12, 16]
        with self.assertRaises(ScenarioError):
            build_runtime(self.scenario)

    def test_uav_and_request_array_order_is_canonicalised(self):
        reordered = copy.deepcopy(self.scenario)
        reordered["fleet"].reverse()
        reordered["requests"].reverse()
        with tempfile.TemporaryDirectory() as work_a, tempfile.TemporaryDirectory() as work_b:
            result_a = schedule(self.scenario, run_seed=11, work_directory=work_a)
            result_b = schedule(reordered, run_seed=11, work_directory=work_b)
        self.assertEqual(result_a["assignments"], result_b["assignments"])


if __name__ == "__main__":
    unittest.main()
