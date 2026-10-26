"""Count-based traffic state estimates (DfT flows, assumed capacities)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic.corridor_sumo import count_state as cs


class CountStateTest(unittest.TestCase):
    def test_road_kind_and_lane_floor(self):
        self.assertEqual(cs.road_kind("A4", "highway.primary", 13.4), "a_road_signalised")
        self.assertEqual(cs.road_kind("A40", "highway.trunk", 22.2), "trunk_grade_separated")
        self.assertEqual(cs.road_kind("M4", "highway.motorway", 31.0), "motorway")
        self.assertEqual(cs.road_kind("U", "highway.residential", 8.9), "minor")
        self.assertEqual(cs.lanes_for("a_road_signalised", 1), 2)
        self.assertEqual(cs.lanes_for("minor", 1), 1)
        self.assertEqual(cs.lanes_for("motorway", 4), 4)

    def test_volume_capacity_classes(self):
        self.assertEqual(cs.classify(0.3), "free")
        self.assertEqual(cs.classify(0.6), "moderate")
        self.assertEqual(cs.classify(0.8), "heavy")
        self.assertEqual(cs.classify(1.2), "congested")

    def test_signalised_speed_falls_and_density_rises_with_flow(self):
        states = [
            cs.link_state(q, 1800, 13.4, 2, "a_road_signalised") for q in (200, 900, 1600, 2200)
        ]
        speeds = [s["v"] for s in states]
        self.assertEqual(speeds, sorted(speeds, reverse=True))
        self.assertLess(speeds[0], 13.4)  # signal delay even when quiet
        densities = [s["k"] for s in states]
        self.assertEqual(densities, sorted(densities))
        s = states[2]
        self.assertAlmostEqual(s["k"], s["q"] / (s["v"] * 3.6), delta=0.1)
        self.assertAlmostEqual(s["k_lane"], s["k"] / 2, delta=0.1)
        self.assertEqual(states[-1]["los"], "congested")

    def test_control_delay_matches_hcm_uniform_term_at_low_flow(self):
        # x -> 0: d1 = 0.5 C (1-g)^2 = 0.5 * 90 * 0.25 = 11.25 s, d2 -> 0.
        self.assertAlmostEqual(cs.control_delay_s(1e-6, 1800), 11.25, places=2)
        self.assertGreater(cs.control_delay_s(1.1, 1800), cs.control_delay_s(0.9, 1800))

    def test_grade_separated_roads_use_speed_ratio(self):
        # BPR keeps 91% of free speed at x = 0.91: free, although near capacity.
        self.assertEqual(cs.link_state(2900, 3200, 22.2, 2, "trunk_grade_separated")["los"], "free")
        # x = 1.3: v / v0 = 1 / (1 + 0.15 * 1.3^4) = 0.70.
        self.assertEqual(
            cs.link_state(4160, 3200, 22.2, 2, "trunk_grade_separated")["los"], "moderate"
        )


if __name__ == "__main__":
    unittest.main()
