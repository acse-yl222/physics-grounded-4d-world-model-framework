"""Prepare a separate refinement candidate without replacing the delivered baseline."""
import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from urban_geometry.region_inventory import polygon_parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    scene = Path(__file__).resolve().parent
    source = scene / 'geometry/reconstruction_v2'
    output = args.output
    if output.exists():
        raise ValueError('Refusing to overwrite a candidate')
    output.mkdir(parents=True)
    for name in ['region.json', 'region.geojson', 'interfaces.json', 'inspection_views.json']:
        shutil.copy2(source / name, output / name)
    for name in ['src', 'references']:
        shutil.copytree(source / name, output / name, ignore=shutil.ignore_patterns('__pycache__'))
    data = json.loads((source / 'geometry.json').read_text())
    mapping = json.loads((source / 'src/modules.json').read_text())
    mapping['overture-6f706c10-772f-4b96-83f6-90024f62cfd1'] = 'directorate_refined'
    mapping['overture-cd979368-d9c0-4968-8072-59770a6b0f31'] = 'auditorium_refined'
    mapping['site-support'] = 'site_support_refined'
    projection = Transformer.from_crs('EPSG:4326', data['crs'], always_xy=True)
    document = ET.parse(scene / 'input/osm_20261005/map.osm.xml').getroot()
    nodes = {node.get('id'): projection.transform(float(node.get('lon')), float(node.get('lat')))
             for node in document.findall('node')}
    site = next(feature for feature in data['buildings'] if feature['id'] == 'site-support')
    domain = unary_union([Polygon(part['outer'], part['holes']) for part in site['geometry']])
    building_union = unary_union([Polygon(part['outer'], part['holes'])
                                 for feature in data['buildings'] if feature['kind'] == 'building'
                                 for part in feature['geometry']])
    details = []
    for way in document.findall('way'):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('tag')}
        refs = [node.get('ref') for node in way.findall('nd')]
        if len(refs) < 2 or any(ref not in nodes for ref in refs):
            continue
        coordinates = [nodes[ref] for ref in refs]
        geometry = None
        if tags.get('highway') in ('footway', 'pedestrian', 'path') and tags.get('covered') != 'yes':
            if tags.get('area') == 'yes' and refs[0] == refs[-1]:
                geometry = Polygon(coordinates)
            else:
                geometry = LineString(coordinates).buffer(.9, cap_style=2)
            material, color = 'mapped walking route; assumed finish', [.58, .55, .49]
        elif refs[0] == refs[-1] and len(refs) >= 4:
            if tags.get('leisure') == 'pitch' and tags.get('indoor') != 'yes' and 'Indoor' not in tags.get('name', ''):
                geometry = Polygon(coordinates)
                sport = tags.get('sport', 'unknown')
                material, color = 'mapped ' + sport + '; assumed finish', [.31, .42, .23]
                if sport in ('tennis', 'basketball', 'volleyball'):
                    color = [.48, .38, .29] if tags.get('surface') != 'concrete' else [.58, .57, .54]
                elif sport == 'multi':
                    color = [.52, .28, .20]
            elif tags.get('natural') == 'water':
                geometry = Polygon(coordinates)
                material, color = 'mapped water; unmeasured level', [.20, .32, .34]
        if geometry is None or not geometry.is_valid or not geometry.intersects(domain):
            continue
        geometry = geometry.intersection(domain).difference(building_union)
        if geometry.is_empty or geometry.area < .01:
            continue
        parts = polygon_parts(geometry)
        if not parts:
            continue
        details.append({'source_id': 'osm-way-' + way.get('id'),
                        'label': 'Mapped ' + tags.get('name', tags.get('highway', 'water')) + ' ' + way.get('id'),
                        'material': material, 'color': color, 'geometry': parts, 'source_tags': tags})
    site['surface_details'] = details
    occupied = Polygon()
    for surface in details:
        polygon = unary_union([Polygon(part['outer'], part['holes']) for part in surface['geometry']])
        surface['geometry'] = polygon_parts(polygon.difference(occupied))
        occupied = occupied.union(polygon)
    for category in ['roads', 'greens', 'geometry']:
        polygon = unary_union([Polygon(part['outer'], part['holes']) for part in site[category]])
        site[category] = polygon_parts(polygon.difference(occupied))
        occupied = occupied.union(polygon)
    (output / 'geometry.json').write_text(json.dumps(data, indent=2))
    (output / 'src/modules.json').write_text(json.dumps(mapping, indent=2))
    report = {'status': 'candidate_unverified', 'mapped_surface_count': len(details),
              'source_ids': [surface['source_id'] for surface in details],
              'limits': 'OSM surfaces and photo-informed landmark modules do not establish full-area architectural detail; satellite is context only.'}
    (output / 'candidate.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
