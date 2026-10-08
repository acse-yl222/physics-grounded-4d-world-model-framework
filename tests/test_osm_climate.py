"""Coordinate and geometry invariants for the campus integration."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

try:
    from shapely.geometry import Polygon, box
    from urban_geometry.osm_scene import building_height, footprints, height_grid, mesh
    from urban_flow.scenarios.osm_climate import face_centres, restore_wind
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'OSM climate dependencies unavailable')
class OSMClimateTests(unittest.TestCase):
    def test_height_sources_remain_distinguishable(self):
        self.assertEqual(building_height({'height': '12 m', 'building:levels': '5'}, 9, 3), (12, 'osm_height'))
        self.assertEqual(building_height({'building:levels': '4'}, 9, 3), (12, 'osm_levels_times_assumed_floor_height'))
        self.assertEqual(building_height({'height': 'unknown'}, 9, 3), (9, 'assumed_unknown_height'))
        self.assertAlmostEqual(building_height({'height': '30 ft'}, 9, 3)[0], 9.144)

    def test_hole_is_preserved_in_grid_and_roof_mesh(self):
        polygon = Polygon([(-4, -4), (4, -4), (4, 4), (-4, 4)], holes=[[(-2, -2), (2, -2), (2, 2), (-2, 2)]])
        features = [{'geometry': polygon, 'height_m': 9}]
        roof = height_grid(features, 4, 1)
        self.assertTrue((roof[2:6, 2:6] == 0).all())
        self.assertEqual(np.count_nonzero(roof), 48)
        geometry = mesh(features, [-4, -4, 4, 4])
        positions = np.asarray(geometry['positions'])
        area = 0.
        for indices in geometry['triangles']:
            face = positions[indices]
            if np.all(face[:, 2] == 9):
                triangle = Polygon(face[:, :2])
                self.assertTrue(polygon.covers(triangle))
                area += triangle.area
        self.assertAlmostEqual(area, polygon.area)

    def test_grid_is_row_positive_north(self):
        roof = height_grid([{'geometry': box(0, 0, 4, 4), 'height_m': 12}], 4, 1)
        self.assertTrue((roof[4:, 4:] == 12).all())
        self.assertTrue((roof[:4] == 0).all())

    def test_cardinal_vectors_restore_to_enu(self):
        expected = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        for rotation, (east, north) in enumerate(expected):
            wind = np.zeros((3, 2, 4, 4), dtype=np.float32)
            wind[0] = 1
            restored = restore_wind(wind, rotation)
            np.testing.assert_allclose(restored[0], east)
            np.testing.assert_allclose(restored[1], north)
            np.testing.assert_allclose(restored[2], 0)
        wind = np.arange(3 * 2 * 4 * 4).reshape(3, 2, 4, 4).astype('f4')
        restored = wind
        for _ in range(4):
            restored = restore_wind(restored, 1)
        np.testing.assert_array_equal(restored, wind)

    def test_faces_use_inlet_and_closed_lateral_boundaries(self):
        faces = np.ones((3, 2, 4, 4), dtype=np.float32)
        result = face_centres(faces, np.full((2, 4), 3.))
        np.testing.assert_allclose(result[0, :, :, 0], 2.)
        np.testing.assert_allclose(result[1, :, 0, :], .5)
        np.testing.assert_allclose(result[2, 0], .5)

    def test_incomplete_outline_is_reported_not_invented(self):
        document = '<osm><node id="1" lon="0" lat="0"/><way id="2"><nd ref="1"/><nd ref="3"/><nd ref="1"/><tag k="building" v="yes"/></way></osm>'
        transform = {'lon0': 0, 'lat0': 0, 'metres_per_degree': 111320, 'R': [[1, 0], [0, 1]], 'scale': 1, 't': [0, 0]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'map.osm'
            path.write_text(document)
            features, skipped = footprints(path, transform)
        self.assertEqual(features, [])
        self.assertEqual(skipped[0]['id'], 'way/2')


if __name__ == '__main__':
    unittest.main()
