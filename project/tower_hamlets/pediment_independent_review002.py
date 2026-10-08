from pathlib import Path
import bpy,bmesh,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';A=R/'exports/facade-pediment-pilot002';O=R/'exports/pediment-independent-review002';O.mkdir(exist_ok=True);src=A/'pediment.blend';sha=hashlib.file_digest(src.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));deps=bpy.context.evaluated_depsgraph_get();s=bpy.context.scene;meshes=[o for o in bpy.data.objects if o.type=='MESH'];topology=[]
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

# Independent intervals from actual vertices, not author claims.
longs=[o for o in meshes if o.name.startswith('Coffer_longitudinal')];cross=[o for o in meshes if o.name.startswith('Coffer_curved')];interval=lambda o:(min(v.co.y for v in o.data.vertices),max(v.co.y for v in o.data.vertices))
overlap=[]
for a in longs:
 for b in cross:
  x,y=interval(a),interval(b);overlap.append({'longitudinal':a.name,'cross':b.name,'overlap_depth_m':max(0,min(x[1],y[1])-max(x[0],y[0]))})
lat=bpy.data.objects['Rear_open_cross_lattice'];adj={v.index:set() for v in lat.data.vertices}
for e in lat.data.edges:
 a,b=e.vertices;adj[a].add(b);adj[b].add(a)
unseen=set(adj);components=[]
while unseen:
 stack=[unseen.pop()];n=0
 while stack:
  q=stack.pop();n+=1
  for k in adj[q]:
   if k in unseen:unseen.remove(k);stack.append(k)
 components.append(n)
import math
from mathutils.bvhtree import BVHTree
coffertrees=[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])) for o in meshes if o.name.startswith(('Coffer_','Arch_vault_soffit'))]
radial=[]
for angular in [math.pi/4,math.pi/2,3*math.pi/4]:
 for yy in [1.319,1.321,2.359,2.361,2.459,2.461,3.399,3.401]:
  direction=Vector((math.cos(angular),0,math.sin(angular)));hits=[]
  for name,tree in coffertrees:
   loc,n,index,dist=tree.ray_cast(Vector((0,yy,8)),direction,8)
   if loc is not None:hits.append((dist,name,loc))
  dist,name,loc=min(hits,key=lambda q:q[0]);radius=math.hypot(loc.x,loc.z-8);radial.append({'theta':angular,'y':yy,'radius':radius,'object':name})
checks.update({'actual_coffer_overlap_depth_max_m':max(q['overlap_depth_m'] for q in overlap),'coffer_interval_pairs':overlap,'lattice_connected_components':components,'joint_adjacent_radial_rays':radial,'no_coffer_joint_gap':all(q['radius'] is not None and abs(q['radius']-5.33)<.01 for q in radial)})
(O/'review.json').write_text(json.dumps(checks,indent=2));print('EXTRA',checks['actual_coffer_overlap_depth_max_m'],components,checks['no_coffer_joint_gap'])
