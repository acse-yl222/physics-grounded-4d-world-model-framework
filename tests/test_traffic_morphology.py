"""Conservation/support and development-only decision checks for screening."""
import copy
import unittest
import numpy as np
from urban_planning.traffic_morphology import aggregate, domain
from urban_planning.traffic_morphology_analysis import select_policies


class TrafficMorphologyTests(unittest.TestCase):
    def test_grid_refinement_preserves_source_and_receptor_area(self):
        blocked=np.zeros((8,8),dtype=bool);blocked[2:4,2:4]=True
        source=np.zeros((4,8,8));source[0,4,4]=1
        inputs={'x_roof4':blocked.astype(float)*16,'x_blocked4':blocked,'x_source4':source}
        cfg={'height_m':64,'source_layer_m':[0,8],'receptor_boundary_buffer_m':8}
        a=domain(inputs,'x',cfg,4,1);b=domain(inputs,'x',cfg,8,1.25)
        self.assertEqual(a[1].sum(),b[1].sum())
        self.assertEqual(a[2].sum()*16,b[2].sum()*64)
        self.assertFalse(np.any(a[1][:,~a[0]]))
        self.assertFalse(np.any(b[1][:,~b[0]]))
        np.testing.assert_allclose(aggregate(source,2,'sum').sum(axis=(1,2)),source.sum(axis=(1,2)))

    def test_development_objectives_differ_without_holdout(self):
        first={'source_sector_au_s':[1,4,2,3],'local_sector_means':[4,1,3,2],
               'plans':[{'plan':[0,1],'mean_reduction_fraction':.1},
                        {'plan':[2,3],'mean_reduction_fraction':.4}]}
        second=copy.deepcopy(first)
        second['plans'][0]['mean_reduction_fraction']=.6
        second['plans'][1]['mean_reduction_fraction']=.2
        untouched=copy.deepcopy([first,second]);policies=select_policies([first,second])
        self.assertEqual(policies['development_mean'],[0,1])
        self.assertEqual(policies['development_worst'],[2,3])
        self.assertEqual(policies['source_mass'],[1,3])
        self.assertEqual(policies['local_concentration'],[0,2])
        self.assertEqual([first,second],untouched)


if __name__=='__main__':unittest.main()
