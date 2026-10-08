"""Build a full mapped-campus artistic detail plan without replacing previous versions."""
import argparse
import hashlib
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, substring
from shapely.strtree import STRtree

from urban_geometry.region_inventory import polygon_parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', choices=['campus', 'study'], default='campus')
    args = parser.parse_args()
    scene = Path(__file__).resolve().parent
    source = scene / 'geometry/refinement_candidate_20261007_v2'
    output = args.output
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    for name in ['region.json', 'region.geojson', 'interfaces.json', 'inspection_views.json']:
        shutil.copy2(source / name, output / name)
    for name in ['src', 'references']:
        shutil.copytree(source / name, output / name, ignore=shutil.ignore_patterns('__pycache__'))
    kernel = scene.parents[1] / 'src/urban_geometry/visual_detail.py'
    shutil.copy2(kernel, output / 'src/buildings/visual_detail.py')
    shutil.copy2(kernel.with_name('visual_walkways.py'), output / 'src/buildings/visual_walkways.py')
    data = json.loads((source / 'geometry.json').read_text())
    mapping = json.loads((source / 'src/modules.json').read_text())
    document = ET.parse(scene / 'input/osm_20261005/map.osm.xml').getroot()
    projection = Transformer.from_crs('EPSG:4326', data['crs'], always_xy=True)
    nodes = {node.get('id'): projection.transform(float(node.get('lon')), float(node.get('lat')))
             for node in document.findall('node')}
    boundary = next(way for way in document.findall('way') if way.get('id') == '395256540')
    campus = Polygon([nodes[node.get('ref')] for node in boundary.findall('nd')])
    if not campus.is_valid:
        raise ValueError('Invalid mapped campus boundary')
    study = box(-1000, -1000, 1000, 1000)
    detail_boundary = study if args.scope == 'study' else campus
    buildings = [feature for feature in data['buildings'] if feature['kind'] == 'building']
    polygons = [unary_union([Polygon(part['outer'], part['holes']) for part in feature['geometry']]) for feature in buildings]
    tree = STRtree(polygons)
    overrides = {}
    for name in ['library_visual_profile.json', 'hall_visual_profile.json']:
        profile = json.loads((scene / 'configs' / name).read_text())
        overrides[profile.get('source_feature_id', profile.get('building_id'))] = profile
    selected = []
    campus_ids = []
    exterior_ids = []
    crossing_ids = []
    for index, (feature, geometry) in enumerate(zip(buildings, polygons)):
        if geometry.intersection(detail_boundary).area <= .01:
            continue
        selected.append(feature['id'])
        if geometry.intersection(campus).area > .01:
            campus_ids.append(feature['id'])
        else:
            exterior_ids.append(feature['id'])
        if not detail_boundary.covers(geometry):
            crossing_ids.append(feature['id'])
        if mapping[feature['id']] in ('directorate_refined', 'auditorium_refined'):
            continue
        digest = int(hashlib.sha256(feature['id'].encode()).hexdigest()[:8], 16)
        name = feature['name'].lower()
        palette = 'cream' if any(word in name for word in ['hall', 'hostel', 'residential']) else ['sandstone', 'cream', 'brick'][digest % 3]
        profile = {'palette': palette, 'bay_pitch_m': 2.6 + .2 * (digest % 4),
                   'window_width_m': 1.3, 'window_height_m': 1.45, 'shade_depth_m': .30,
                   'parapet_height_m': .45, 'floor_height_target_m': 3.0}
        override = overrides.get(feature['id'], {})
        profile.update({key: override[key] for key in profile if key in override})
        height = float(feature['height_m'])
        floors = max(1, round(height / profile['floor_height_target_m']))
        neighbour_indices = [int(other) for other in tree.query(geometry.buffer(3)) if int(other) != index]
        neighbours = [polygons[other] for other in neighbour_indices]
        neighbour_union = unary_union(neighbours)
        edges = []
        for part in feature['geometry']:
            polygon = orient(Polygon(part['outer'], part['holes']), sign=1)
            for ring_index, ring in enumerate([polygon.exterior, *polygon.interiors]):
                coordinates = list(ring.coords)
                for start, end in zip(coordinates, coordinates[1:]):
                    if math.dist(start, end) < .001:
                        continue
                    line = LineString([start, end])
                    cuts = {0.0, line.length}
                    for neighbour in neighbours:
                        overlap = line.intersection(neighbour.buffer(.25))
                        segments = [overlap] if overlap.geom_type == 'LineString' else list(getattr(overlap, 'geoms', []))
                        for segment in segments:
                            if segment.geom_type == 'LineString' and not segment.is_empty:
                                from shapely.geometry import Point
                                cuts.update(line.project(Point(point)) for point in [segment.coords[0], segment.coords[-1]])
                    ordered = sorted(cuts)
                    for lower, upper in zip(ordered, ordered[1:]):
                        if upper - lower < .001:
                            continue
                        first, second = line.interpolate(lower), line.interpolate(upper)
                        midpoint = line.interpolate((lower + upper) / 2)
                        blockers = [other for other in neighbour_indices if midpoint.distance(polygons[other]) < .251]
                        clearance = 3.0 if neighbour_union.is_empty else min(3.0, midpoint.distance(neighbour_union))
                        edges.append({'start': [first.x, first.y], 'end': [second.x, second.y], 'exposed': not blockers,
                                      'blocked_height_m': max([buildings[other]['height_m'] for other in blockers], default=0),
                                      'clearance_m': clearance, 'outer': ring_index == 0})
        eligible = [edge for edge in edges if edge['exposed'] and edge['outer'] and math.dist(edge['start'], edge['end']) > 3]
        if eligible:
            max(eligible, key=lambda edge: math.dist(edge['start'], edge['end']))['entrance'] = True
        parapets = geometry.difference(geometry.buffer(-.18, join_style=2))
        feature['visual_detail'] = {'profile': profile, 'floors': floors, 'edges': edges,
                                    'parapets': polygon_parts(parapets), 'status': 'artistic_not_surveyed'}
        feature['coverage_level'] = 'user_authorized_artistic_visual_detail'
        mapping[feature['id']] = 'visual_detail'
    building_union = unary_union(polygons)
    routes = []
    for way in document.findall('way'):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('tag')}
        refs = [node.get('ref') for node in way.findall('nd')]
        if tags.get('highway') not in ('footway', 'path') or len(refs) < 2 or any(ref not in nodes for ref in refs):
            continue
        line = LineString([nodes[ref] for ref in refs])
        if not 12 <= line.length <= 90 or not campus.covers(line) or line.distance(building_union) > 12:
            continue
        route = substring(line, 2, line.length - 2)
        canopy = route.buffer(1.0, cap_style=2, join_style=2)
        if canopy.intersects(building_union.buffer(.4)) or not campus.covers(canopy):
            continue
        if any(canopy.intersects(Polygon(part['outer'], part['holes'])) for prior in routes for part in prior['geometry']):
            continue
        posts = []
        for step in range(max(2, math.ceil(route.length / 5)) + 1):
            distance = route.length * step / max(2, math.ceil(route.length / 5))
            center = route.interpolate(distance)
            before, after = route.interpolate(max(0, distance - .1)), route.interpolate(min(route.length, distance + .1))
            length = before.distance(after)
            normal = [-(after.y - before.y) / length, (after.x - before.x) / length]
            for sign in (-1, 1):
                posts.append([center.x + normal[0] * .82 * sign, center.y + normal[1] * .82 * sign])
        routes.append({'source_id': 'osm-way-' + way.get('id'), 'geometry': polygon_parts(canopy), 'posts': posts})
    if routes:
        data['buildings'].append({'id': 'campus-shade-walks', 'name': 'Hypothetical campus shade walks',
                                 'kind': 'site', 'routes': routes, 'evidence_source_ids': ['osm_20261005']})
        mapping['campus-shade-walks'] = 'visual_walkways'
    views = json.loads((source / 'inspection_views.json').read_text())
    views.append({'id': 'campus_overview', 'target': [0, 0, 0], 'offset': [950, -1250, 1100], 'scale': 1750})
    for label, identity in [('library', 'overture-cf214e36-997b-4bcb-b49f-fbdd683fb55b'),
                            ('hostel', 'overture-7f4a1b64-57c1-430d-b02b-ae7e82629154')]:
        polygon = polygons[next(index for index, feature in enumerate(buildings) if feature['id'] == identity)]
        center = [polygon.centroid.x, polygon.centroid.y, 8]
        for side, offset in [('front', [60, -100, 65]), ('rear', [-60, 100, 65]), ('roof', [0, -1, 130])]:
            views.append({'id': label + '_' + side, 'target': center, 'offset': offset, 'scale': 160})
    if args.scope == 'study':
        views = [view for view in views if view['id'] in ('campus_overview', 'library_front')]
        views.append({'id': 'study_overview', 'target': [0, 0, 0], 'offset': [1500, -1800, 1550], 'scale': 2900})
        for label, target in [('north', [0, 740, 5]), ('east', [840, 0, 5]),
                              ('south', [100, -730, 5]), ('west', [-840, 0, 5])]:
            views.append({'id': 'periphery_' + label, 'target': target, 'offset': [90, -140, 110], 'scale': 370})
        exterior_set = set(exterior_ids)
        exterior_index = min((index for index, feature in enumerate(buildings) if feature['id'] in exterior_set),
                             key=lambda index: polygons[index].centroid.distance(LineString([(0, 740), (1, 740)])))
        center = polygons[exterior_index].centroid
        for label, offset in [('front', [35, -50, 27]), ('rear', [-35, 50, 27]), ('roof', [0, -1, 80])]:
            views.append({'id': 'exterior_' + label, 'target': [center.x, center.y, 3], 'offset': offset, 'scale': 85})
        for view in views:
            if view['id'].startswith(('periphery_', 'exterior_')):
                factor = max(1, 3 * view['scale'] / math.sqrt(sum(value ** 2 for value in view['offset'])))
                view['offset'] = [value * factor for value in view['offset']]
    report = {'scope': ('All mapped building footprints intersecting the 2000 m square study area; full crossing footprints retained; outer simulation buffer unchanged' if args.scope == 'study' else 'All mapped building footprints intersecting OSM university way 395256540; surrounding context unchanged'),
              'detail_scope': args.scope, 'detailed_buildings': len(selected), 'detailed_ids': selected,
              'exterior_buildings': len(exterior_ids), 'exterior_ids': exterior_ids,
              'boundary_crossing_ids': crossing_ids,
              'campus_area_m2': campus.area, 'campus_buildings': len(campus_ids), 'campus_ids': campus_ids,
              'new_artistic_buildings': sum(mapping[identity] == 'visual_detail' for identity in selected),
              'hypothetical_shaded_routes': len(routes),
              'existing_photo_informed_buildings': sum(mapping[identity] != 'visual_detail' for identity in selected),
              'status': 'prepared_not_yet_verified', 'simulation_recomputed': False,
              'limitations': 'User-approved artistic facade/floor/roof completion, not a measured digital twin. No satellite-derived facade detail.'}
    for name, value in [('geometry.json', data), ('src/modules.json', mapping), ('inspection_views.json', views),
                        ('coverage.json', report), ('campus_boundary.json', campus.__geo_interface__)]:
        (output / name).write_text(json.dumps(value, indent=2))
    print(json.dumps({key: value for key, value in report.items() if not key.endswith('_ids')}, indent=2))


if __name__ == '__main__':
    main()
