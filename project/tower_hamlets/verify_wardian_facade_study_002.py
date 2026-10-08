from pathlib import Path
import bpy,json,hashlib
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/wardian-facade-study-002';expected=json.loads((O/'expected.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'wardian.blend'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert len(obs)==12
for ob in obs:
 ob.name=ob.name.replace('Museum_','Wardian_');ob['component_kind']=next(k for k in ['stone','metal','cladding','backing','glass','guard'] if '_'+k+'_' in ob.name);assert not ob.modifiers
bpy.ops.wm.save_as_mainfile(filepath=str(O/'wardian.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
for ob in obs:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'wardian.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'wardian.glb'));checks=[]
for ob in [o for o in bpy.data.objects if o.type=='MESH']:
 ex=expected[ob.name.replace('Wardian_','Museum_')];assert ob['building_id']==ex['building_id'];assert len(ob.data.polygons)==ex['triangles'];vs=[tuple(ob.matrix_world@v.co) for v in ob.data.vertices];bounds=[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]];err=max(abs(a-b) for r,t in zip(bounds,ex['bounds']) for a,b in zip(r,t));assert err<1e-3;m=ob.data.materials[0];bs=m.node_tree.nodes['Principled BSDF'];metal=bs.inputs['Metallic'].default_value;rough=bs.inputs['Roughness'].default_value;assert abs(metal-ex['metallic'])<1e-5 and abs(rough-ex['roughness'])<1e-5;checks.append({'name':ob.name,'id_verified':True,'triangles':len(ob.data.polygons),'bounds_error_m':err,'metallic':metal,'roughness':rough,'component_kind':ob['component_kind']})
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'all_bevel_modifiers_applied':True,'independent_glb_checks':checks,'scope':'Appearance hypothesis, estimated geometry/layout/materials; no new evidence of actual facade pattern.','sha256':{n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in ['wardian.blend','wardian.glb']}},indent=2)+'\n');print('Verified',len(checks),'meshes')
