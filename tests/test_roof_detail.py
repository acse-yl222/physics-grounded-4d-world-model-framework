import copy
import unittest

from test_visual_detail import Context
from urban_geometry.roof_detail import build


class RoofDetailTests(unittest.TestCase):
    def feature(self):
        part = {'outer': [[0, 0], [10, 0], [10, 10], [0, 10]], 'holes': [],
                'triangles': [[[0, 0], [10, 0], [10, 10]], [[0, 0], [10, 10], [0, 10]]]}
        return {'source_building_id': 'mapped-building', 'evidence_source_ids': ['mapped'],
                'roof_detail': {'roof_level_m': 8.55, 'drainage': [part], 'panels': [part],
                                'walks': [], 'rooflights': [[5, 5]]}}

    def test_overlay_does_not_mutate_input(self):
        feature = self.feature()
        original = copy.deepcopy(feature)
        report = build(Context(), feature)
        self.assertEqual(feature, original)
        self.assertEqual(report['parameters']['rooflights'], 1)
        self.assertEqual(len(report['created']), 1)

    def test_roof_housings_stay_below_existing_parapet(self):
        context = Context()
        build(context, self.feature())
        for mesh in context.meshes:
            for _, _, elevation, _, _, height in mesh.boxes:
                self.assertLess(elevation + height / 2, 9)

    def test_small_roof_needs_no_housing(self):
        feature = self.feature()
        feature['roof_detail']['rooflights'] = []
        context = Context()
        report = build(context, feature)
        self.assertEqual(report['parameters']['rooflights'], 0)
        self.assertFalse(context.meshes[0].boxes)
        self.assertTrue(context.meshes[0].faces)


if __name__ == '__main__':
    unittest.main()
