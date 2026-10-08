from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';A=R/'exports/facade-pediment-pilot001';O=R/'exports/pediment-independent-review001';O.mkdir(exist_ok=True);src=A/'pediment.blend';sha=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));deps=bpy.context.evaluated_depsgraph_get();s=bpy.context.scene;meshes=[o for o in bpy.data.objects if o.type=='MESH'];topology=[]
for ob in meshes:
 bm=bmesh.new();bm.from_mesh(ob.data);topology.append({'name':ob.name,'nonmanifold':sum(not e.is_manifold for e in bm.edges),'zero_area':sum(f.calc_area()<1e-10 for f in bm.faces),'signed_volume':bm.calc_volume(signed=True),'building_id':ob.get('building_id'),'materials':[{'name':m.name,'base_color':list(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)} for m in ob.data.materials]});bm.free()
wall=[o.name for o in meshes if o.name.startswith('Pediment_wall_true_openings')];rays=[]
for center in [-18,-11.5,11.5,18]:
 for x in [center-2,center,center+2]:
  for z in [1.3,3.7,6.0]:
   hit,loc,n,index,obj,mat=s.ray_cast(deps,Vector((x,-5,z)),Vector((0,1,0)),distance=15);rays.append({'opening_center':center,'x':x,'z':z,'first_hit':obj.name if hit else None,'y':float(loc.y) if hit else None,'normal':list(n) if hit else None,'true_open':bool(hit and loc.y>1.2)})
arch=[]
for x,z in [(0,3),(0,8),(0,12),(0,13),(3,5),(-3,5),(3,10),(-3,10)]:
 hit,loc,n,index,obj,mat=s.ray_cast(deps,Vector((x,-5,z)),Vector((0,1,0)),distance=15);arch.append({'x':x,'z':z,'first_hit':obj.name if hit else None,'y':float(loc.y) if hit else None,'true_open':bool(hit and loc.y>1.2)})
checks={'native_sha256':sha,'source_unchanged':sha==hashlib.file_digest(src.open('rb'),'sha256').hexdigest(),'wall_objects':wall,'topology':topology,'rectangular_opening_rays':rays,'arch_opening_rays':arch,'all_rectangles_true_open':all(r['true_open'] for r in rays),'all_arch_samples_true_open':all(r['true_open'] for r in arch),'local_unassigned_only':all(not o.get('building_id') for o in meshes),'limitations':['Photo proportions visuallyestimated; no geographicowner assertion.','Openingrays samplevoids notfullentrance accessibility or glazingconstruction.']};(O/'review.json').write_text(json.dumps(checks,indent=2));print('REVIEW',len(wall),sum(r['true_open'] for r in rays),len(rays),sum(r['true_open'] for r in arch),len(arch))
