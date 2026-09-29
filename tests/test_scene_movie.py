import unittest
import numpy as np
from urban_flow.paper_rotor.export_scene_movie import sample_grid

class SampleMappingTests(unittest.TestCase):
    def test_shuffled_cloud_and_missing_points_preserve_coordinates(self):
        ground=np.array([[1.,2.],[3.,4.]])
        rows=np.array([[6,6,84,9,0,0],[2,2,81,10,0,0]])
        grid=sample_grid(rows,ground,4,80)
        self.assertEqual(grid[0,0],10);self.assertEqual(grid[1,1],9)
        self.assertTrue(np.isnan(grid[0,1]))
    def test_duplicates_and_wrong_height_are_not_silently_accepted(self):
        ground=np.zeros((2,2));row=[2,2,80,10,0,0]
        for rows in ([row,row],[[2,2,90,10,0,0]]):
            with self.assertRaises(ValueError):sample_grid(rows,ground,4,80)
