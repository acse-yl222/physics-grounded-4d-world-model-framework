import copy
import math
import unittest

from urban_geometry.visual_detail import build


class Object(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name


class Mesh:
    def __init__(self, name):
        self.name = name
        self.faces = []
        self.boxes = []

    def face(self, points, material):
        assert all(math.isfinite(value) for point in points for value in point)
        self.faces.append(points)

    def surface(self, parts, elevation, material):
        for part in parts:
            for triangle in part['triangles']:
                self.face([(*point, elevation) for point in triangle], material)

    def box(self, east, north, elevation, width, depth, height, material, angle=0):
        assert all(math.isfinite(value) for value in (east, north, elevation, width, depth, height, angle))
        assert min(width, depth, height) > 0
        self.boxes.append((east, north, elevation, width, depth, height))

    def done(self):
        return Object(self.name) if self.faces or self.boxes else None


class Context:
    def __init__(self):
        self.meshes = []

    def mesh(self, name):
        result = Mesh(name)
        self.meshes.append(result)
        return result

    def material(self, name, color, **kwargs):
        return name


class VisualDetailTests(unittest.TestCase):
    def feature(self, exposed=True):
        ring = [[0, 0], [12, 0], [12, 10], [0, 10]]
        return {'height_m': 9, 'height_basis': 'assumed', 'evidence_source_ids': ['mapped'],
                'geometry': [{'outer': ring, 'holes': [], 'triangles': [ring[:3], [ring[0], ring[2], ring[3]]]}],
                'visual_detail': {'profile': {'palette': 'cream', 'bay_pitch_m': 3,
                                              'window_width_m': 1.3, 'window_height_m': 1.5,
                                              'shade_depth_m': .3, 'parapet_height_m': .45},
                                  'floors': 3, 'parapets': [],
                                  'edges': [{'start': start, 'end': end, 'exposed': exposed, 'clearance_m': 3}
                                            for start, end in zip(ring, ring[1:] + ring[:1])]}}

    def test_all_elevations_get_physical_openings(self):
        feature = self.feature()
        original = copy.deepcopy(feature)
        context = Context()
        report = build(context, feature)
        self.assertEqual(feature, original)
        self.assertEqual(report['parameters']['openings'], 42)
        self.assertEqual(len(context.meshes[2].faces), 42)
        self.assertTrue(report['parameters']['artistic'])
        self.assertEqual(len(set(report['created'])), 3)

    def test_shared_edges_remain_closed(self):
        report = build(Context(), self.feature(False))
        self.assertEqual(report['parameters']['openings'], 0)

    def test_door_has_ground_level_glazing(self):
        feature = self.feature()
        feature['visual_detail']['edges'][0]['entrance'] = True
        context = Context()
        build(context, feature)
        self.assertTrue(any(min(point[2] for point in face) == 0 for face in context.meshes[2].faces))

    def test_lower_neighbour_does_not_hide_upper_floors(self):
        feature = self.feature(False)
        for edge in feature['visual_detail']['edges']:
            edge['blocked_height_m'] = 3
        report = build(Context(), feature)
        self.assertEqual(report['parameters']['openings'], 14)


if __name__ == '__main__':
    unittest.main()
