"""Prepare a projected, triangulated Overture/OSM inventory for region authoring."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import mapbox_earcut
import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, LineString, box, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from urban_geometry.osm_scene import footprints


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def polygon_parts(geometry):
    polygons = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
    result = []
    for polygon in polygons:
        if polygon.geom_type != 'Polygon' or polygon.area < 1e-8:
            continue
        rings = [np.asarray(ring.coords[:-1], dtype=np.float64) for ring in [polygon.exterior, *polygon.interiors]]
        vertices = np.concatenate(rings)
        ends = np.cumsum([len(ring) for ring in rings], dtype=np.uint32)
        indices = mapbox_earcut.triangulate_float64(vertices, ends).reshape(-1, 3)
        triangles = vertices[indices]
        area = sum(Polygon(triangle).area for triangle in triangles)
        if not np.isclose(area, polygon.area, rtol=1e-8, atol=1e-6):
            raise ValueError('Triangulation changed polygon area')
        result.append({'outer': rings[0].tolist(), 'holes': [ring.tolist() for ring in rings[1:]],
                       'triangles': triangles.tolist()})
    return result


def prepare(root, overture, osm, longitude, latitude, half_width=1536, exclusions=None):
    exclusions = exclusions or {}
    region = json.loads((root / 'region.json').read_text())
    crs = CRS.from_proj4(f'+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m +no_defs')
    projection = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    domain = box(-half_width, -half_width, half_width, half_width)
    focus = transform(projection.transform, box(*region['bbox_wgs84']))
    def project(points):
        coordinates = np.asarray(points)
        return np.column_stack(projection.transform(coordinates[:, 0], coordinates[:, 1]))
    osm_rows, rejected = footprints(osm, {}, project=project)
    osm_by_id = {row['id']: row for row in osm_rows}
    rows, polygons, excluded, seen = [], [], [], set()
    for source in json.loads(overture.read_text())['features']:
        properties = source['properties']
        identity = 'overture-' + source['id']
        if identity in exclusions:
            excluded.append({'id': identity, 'reason': exclusions[identity]})
            continue
        geometry = transform(projection.transform, shape(source['geometry']))
        if properties.get('is_underground') or not geometry.intersects(domain):
            continue
        if identity in seen or not geometry.is_valid or geometry.is_empty:
            excluded.append({'id': identity, 'reason': 'duplicate ID or invalid geometry'})
            continue
        seen.add(identity)
        name = (properties.get('names') or {}).get('primary') or identity
        if name == 'OAT Open Air Theatre':
            excluded.append({'id': identity, 'reason': 'mapped open-air theatre, not an enclosed building'})
            continue
        sources = properties.get('sources', [])
        tags = {}
        for evidence in sources:
            record = evidence.get('record_id') or ''
            match = re.fullmatch(r'([wr])(\d+)@\d+', record)
            if match:
                record = ('way/' if match[1] == 'w' else 'relation/') + match[2]
            for prefix in ('https://www.openstreetmap.org/', 'https://openstreetmap.org/'):
                record = record.removeprefix(prefix)
            if record in osm_by_id:
                tags = osm_by_id[record]['tags']
        height = properties.get('height')
        floors = properties.get('num_floors')
        basis = 'overture_source_reported_height'
        if not height and floors:
            height, basis = float(floors) * 3, 'source_floor_count_times_assumed_3m'
        if not height:
            from urban_geometry.osm_scene import building_height
            height, basis = building_height(tags, 9, 3)
        rows.append({'id': identity, 'name': name, 'geometry': polygon_parts(geometry),
                     'height_m': float(height), 'height_basis': basis, 'source_properties': properties,
                     'osm_tags': tags, 'kind': 'building', 'in_focus': geometry.intersects(focus),
                     'boundary_crossing': geometry.intersects(focus) and not focus.covers(geometry),
                     'detail_parameters': {}, 'evidence_source_ids': ['overture_20260923'],
                     'coverage_level': 'mapped_footprint_assumed_exterior'})
        polygons.append(geometry)
    tree = STRtree(polygons)
    additions = 0
    for source in osm_rows:
        geometry = source['geometry']
        if 'osm-' + source['id'].replace('/', '-') in exclusions:
            continue
        if source['tags'].get('name') == 'OAT Open Air Theatre':
            continue
        if not geometry.intersects(domain):
            continue
        overlaps = [polygons[int(index)] for index in tree.query(geometry, predicate='intersects')]
        if overlaps and geometry.intersection(unary_union(overlaps)).area / geometry.area > .5:
            continue
        rows.append({'id': 'osm-' + source['id'].replace('/', '-'), 'name': source['tags'].get('name', source['id']),
                     'geometry': polygon_parts(geometry), 'height_m': source['height_m'],
                     'height_basis': source['height_basis'], 'osm_tags': source['tags'], 'kind': 'building',
                     'in_focus': geometry.intersects(focus), 'boundary_crossing': not focus.covers(geometry),
                     'detail_parameters': {}, 'evidence_source_ids': ['osm_20261005'],
                     'coverage_level': 'mapped_footprint_assumed_exterior'})
        polygons.append(geometry)
        additions += 1
    document = ET.parse(osm).getroot()
    nodes = {node.get('id'): (float(node.get('lon')), float(node.get('lat'))) for node in document.findall('node')}
    roads, greens = [], []
    for way in document.findall('way'):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('tag')}
        references = [node.get('ref') for node in way.findall('nd')]
        if len(references) < 2 or any(reference not in nodes for reference in references):
            continue
        coordinates = project([nodes[reference] for reference in references])
        if 'highway' in tags:
            width = {'primary': 12, 'secondary': 9, 'tertiary': 7, 'residential': 5, 'service': 4, 'footway': 1.8, 'path': 1.5}.get(tags['highway'], 4)
            polygon = LineString(coordinates).buffer(width / 2, cap_style=2).intersection(domain)
            if not polygon.is_empty:
                roads.append(polygon)
        if references[0] == references[-1] and len(references) >= 4 and (
                tags.get('landuse') in ('grass', 'forest', 'meadow') or tags.get('leisure') in ('park', 'garden', 'pitch') or tags.get('natural') in ('wood', 'scrub')):
            polygon = Polygon(coordinates)
            if polygon.is_valid and polygon.intersects(domain):
                greens.append(polygon.intersection(domain))
    buildings = len(rows)
    rows.append({'id': 'site-support', 'name': 'Site support', 'kind': 'site',
                 'geometry': polygon_parts(domain), 'roads': polygon_parts(unary_union(roads)),
                 'greens': polygon_parts(unary_union(greens)),
                 'evidence_source_ids': ['osm_20261005'], 'detail_parameters': {}})
    write(root / 'geometry.json', {'crs': crs.to_string(), 'origin_projected_m': [0, 0],
          'axes': 'X east, Y north, Z up; metres; azimuthal equidistant about scene origin',
          'vertical_datum': 'Unsurveyed planar ground at local z=0; heights mostly assumptions', 'buildings': rows})
    write(root / 'src/modules.json', {row['id']: 'site_support' if row['kind'] == 'site' else 'baseline' for row in rows})
    report = {'buildings_in_buffer': buildings, 'buildings_in_focus': sum(bool(row.get('in_focus')) for row in rows),
              'focus_area_m2': focus.area, 'mapped_footprint_fraction_focus': unary_union(polygons).intersection(focus).area / focus.area,
              'osm_additions': additions, 'height_basis': dict(Counter(row['height_basis'] for row in rows if row['kind'] == 'building')),
              'excluded': excluded, 'osm_rejected': rejected, 'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (overture, osm)},
              'geographic_completeness': 'Coverage of downloaded sources, not verified exhaustive against current orthophotos',
              'triangulation': 'Earcut, area checked including holes; whole intersecting buildings retained'}
    write(root / 'inventory_audit.json', report)
    region.update(projection_executed=True, executed_crs=crs.to_string(), vertical_datum='Estimated planar local zero', imagery_acquired=True)
    write(root / 'region.json', region)
    write(root / 'interfaces.json', {'coordinate_frame_status': 'frozen', 'crs': crs.to_string(), 'ground_z_m': 0,
          'shared_walls': [], 'entrances': [], 'ground_openings': [],
          'policy': 'Retain mapped wall shells; no inferred shared openings or bridges. Site support belongs to coordinator.'})
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--overture', type=Path, required=True)
    parser.add_argument('--osm', type=Path, required=True)
    parser.add_argument('--longitude', type=float, required=True)
    parser.add_argument('--latitude', type=float, required=True)
    parser.add_argument('--exclusions', type=Path)
    args = parser.parse_args()
    exclusions = json.loads(args.exclusions.read_text()) if args.exclusions else None
    prepare(args.project, args.overture, args.osm, args.longitude, args.latitude, exclusions=exclusions)


if __name__ == '__main__':
    main()
