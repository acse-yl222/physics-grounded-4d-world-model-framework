"""Plot source coverage and record a manually reviewed region model checkpoint."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from matplotlib.collections import PatchCollection
import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon, box

from urban_geometry.osm_scene import footprints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--osm', type=Path, required=True)
    parser.add_argument('--export', default='dense_v5')
    args = parser.parse_args()
    root = args.project
    data = json.loads((root / 'geometry.json').read_text())
    buildings = [row for row in data['buildings'] if row['kind'] == 'building']
    projection = Transformer.from_crs('EPSG:4326', data['crs'], always_xy=True)
    def project(points):
        coordinates = np.asarray(points)
        return np.column_stack(projection.transform(coordinates[:, 0], coordinates[:, 1]))
    old, _ = footprints(args.osm, {}, project=project)
    focus = box(-1000, -1000, 1000, 1000)
    old = [row for row in old if row['geometry'].intersects(focus)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)
    for axis, rows, title in [(axes[0], old, 'Previous OSM-only source coverage'),
                              (axes[1], buildings, 'Overture + OSM source coverage')]:
        patches = []
        for row in rows:
            if isinstance(row['geometry'], list):
                polygons = [Polygon(part['outer'], part['holes']) for part in row['geometry']]
            else:
                polygons = [row['geometry']] if row['geometry'].geom_type == 'Polygon' else list(row['geometry'].geoms)
            for polygon in polygons:
                patches.append(Patch(np.asarray(polygon.exterior.coords), closed=True))
        axis.add_collection(PatchCollection(patches, facecolor='#4a625e', edgecolor='none'))
        axis.set(xlim=(-1000, 1000), ylim=(-1000, 1000), aspect='equal', xlabel='East (m)', ylabel='North (m)', title=title)
        axis.set_facecolor('#f0eee7')
    fig.suptitle('Thapar University · approximately 2 × 2 km\nSource coverage is not surveyed completeness; no density-filling buildings added')
    output = root.parents[1] / 'reports'
    output.mkdir(exist_ok=True)
    fig.savefig(output / 'reconstruction_coverage.png', dpi=170)
    plt.close(fig)
    audit = json.loads((root / 'inventory_audit.json').read_text())
    audit['focus_height_basis'] = dict(Counter(row['height_basis'] for row in buildings if row['in_focus']))
    audit['native_export'] = args.export
    audit['partial_photo_informed_landmarks'] = ['Directorate', 'Auditorium']
    audit['full_detailed_buildings_verified'] = 0
    audit['note'] = 'All inventory envelopes built; only two partial photo-informed facades. No claim of full facade verification.'
    (output / 'reconstruction_audit.json').write_text(json.dumps(audit, indent=2))
    export = root / 'exports' / args.export
    progress = {'stage': 'numerically_verified_and_visually_reviewed_baseline',
                'inventory_complete': 'relative to downloaded source inventory only',
                'building_envelopes_integrated': len(buildings), 'partial_landmark_modules': 2,
                'full_detailed_buildings_verified': 0, 'numerical_verified': True,
                'visual_reviewed': True, 'delivered': False,
                'pending': ['Final viewer and new simulation checks', 'Current facade, height and terrain evidence remains absent'],
                'buildings': [{'id': row['id'], 'inventoried': True, 'module_built': True, 'integrated': True,
                               'numerical_export_verified': True, 'facade_evidence_reviewed': row['name'] in ('Directorate', 'Auditorium'),
                               'coverage_level': row['coverage_level'], 'full_detail_verified': False} for row in buildings],
                'master_sha256': hashlib.sha256((export / 'region.blend').read_bytes()).hexdigest(),
                'glb_sha256': hashlib.sha256((export / 'region.glb').read_bytes()).hexdigest()}
    (root / 'progress.json').write_text(json.dumps(progress, indent=2))


if __name__ == '__main__':
    main()
