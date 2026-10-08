import unittest
from urban_flow.paper_rotor.scene_parameters import rotor_parameters

class ScalingTests(unittest.TestCase):
    def test_paper_ratios_recover_original_rotor(self):
        config={'sigma_over_diameter':.02/.4647,'inner_diameter_ratio':.09/.4647,'cutoff_sigma':2}
        p=rotor_parameters(config,.4647/2)
        self.assertAlmostEqual(p['sigma_m'],.02)
        self.assertAlmostEqual(p['inner_radius_m'],.045)
        self.assertAlmostEqual(p['thickness_m'],.08)
        full=rotor_parameters(config,41.)
        self.assertAlmostEqual(full['thickness_m']/82.,.08/.4647)
    def test_legacy_parameters_are_preserved(self):
        self.assertEqual(rotor_parameters({'sigma_m':8.,'cutoff_sigma':2},41.),dict(sigma_m=8.,inner_radius_m=0.,thickness_m=32.))
    def test_invalid_hole_is_rejected(self):
        with self.assertRaises(ValueError):rotor_parameters({'sigma_m':1.,'cutoff_sigma':2,'inner_diameter_ratio':1},2.)
