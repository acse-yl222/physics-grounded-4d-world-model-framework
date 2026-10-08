"""Portable minimal Blender module assembler. Numerical success is not delivery."""
import argparse
import hashlib
import importlib
import json
import math
import re
import struct
import sys
from pathlib import Path
import bpy
from mathutils import Vector

IMAGE_KINDS = {'aerial', 'orthophoto', 'satellite', 'street_photo', 'street_view', 'user_photo', 'image', 'drawing'}
SOURCE_KINDS = IMAGE_KINDS | {'vector', 'lidar', 'survey', 'text', 'procedural_test_fixture'}


def validate_sources(sources):
    required={'id','provider','url','kind','accessed_at','capture_date','viewpoint','license_url',
              'attribution','rights_review','geometry_derivation','export_texture_use'}
    ledger={}
    for source in sources:
        if not required<=source.keys():raise ValueError('Incomplete source record')
        sid=source['id']
        if not isinstance(sid,str) or not sid or sid in ledger:raise ValueError('Invalid or duplicate source ID')
        if source['kind'] not in SOURCE_KINDS:raise ValueError('Unknown source kind')
        if not source['rights_review']:raise ValueError('Missing rights review')
        ledger[sid]=source
    return ledger


def finite_object(ob):
    if not all(math.isfinite(x) for row in ob.matrix_world for x in row):return False
    return ob.type!='MESH' or all(math.isfinite(x) for v in ob.data.vertices for x in v.co)


