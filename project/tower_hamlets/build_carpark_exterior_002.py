from pathlib import Path
import bpy,json
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/carpark-exterior-004';O.mkdir(exist_ok=False);bpy.ops.wm.open_mainfile(filepath=str(R/'exports/carpark-exterior-001/carpark.blend'));r=json.loads((R/'references/carpark_exterior_roof.json').read_text());s=bpy.context.scene
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 if ob.name=='Deck_08_estimated' or (ob.name.startswith(('Facade_band_','Coping_')) and ob.name.split('_')[-2]=='7'):bpy.data.objects.remove(ob,do_unlink=True)
for q in r['zones']:
 m=bpy.data.meshes.new('Roof_'+q['name']);m.from_pydata(q['vertices'],[],q['faces']);m.update();ob=bpy.data.objects.new('Roof_'+q['name'],m);bpy.context.collection.objects.link(ob);m.materials.append(bpy.data.materials['deck']);ob['basis']=r['basis']
# Extend the existing estimated grid to each local roof underside.
for name,plane in r['column_upper_planes'].items():
 ob=bpy.data.objects.get(name)
 if ob is None:continue
 highest=max(v.co.z for v in ob.data.vertices);a,b,c=plane['plane'];cx,cy=plane['center']
 for v in ob.data.vertices:
  if abs(v.co.z-highest)<.001:v.co.z=a+b*(v.co.x-cx)+c*(v.co.y-cy)-4.28000021-.28
 ob['basis']='Estimated grid extended to fitted-plane underside; not surveyed supports'
s.render.filepath=str(O/'carpark.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'carpark.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');expected={};points=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.select_set(True);ob.data.calc_loop_triangles();expected[ob.name]=len(ob.data.loop_triangles);points.extend(ob.matrix_world@v.co for v in ob.data.vertices)
bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
bpy.ops.export_scene.gltf(filepath=str(O/'carpark.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False);bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'carpark.blend'));assert len([o for o in bpy.data.objects if o.type=='MESH'])==len(expected)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'carpark.glb'));assert {o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'}==expected
points=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];actual=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]];assert max(abs(a-b) for aa,bb in zip(bounds,actual) for a,b in zip(aa,bb))<1e-4
(O/'verification.json').write_text(json.dumps({'native_reopened':True,'glb_reimport_counts_bounds_verified':True,'objects':len(expected),'bounds_enu_m':bounds,'scope':'Exterior hypothesis; observed plane equations, estimated full plan boundaries/facade/structure. Missing verified access and upper supports.'},indent=2)+'\n')
