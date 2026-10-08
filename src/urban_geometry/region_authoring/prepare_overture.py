"""Prepare a labelled massing baseline, preserving source polygons and building parts."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil

import mapbox_earcut
import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import shape, box, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import transform, unary_union


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def parts(geometry):
    result = []
    polygons = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
    for poly in polygons:
        if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 1e-6:
            continue
        poly = orient(poly, sign=1)
        rings = [np.asarray(r.coords[:-1], dtype=np.float64) for r in [poly.exterior, *poly.interiors]]
        vertices = np.concatenate(rings)
        indices = mapbox_earcut.triangulate_float64(vertices, np.cumsum([len(r) for r in rings], dtype=np.uint32))
        triangles = vertices[indices.reshape(-1, 3)]
        assert np.isclose(sum(Polygon(t).area for t in triangles), poly.area, atol=1e-5, rtol=1e-8)
        result.append({'outer': rings[0].tolist(), 'holes': [r.tolist() for r in rings[1:]], 'triangles': triangles.tolist()})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--download', type=Path, required=True)
    args = parser.parse_args()
    root, download = args.project, args.download
    region = json.loads((root / 'region.json').read_text())
    lon, lat = region['centre_wgs84']
    crs = CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    projector = Transformer.from_crs(4326, crs, always_xy=True).transform
    aoi = transform(projector, box(*region['bbox_wgs84']))
    records = {}
    for kind in ('buildings', 'building_parts', 'water'):
        shutil.copy2(download / f'{kind}.geojson', root / 'references' / f'{kind}.geojson')
        records[kind] = json.loads((download / f'{kind}.geojson').read_text())['features']
    children = defaultdict(list)
    for f in records['building_parts']:
        children[f['properties'].get('building_id')].append(f)
    rows, excluded, inventory = [], [], []
    parents = {f['id']: f for f in records['buildings']}
    def add(f, geometry, kind, parent=None):
        p = f['properties']
        if geometry.is_empty:
            return
        if p.get('is_underground'):
            excluded.append({'id': f['id'], 'reason': 'underground excluded from exterior baseline'})
            return
        height, basis = p.get('height'), 'source_reported_height'
        if height is None:
            floors = p.get('num_floors')
            height, basis = (floors * 3, 'source_floors_times_assumed_3m') if floors else (9, 'assumed_9m_unknown_height')
        minimum = p.get('min_height')
        minimum_basis = 'source_reported_min_height'
        if minimum is None:
            minimum, minimum_basis = ((p.get('min_floor') or 0) * 3, 'assumed_floor_or_ground_zero')
        if height <= minimum:
            excluded.append({'id': f['id'], 'reason': 'nonpositive height interval'})
            return
        rows.append({'id': 'overture-' + ('part-' if kind == 'part' else 'building-') + f['id'],
                     'name': (p.get('names') or {}).get('primary') or ((parent or {}).get('properties', {}).get('names') or {}).get('primary') or f['id'],
                     'kind': kind, 'parent_id': p.get('building_id'), 'geometry': parts(geometry),
                     'height_m': height, 'min_height_m': minimum, 'height_basis': basis,
                     'minimum_height_basis': minimum_basis, 'source_properties': p,
                     'boundary_crossing': not aoi.covers(geometry), 'detail_parameters': {},
                     'evidence_source_ids': ['overture_building_parts_20260923' if kind == 'part' else 'overture_buildings_20260923'],
                     'coverage_level': 'mapped_massing_baseline_not_facade_reconstruction'})
    for f in records['buildings']:
        g = transform(projector, shape(f['geometry']))
        if not g.is_valid:
            excluded.append({'id': f['id'], 'reason': 'invalid geometry'}); continue
        if not g.intersects(aoi):
            continue
        inventory.append({'id': f['id'], 'name': (f['properties'].get('names') or {}).get('primary'), 'parts': len(children[f['id']])})
        # Do not extrude an envelope over its detailed parts. Retain residual plan area.
        child_polys = [transform(projector, shape(c['geometry'])) for c in children[f['id']] if not c['properties'].get('is_underground')]
        if child_polys:
            g = g.difference(unary_union(child_polys))
        add(f, g, 'building')
    for f in records['building_parts']:
        g = transform(projector, shape(f['geometry']))
        if g.is_valid and (g.intersects(aoi) or f['properties'].get('building_id') in {i['id'] for i in inventory}):
            add(f, g, 'part', parents.get(f['properties'].get('building_id')))
    water = []
    for f in records['water']:
        g = transform(projector, shape(f['geometry']))
        if g.geom_type in ('Polygon', 'MultiPolygon') and g.is_valid:
            water.extend(parts(g.intersection(aoi)))
    rows.append({'id': 'site-support', 'name': 'Estimated flat ground and mapped water', 'kind': 'site',
                 'geometry': parts(aoi), 'water': water, 'evidence_source_ids': ['overture_water_20260923']})
    write(root / 'geometry.json', {'crs': crs.to_string(), 'origin_projected_m': [0, 0],
          'axes': 'X east Y north Z up, metres', 'vertical_datum': 'Unsurveyed local flat ground z=0', 'buildings': rows})
    write(root / 'inventory_audit.json', {'downloaded_buildings': len(records['buildings']),
          'downloaded_parts': len(records['building_parts']), 'inventory': inventory,
          'rendered_building_and_part_objects': len(rows)-1, 'excluded': excluded,
          'height_basis': dict(Counter(r['height_basis'] for r in rows[:-1])),
          'boundary_crossing_objects': sum(r['boundary_crossing'] for r in rows[:-1]),
          'aoi_area_m2': aoi.area, 'aoi_bounds_m': list(aoi.bounds),
          'limitations': ['Inventory is relative to downloaded sources, not an exhaustive real-world audit.',
            'Boundary-crossing parent parts outside query may be incomplete.',
            'Parent envelopes subtract part footprints; residual heights may represent tower maximum rather than podium.',
            'No aerial/street image acquired; no facade verification; no terrain survey.']})
    write(root / 'src/modules.json', {r['id']: 'site_support' if r['kind']=='site' else 'baseline' for r in rows})
    write(root / 'interfaces.json', {'coordinate_frame_status': 'frozen', 'crs': crs.to_string(),
          'ground_z_m': 0, 'shared_walls': [], 'entrances': [], 'ground_openings': [],
          'policy': 'Mapped parts replace parent plan overlap; no invented shared openings. No calibrated support elevations.'})
    ledger = []
    for kind in ('buildings','building_parts','water'):
        path = root / 'references' / f'{kind}.geojson'
        ledger.append({'id': f'overture_{kind}_20260923', 'provider': 'Overture Maps Foundation / source contributors',
          'url': 'https://docs.overturemaps.org/', 'kind': 'vector', 'accessed_at': '2026-10-07',
          'capture_date': None, 'viewpoint': None, 'license_url': 'https://docs.overturemaps.org/attribution/',
          'attribution': '© OpenStreetMap contributors, Overture Maps Foundation; per-feature source attribution preserved',
          'rights_review': 'Buildings and base themes ODbL; local derived baseline, no imagery or textures reused.',
          'geometry_derivation': 'allowed', 'export_texture_use': 'not_applicable', 'status': 'retrieved',
          'release': '2026-09-23.1', 'filename': f'references/{kind}.geojson',
          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    write(root / 'references/sources.json', ledger)
    region.update(projection_executed=True, executed_crs=crs.to_string(), vertical_datum='Unsurveyed flat ground', imagery_acquired=False)
    write(root / 'region.json', region)
    print(json.dumps({'objects':len(rows)-1,'inventory':len(inventory),'height_basis':dict(Counter(r['height_basis'] for r in rows[:-1]))}))


if __name__ == '__main__':
    main()