def bounds(objects):
    vertices=[ob.matrix_world@Vector(p) for ob in objects for p in ob.bound_box]
    return [[min(p[i] for p in vertices) for i in range(3)],
            [max(p[i] for p in vertices) for i in range(3)]]


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--run',required=True)
    p.add_argument('--allow-partial',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    root=Path(args.project).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',args.run):raise ValueError('Unsafe run name')
    out=root/'exports'/args.run
    if out.exists():raise ValueError('Refusing to overwrite an existing run')
    data=json.loads((root/'geometry.json').read_text())
    rows=data['buildings'];features={str(f['id']):f for f in rows}
    modules=json.loads((root/'src/modules.json').read_text())
    if not features or len(features)!=len(rows):raise ValueError('Empty inventory or duplicate IDs')
    if not modules or not set(modules)<=set(features):raise ValueError('Invalid module mapping')
    if not args.allow_partial and set(modules)!=set(features):raise ValueError('Missing modules; explicitly use --allow-partial for a draft')
    if not data.get('crs') or data.get('vertical_datum') is None:raise ValueError('Document CRS and vertical datum, including estimated status')
    sources=json.loads((root/'references/sources.json').read_text())
    ledger=validate_sources(sources)
    for oid in modules:
        evidence=features[oid].get('evidence_source_ids',[])
        if not evidence:raise ValueError('Missing evidence-source IDs for '+oid)
        for sid in evidence:
            source=ledger.get(sid,{})
            if source.get('geometry_derivation')!='allowed':raise ValueError('Unreviewed derivation rights: '+sid)
            if source['kind'] in IMAGE_KINDS and source.get('actually_inspected') is not True:
                raise ValueError('Image not actually inspected: '+sid)
    def source_snapshot():
        files=['geometry.json','region.json','region.geojson','interfaces.json','src/modules.json','references/sources.json']
        files+=sorted(str(f.relative_to(root)) for f in (root/'src').rglob('*.py'))
        return {s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in files}
    initial_sources=source_snapshot()
    sys.path.insert(0,str(root/'src'));from detailed_common import BuildingContext
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    authored=[];reports={}
    for oid,slug in modules.items():
        if not re.fullmatch(r'[a-z][a-z0-9_]*',slug):raise ValueError('Invalid module slug')
        feature=features[oid];before=json.dumps(feature,sort_keys=True)
        col=bpy.data.collections.new(oid+' | '+feature['name']);scene.collection.children.link(col)
        old_objects=set(bpy.data.objects)
        result=importlib.import_module('buildings.'+slug).build(BuildingContext(col,feature),feature)
        if json.dumps(feature,sort_keys=True)!=before:raise ValueError('Module mutated feature input')
        json.dumps(result);objects=list(col.all_objects)
        if not objects or set(result['created'])!={o.name for o in objects}:raise ValueError('Incomplete created list')
        if set(bpy.data.objects)-old_objects!=set(objects) or not old_objects<=set(bpy.data.objects):
            raise ValueError('Module added objects outside its collection or removed previous objects')
        for ob in objects:
            if ob.type not in ('MESH','FONT'):raise ValueError('Module must return meshes or fonts only')
            if not ob.data.materials or any(m is None for m in ob.data.materials):raise ValueError('Missing material')
            if not finite_object(ob):raise ValueError('Nonfinite object transform or mesh')
            if ob.type=='MESH' and (not ob.data.polygons or not all(math.isfinite(x) for v in ob.data.vertices for x in v.co)):
                raise ValueError('Empty or nonfinite mesh')
            ob['research_object_id']=oid+'::'+ob.name;ob['building_id']=oid
        authored.extend(objects);reports[oid]=result
    bpy.context.view_layer.update();bb=bounds(authored)
    centre=(Vector(bb[0])+Vector(bb[1]))/2;span=max(Vector(bb[1])-Vector(bb[0]))
    bpy.ops.object.camera_add(location=centre+Vector((1.0,-1.3,1.1))*max(span,10))
    cam=bpy.context.object;cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=max(span,10)*1.6;cam.data.clip_end=max(span*10,1000);scene.camera=cam
    bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2.0;bpy.context.object.rotation_euler=(.4,-.3,-.3)
    scene.world=bpy.data.worlds.new('Neutral inspection world');scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.6
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    out.mkdir(parents=True);master=out/'region.blend';glb=out/'region.glb'
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(master),compress=False)
    stamp=master.stat().st_mtime_ns
    scene.render.filepath=str(out/'overview.png');bpy.ops.render.render(write_still=True)
    # Explicitly reopen saved bytes before export. Do not flatten shader links.
    bpy.ops.wm.open_mainfile(filepath=str(master));scene=bpy.context.scene
    authored=[o for o in scene.objects if o.get('research_object_id')]
    bpy.ops.object.select_all(action='DESELECT')
    for ob in authored:ob.select_set(True)
    bpy.context.view_layer.objects.active=authored[0];bpy.ops.object.convert(target='MESH')
    expected={}
    for ob in authored:
        ob.data.calc_loop_triangles();expected[ob['research_object_id']]=len(ob.data.loop_triangles)
    if len(expected)!=len(authored):raise ValueError('Duplicate object IDs')
    bb=bounds(authored)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,
        export_extras=True,export_apply=True,export_draco_mesh_compression_enable=False)
    with glb.open('rb') as f:
        magic,version,total=struct.unpack('<4sII',f.read(12));length,kind=struct.unpack('<II',f.read(8));gltf=json.loads(f.read(length))
    assert magic==b'glTF' and version==2 and total==glb.stat().st_size
    assert 'KHR_draco_mesh_compression' not in gltf.get('extensionsUsed',[])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
    actual={o.get('research_object_id'):len(o.data.polygons) for o in imported}
    assert len(actual)==len(imported) and actual==expected,'Object or triangle mismatch'
    assert {o.get('building_id') for o in imported}==set(modules)
    assert all(o.data.materials and all(m is not None for m in o.data.materials) for o in imported)
    assert all(finite_object(o) for o in imported),'Nonfinite imported transform or mesh'
    imported_bb=bounds(imported);error=max(abs(bb[i][j]-imported_bb[i][j]) for i in range(2) for j in range(3))
    assert error<.002,'Export fidelity mismatch, not survey tolerance'
    images={n.image for o in imported for m in o.data.materials if m.node_tree for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    assert all(len(im.pixels)>0 for im in images)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'glb_verification.blend'),compress=False)
    if source_snapshot()!=initial_sources:raise ValueError('Source changed during build; discard this run and rebuild from a frozen batch')
    report={'master':str(master.relative_to(root)),'master_mtime_ns':stamp,'glb':str(glb.relative_to(root)),
        'glb_bytes':glb.stat().st_size,'glb_mtime_ns':glb.stat().st_mtime_ns,
        'source_sha256':initial_sources,
        'buildings':reports,'inventory_count':len(features),'integrated_count':len(modules),
        'pending_ids':sorted(set(features)-set(modules)),'objects':len(actual),'triangles':sum(actual.values()),
        'bounds_error_m':error,'numerical_export_verified':True,'native_compression':False,'draco':False,
        'images_decoded':len(images),'embedded_images':len(gltf.get('images',[])),
        'visual_reviewed':False,'materials_visually_verified':False,'texture_preservation_verified':False,
        'module_mutation_isolation_verified':False,'site_interfaces_verified':False,'delivered':False,
        'limitations':'Minimal assembly/export check only. Requires site-specific geometry, interface, material and visual review; not a survey or full-area completion certificate.'}
    (out/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('REGION_NUMERICAL_EXPORT_VERIFIED',len(modules),len(features),str(out),flush=True)

if __name__=='__main__':main()
