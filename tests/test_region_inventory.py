"""Projection, hole preservation and inventory scope regressions."""
import json
from pathlib import Path
import tempfile
import unittest

try:
    from pyproj import Transformer
    from shapely.geometry import Polygon, MultiPolygon, box
    from urban_geometry.region_inventory import polygon_parts, prepare
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Install requirements-region-inventory.txt')
class RegionInventoryTests(unittest.TestCase):
    def test_concavity_holes_and_disjoint_parts(self):
        polygon = Polygon([(0, 0), (8, 0), (8, 8), (5, 8), (5, 6), (0, 6)],
                          holes=[[(1, 1), (3, 1), (3, 3), (1, 3)]])
        geometry = MultiPolygon([polygon, box(10, 0, 12, 2)])
        parts = polygon_parts(geometry)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0]['holes']), 1)
        triangles = [Polygon(triangle) for part in parts for triangle in part['triangles']]
        self.assertAlmostEqual(sum(triangle.area for triangle in triangles), geometry.area)
        self.assertTrue(all(geometry.covers(triangle) for triangle in triangles))

    def test_projection_and_open_air_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'region.json').write_text(json.dumps({'bbox_wgs84': [76.35, 30.34, 76.38, 30.37]}))
            overture = root / 'overture.json'
            coordinates = [[76.36, 30.35], [76.3601, 30.35], [76.3601, 30.3501], [76.36, 30.3501], [76.36, 30.35]]
            overture.write_text(json.dumps({'features': [
                {'id': 'building', 'geometry': {'type': 'Polygon', 'coordinates': [coordinates]}, 'properties': {'height': 12}},
                {'id': 'theatre', 'geometry': {'type': 'Polygon', 'coordinates': [coordinates]},
                 'properties': {'names': {'primary': 'OAT Open Air Theatre'}}}]}))
            osm = root / 'map.osm'
            osm.write_text('<osm>' + ''.join(f'<node id="{index}" lon="{point[0]}" lat="{point[1]}"/>'
                for index, point in enumerate(coordinates[:-1])) + '<way id="5">' +
                ''.join(f'<nd ref="{index}"/>' for index in [0, 1, 2, 3, 0]) +
                '<tag k="building" v="yes"/><tag k="name" v="OAT Open Air Theatre"/></way></osm>')
            prepare(root, overture, osm, 76.36621, 30.35447)
            inventory = json.loads((root / 'geometry.json').read_text())
            self.assertEqual([row['id'] for row in inventory['buildings']], ['overture-building', 'site-support'])
            row = inventory['buildings'][0]
            self.assertEqual(row['height_basis'], 'overture_source_reported_height')
            projection = Transformer.from_crs('EPSG:4326', inventory['crs'], always_xy=True)
            self.assertAlmostEqual(projection.transform(76.36621, 30.35447)[0], 0, places=6)
            self.assertAlmostEqual(projection.transform(76.36621, 30.35447)[1], 0, places=6)
            self.assertEqual(row['geometry'][0]['outer'][0], list(projection.transform(*coordinates[0])))


if __name__ == '__main__':
    unittest.main()
