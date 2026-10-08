from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/twenty-cabot-photo-study-001';r=json.loads((R/'references/twenty_cabot_photo_study.json').read_text());checks=[]
bpy.ops.wm.open_mainfile(filepath=str(O/'twenty_cabot.blend'));native_names=sorted(o.name for o in bpy.data.objects if o.type=='MESH');assert native_names==sorted(q['name'] for q in r['objects'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'twenty_cabot.glb'));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert sorted(o.name for o in obs)==native_names
for q in r['objects']:
 ob=bpy.data.objects[q['name']];assert ob['building_id']==q['building_id'];vv=[list(ob.matrix_world@v.co) for v in ob.data.vertices];err=max(abs(fun(v[i] for v in vv)-fun(v[i] for v in q['vertices'])) for fun in [min,max] for i in range(3));assert err<.001;assert len(ob.data.polygons)==q['triangles'];bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bad=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-10 for f in bm.faces);bm.free();checks.append({'name':ob.name,'bounds_error_m':err,'triangles':len(ob.data.polygons),'nonmanifold_edges_after_seam_weld':bad,'zero_area_faces':zero,'materials':[m.name for m in ob.data.materials]})
# Independent geometry envelope comparison for original roofbody objects.
new={q['name']:[min(v[2] for v in q['vertices']),max(v[2] for v in q['vertices'])] for q in r['objects']};bpy.ops.wm.open_mainfile(filepath=r['source_blend']);roofchecks=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 original=[min(v.co.z for v in ob.data.vertices),max(v.co.z for v in ob.data.vertices)];assert all(abs(a-b)<.0001 for a,b in zip(original,new[ob.name]));roofchecks.append({'name':ob.name,'minmax_unchanged':True,'bounds':original})
for state,path in [('before',r['source_blend']),('after',str(O/'twenty_cabot.blend'))]:
 bpy.ops.wm.open_mainfile(filepath=path);s=bpy.context.scene;s.cycles.samples=48;s.render.resolution_x=1200;s.render.resolution_y=1000
 for label,t,off,scale in [('comparison',(-258,-90,31),(-130,-150,45),105),('detail-comparison',(-270,-105,29),(-75,-85,8),40)]:
  t=Vector(t);s.camera.location=t+Vector(off);s.camera.rotation_euler=(t-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(label+'-'+state+'.png'));bpy.ops.render.render(write_still=True)
report={'native_reopened':True,'independent_glb_id_bounds_material_triangle_checks':checks,'roof_body_extents_preserved':roofchecks,'triangles':sum(q['triangles'] for q in r['objects']),'limitations':r['limitations'],'sha256':{f:hashlib.sha256((O/f).read_bytes()).hexdigest() for f in ['twenty_cabot.blend','twenty_cabot.glb']}};(O/'verification.json').write_text(json.dumps(report,indent=2));print(checks)
