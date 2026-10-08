"""Prepare a reversible campus roof overlay on the preserved visual-detail model."""
import argparse
import json
import math
import shutil
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from urban_geometry.region_inventory import polygon_parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    scene = Path(__file__).resolve().parent
    source = scene / 'geometry/visual_study_20261008'
    output = args.output
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    for name in ['region.json', 'region.geojson', 'interfaces.json']:
        shutil.copy2(source / name, output / name)
    shutil.copytree(source / 'references', output / 'references')
    (output / 'src/buildings').mkdir(parents=True)
    for name in ['build_region.py', 'detailed_common.py']:
        shutil.copy2(source / 'src' / name, output / 'src' / name)
    (output / 'src/buildings/__init__.py').touch()
    shutil.copy2(scene.parents[1] / 'src/urban_geometry/roof_detail.py', output / 'src/buildings/roof_detail.py')
    data = json.loads((source / 'geometry.json').read_text())
    campus = set(json.loads((source / 'coverage.json').read_text())['campus_ids'])
    rows = []
    rooflight_count = 0
    for feature in data['buildings']:
        if feature['id'] not in campus or 'visual_detail' not in feature:
            continue
        outline = unary_union([Polygon(part['outer'], part['holes']) for part in feature['geometry']])
        interior = outline.buffer(-.30, join_style=2)
        if interior.is_empty:
            continue
        surface = interior.buffer(-.32, join_style=2)
        panels, walks, rooflights = [], [], []
        if not surface.is_empty:
            west, south, east, north = surface.bounds
            for column in range(math.floor(west / 6), math.ceil(east / 6)):
                for row in range(math.floor(south / 6), math.ceil(north / 6)):
                    panel = surface.intersection(box(column * 6 + .05, row * 6 + .05, (column + 1) * 6 - .05, (row + 1) * 6 - .05))
                    if not panel.is_empty:
                        panels.extend(polygon_parts(panel))
            if surface.area > 120:
                center = surface.centroid
                path = box(west, center.y - .4, east, center.y + .4) if east - west >= north - south else box(center.x - .4, south, center.x + .4, north)
                walks = polygon_parts(surface.intersection(path))
            if surface.area > 350:
                safe = surface.buffer(-2)
                for column in range(math.ceil(west / 12), math.floor(east / 12) + 1):
                    for row in range(math.ceil(south / 12), math.floor(north / 12) + 1):
                        center = [column * 12, row * 12]
                        housing = box(center[0] - .9, center[1] - 1.3, center[0] + .9, center[1] + 1.3)
                        if safe.covers(housing) and (not walks or housing.distance(path) > 1):
                            rooflights.append(center)
                            if len(rooflights) >= min(8, max(1, int(surface.area / 500))):
                                break
                    if len(rooflights) >= min(8, max(1, int(surface.area / 500))):
                        break
        rooflight_count += len(rooflights)
        rows.append({'id': feature['id'] + '-roof-detail', 'source_building_id': feature['id'],
                     'name': feature['name'] + ' estimated roof', 'kind': 'roof_overlay',
                     'evidence_source_ids': feature['evidence_source_ids'],
                     'roof_detail': {'roof_level_m': feature['height_m'] - feature['visual_detail']['profile']['parapet_height_m'],
                                     'drainage': polygon_parts(interior), 'panels': panels, 'walks': walks, 'rooflights': rooflights}})
    data['buildings'] = rows
    views = [{'id': 'roof_overview', 'target': [0, 0, 0], 'offset': [1200, -1600, 2200], 'scale': 1700}]
    original_views = json.loads((source / 'inspection_views.json').read_text())
    views.extend(view for view in original_views if view['id'] == 'library_front')
    mapping = {row['id']: 'roof_detail' for row in rows}
    report = {'scope': 'Artistic roof overlay on campus buildings; two photo-informed landmarks remain unchanged',
              'roof_buildings': len(rows), 'rooflights': rooflight_count,
              'source_building_ids': [row['source_building_id'] for row in rows],
              'existing_heights_and_outlines_unchanged': True, 'simulation_recomputed': False}
    for name, value in [('geometry.json', data), ('src/modules.json', mapping),
                        ('inspection_views.json', views), ('coverage.json', report)]:
        (output / name).write_text(json.dumps(value, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'source_building_ids'}))


if __name__ == '__main__':
    main()
