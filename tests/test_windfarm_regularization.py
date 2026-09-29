import unittest
import numpy as np
from urban_flow.paper_rotor.prepare_windfarm import regularize_fluid

class GeometryRegularizationTests(unittest.TestCase):
    def test_resolved_domain_is_preserved(self):
        original=np.zeros((3,4,5),dtype=bool)
        result,removed=regularize_fluid(original)
        self.assertTrue(np.array_equal(result,original))
        self.assertFalse(removed.any())

    def test_single_cell_slit_is_recorded_without_mutating_source(self):
        original=np.ones((6,6,6),dtype=bool)
        original[1:4,1:4,1:4]=False
        original[2,2,4]=False
        backup=original.copy()
        result,removed=regularize_fluid(original)
        self.assertTrue(np.array_equal(original,backup))
        self.assertEqual(int(removed.sum()),1)
        self.assertTrue(removed[2,2,4])
        self.assertTrue(np.array_equal(result,original|removed))
        self.assertFalse(regularize_fluid(result)[1].any())
