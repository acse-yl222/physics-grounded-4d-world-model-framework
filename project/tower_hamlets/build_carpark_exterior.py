"""Exterior appearance study, not surveyed reconstruction. Blender/GLB only."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/carpark-exterior-001';O.mkdir(exist_ok=False);bpy.ops.wm.open_mainfile(filepath=str(R/'exports/carpark-cad-001/carpark.blend'));s=bpy.context.scene
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and ob.name.startswith('Rail_'):bpy.data.objects.remove(ob,do_unlink=True)
def mat(name,color,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return m
fascia=mat('Estimated neutral facade panels',(.38,.43,.46),.7);cap=mat('Estimated dark coping',(.08,.11,.13),.45)
g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']=='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c');params=json.loads((R/'exports/carpark-cad-001/parameters.json').read_text());spacing=params['assumed_level_spacing_m']
def panel(name,a,b,z,h,w,material):
 d=Vector((b[0]-a[0],b[1]-a[1],0));length=d.length
 if length<.01:return
 bpy.ops.mesh.primitive_cube_add(size=1,location=((a[0]+b[0])/2,(a[1]+b[1])/2,z+h/2));ob=bpy.context.object;ob.name=name;ob.dimensions=(length+.012,w,h);ob.rotation_euler[2]=math.atan2(d.y,d.x);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(material);ob['basis']='Estimated appearance completion; panel dimensions/layout not visually verified';bevel=ob.modifiers.new('Small edge bevel','BEVEL');bevel.width=.018;bevel.segments=2;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=bevel.name)
for q in f['geometry']:
 for ringindex,ring in enumerate([q['outer']]+q.get('holes',[])):
  for i in range(1,8):
   for j,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
    panel(f'Facade_band_{ringindex}_{i}_{j}',a,b,i*spacing,.95,.16,fascia);panel(f'Coping_{ringindex}_{i}_{j}',a,b,i*spacing+.95,.065,.22,cap)
# Render as an exterior asset, with no engineering annotations in the scene.
s.render.resolution_x=1400;s.render.resolution_y=900;s.cycles.samples=48;s.render.filepath=str(O/'carpark.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'carpark.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={}
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();expected[ob.name]=len(ob.data.loop_triangles)
bpy.ops.export_scene.gltf(filepath=str(O/'carpark.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'carpark.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'carpark.glb'));actual={o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'independent_glb_triangle_counts_verified':True,'objects':len(expected),'scope':'Estimated exterior appearance study; mapped outline and source floor count only. Not verified real facade.','limitations':['Neutral facade bands, coping, column grid and heights estimated.','Top remains flat in this study; measured top-surface refinements not integrated.','No verified entrances or ramps; not operational building model.']},indent=2)+'\n')
