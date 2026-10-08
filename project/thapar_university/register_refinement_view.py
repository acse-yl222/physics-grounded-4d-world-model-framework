"""Retain a geometry-only inspection view, without mixing older simulation fields."""
import hashlib
import argparse
import json
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from common.contract import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', default='refinement_candidate_20261007_v2')
    parser.add_argument('--export', default='campus_review_002')
    parser.add_argument('--run-id', default='refinement_20261007_geometry')
    parser.add_argument('--view-prefix', default='refinement')
    parser.add_argument('--artistic', action='store_true')
    parser.add_argument('--roof-candidate')
    parser.add_argument('--roof-export', default='roof_001')
    args = parser.parse_args()
    scene = Path(__file__).resolve().parent
    candidate = scene / 'geometry' / args.candidate
    export = candidate / 'exports' / args.export
    run_id = args.run_id
    run = scene / 'runs' / run_id
    if run.exists():
        raise FileExistsError(run)
    verification = json.loads((export / 'verification.json').read_text())
    if not verification['numerical_export_verified']:
        raise ValueError('Geometry export not verified')
    for name, expected in verification['source_sha256'].items():
        if hashlib.sha256((candidate / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Changed source: ' + name)
    roof_candidate = scene / 'geometry' / args.roof_candidate if args.roof_candidate else None
    roof_verification = None
    if roof_candidate:
        roof_verification = json.loads((roof_candidate / 'exports' / args.roof_export / 'verification.json').read_text())
        if not roof_verification['numerical_export_verified']:
            raise ValueError('Roof geometry export not verified')
        for name, expected in roof_verification['source_sha256'].items():
            if hashlib.sha256((roof_candidate / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Changed roof source: ' + name)
    run.mkdir(parents=True)
    shutil.copy2(export / 'region.glb', run / 'region.glb')
    shutil.copy2(candidate / 'REVIEW.md', run / 'REVIEW.md')
    if roof_candidate:
        shutil.copy2(roof_candidate / 'exports' / args.roof_export / 'region.glb', run / 'roofs.glb')
    with tarfile.open(run / 'source_snapshot.tar.gz', 'w:gz') as archive:
        for name in verification['source_sha256']:
            archive.add(candidate / name, arcname=name)
        archive.add(Path(__file__), arcname='register_refinement_view.py')
        archive.add(scene / 'prepare_visual_campus.py', arcname='prepare_visual_campus.py')
        if (candidate / 'review_renders/render_report.json').exists():
            archive.add(scene.parents[1] / 'src/urban_geometry/render_review.py', arcname='render_review.py')
            archive.add(candidate / 'review_renders/render_report.json', arcname='render_report.json')
        for name in ['coverage.json', 'campus_boundary.json', 'detail_validation.json', 'visual_review.json']:
            if (candidate / name).exists():
                archive.add(candidate / name, arcname=name)
        archive.add(export / 'verification.json', arcname='verification.json')
        if roof_candidate:
            for name in roof_verification['source_sha256']:
                archive.add(roof_candidate / name, arcname='roofs/' + name)
            archive.add(roof_candidate / 'exports' / args.roof_export / 'verification.json', arcname='roofs/verification.json')
            archive.add(scene / 'prepare_roof_detail.py', arcname='prepare_roof_detail.py')
    project = json.loads((scene / 'project.json').read_text())
    coverage_path = candidate / 'coverage.json'
    coverage = json.loads(coverage_path.read_text()) if coverage_path.exists() else {}
    detail_count = coverage.get('detailed_buildings', coverage.get('campus_buildings', 315))
    detail_scope = coverage.get('detail_scope', 'campus')
    manifest = {
        'schema_version': '1.1.0', 'scene_id': 'thapar_university',
        'simulation': 'geometry', 'run_id': run_id, 'status': 'complete',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'spatial': project['spatial'], 'time': {'unit': 's', 'samples': []},
        'provenance': {
            'code_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'dirty': True,
            'parameters': {'geometry_only': True, 'full_refinement_complete': False,
                           'artistic_visual_version': args.artistic,
                           'detail_scope': detail_scope,
                           'detailed_buildings': detail_count,
                           'note': (f'ARTISTIC visual detail on {detail_count} mapped buildings in {detail_scope} scope; inferred floors/windows/roofs and proposed campus shade walks, NOT surveyed reconstruction. Old simulations do not apply.' if args.artistic else 'Partial refinement: two historical-photo-informed facades and mapped outdoor surfaces. Most heights assumed. No simulations recomputed.')},
            'inputs': [{'id': 'refined_glb', 'sha256': hashlib.sha256((run / 'region.glb').read_bytes()).hexdigest()}],
        },
        'artifacts': [{'id': 'source_snapshot', 'asset': 'source_snapshot.tar.gz',
                       'sha256': hashlib.sha256((run / 'source_snapshot.tar.gz').read_bytes()).hexdigest(),
                       'media_type': 'application/gzip'},
                      {'id': 'review', 'asset': 'REVIEW.md',
                       'sha256': hashlib.sha256((run / 'REVIEW.md').read_bytes()).hexdigest(),
                       'media_type': 'text/markdown'}],
        'layers': [{'id': 'refined_geometry', 'kind': 'mesh', 'format': 'glb',
                    'asset': 'region.glb', 'sampling': 'static',
                    'encoding': {'coordinate_frame': 'glTF-y-up'},
                    'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}],
    }
    if roof_candidate:
        roof_coverage = json.loads((roof_candidate / 'coverage.json').read_text())
        manifest['provenance']['parameters']['roof_overlay_buildings'] = roof_coverage['roof_buildings']
        manifest['provenance']['parameters']['note'] += ' Campus roof finishes and opaque rooflight housings are also artistic estimates, not observed structures.'
        manifest['provenance']['inputs'].append({'id': 'roof_overlay', 'sha256': hashlib.sha256((run / 'roofs.glb').read_bytes()).hexdigest()})
        manifest['layers'].append({'id': 'roof_detail', 'kind': 'mesh', 'format': 'glb',
                                  'asset': 'roofs.glb', 'sampling': 'static',
                                  'encoding': {'coordinate_frame': 'glTF-y-up'},
                                  'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}})
    (run / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    validate(run / 'manifest.json')
    views = {
        args.view_prefix: ([950, -1250, 1100] if args.artistic else [1500, -1700, 1500], [0, 0, 0]),
        args.view_prefix + '_directorate': ([550, -285, 48], [525, -215, 3]),
    }
    if args.artistic:
        for camera_view in json.loads((candidate / 'inspection_views.json').read_text()):
            if camera_view['id'] in ('library_front', 'hostel_front'):
                target = camera_view['target']
                position = [value + offset for value, offset in zip(target, camera_view['offset'])]
                views[args.view_prefix + '_' + camera_view['id'].split('_')[0]] = (position, target)
            if camera_view['id'].startswith('periphery_') or camera_view['id'] in ('study_overview', 'exterior_front'):
                target = camera_view['target']
                position = [value + offset for value, offset in zip(target, camera_view['offset'])]
                suffix = camera_view['id'].removeprefix('periphery_')
                name = args.view_prefix if camera_view['id'] == 'study_overview' else args.view_prefix + '_' + suffix
                views[name] = (position, target)
    for name, (position, target) in views.items():
        view = {'schema_version': '1.1.0', 'scene_id': 'thapar_university',
                'title': 'Refined geometry only · ' + name, 'time_alignment': 'relative',
                'runs': [run_id], 'layers': [{'run_id': run_id, 'layer_id': 'refined_geometry', 'visible': True}],
                'camera': {'position': position, 'target': target}}
        if roof_candidate:
            view['layers'].append({'run_id': run_id, 'layer_id': 'roof_detail', 'visible': True})
        (scene / 'views' / (name + '.json')).write_text(json.dumps(view, indent=2))
    print(run / 'manifest.json')


if __name__ == '__main__':
    main()
