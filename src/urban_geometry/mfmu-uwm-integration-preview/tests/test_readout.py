import unittest

import numpy as np

from bounded_studies.r3_global_mu_v3r4_batch_judge_v3 import readout


class ReadoutTest(unittest.TestCase):
    def test_clear_signal_qualifies(self):
        g = np.asarray([0.0, -1.0, -2.0, -3.0])
        q = readout.qualify_v2(
            g,
            g + 1e-13,
            g - 1e-13,
            g + 1e-13,
            g + 2e-13,
            np.zeros(4) + 1e-13,
            physical_response_pass=True,
            self_pin_free_pass=True,
        )
        self.assertTrue(q["QUALIFIED_G"])
        self.assertAlmostEqual(sum(q["p_G"]), 1.0)

    def test_uniform_signal_abstains(self):
        g = np.zeros(4)
        q = readout.qualify_v2(
            g, g, g, g, g, g,
            physical_response_pass=True,
            self_pin_free_pass=True,
        )
        self.assertFalse(q["QUALIFIED_G"])


if __name__ == "__main__":
    unittest.main()

