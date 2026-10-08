import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/water8-massing-001';src=R/'exports/appearance-owner836-001/region.blend';sha=hashlib.sha256(src.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(src));bid='overture-building-36beb80b-ced9-4f18-a461-04680502f52e';keep=[]
for o in list(bpy.data.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True);continue
 pts=[o.matrix_world@Vector(c) for c in o.bound_box];lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
 if o.get('building_id')==bid or hi[0]<230 or lo[0]>345 or hi[1]<-315 or lo[1]>-245:bpy.data.objects.remove(o,do_unlink=True)
 else:keep.append(o)
with bpy.data.libraries.load(str(O/'water8.blend'),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('Water8_')]
new=[]
for o in b.objects:
 if o and o.type=='MESH':bpy.context.collection.objects.link(o);new.append(o)
def tree(o):
 me=o.data;me.calc_loop_triangles();v=[o.matrix_world@p.co for p in me.vertices];t=[tuple(p.vertices) for p in me.loop_triangles];return BVHTree.FromPolygons(v,t,all_triangles=True,epsilon=0.00001),v,t
rows=[]
for a in new:
 ta,va,fa=tree(a)
 for b in keep:
  tb,vb,fb=tree(b);hits=ta.overlap(tb);near=[]
  # nearest vertices and triangle centroids detect proximity, not solid containment
  samples=va+[sum((va[i] for i in f),Vector())/3 for f in fa]
  for v in samples:
   q,n,idx,d=tb.find_nearest(v)
   if d is not None:near.append(d)
  if hits or min(near,default=1e9)<2:rows.append({'candidate':a.name,'neighbor':b.name,'building_id':b.get('building_id'),'neighbor_bounds_z':[min(v.z for v in vb),max(v.z for v in vb)],'bvh_triangle_contact_pairs':len(hits),'sample_min_distance_m':min(near)})
# shared-line sample just inside each footprint, vertical downward ray finds outer top surface
p0=Vector((310.09676140409164,-300.4536504796824,0));p1=Vector((312.5121032899697,-283.3642914319506,0));direction=(p1-p0).normalized();normal=Vector((-direction.y,direction.x,0));samples=[]
for i in range(21):
 p=p0.lerp(p1,i/20);r={'fraction':i/20,'xy':[p.x,p.y]}
 for label,obs,sign in [('candidate',new,1),('neighbor',keep,-1)]:
  vals=[]
  for ob in obs:
   t,_,_=tree(ob);origin=p+normal*(.05*sign)+Vector((0,0,250));hit=t.ray_cast(origin,Vector((0,0,-1)),300)
   if hit[0] is not None:vals.append({'name':ob.name,'top_z':hit[0].z})
  r[label]=vals
 samples.append(r)
report={'source_native':str(src),'sha256':sha,'source_unchanged':hashlib.sha256(src.read_bytes()).hexdigest()==sha,'nearby_mesh_count':len(keep),'pairs':rows,'shared_edge_top_rays_5cm_inward':samples,'method':'World-coordinate triangle BVH overlap with 1e-5m epsilon; nearest distances at candidate vertices and triangle centroids; 21 downward rays offset5cm either side of mapped shared edge. Contact pairs may be intended coplanar shared walls; not penetration volume. Sparse sampling can miss localized intersections and BVH surface tests cannot detect wholly contained solids.','regional_geometry_modified':False}
(O/'context_mesh_check.json').write_text(json.dumps(report,indent=2))
for ob in keep:
 if ob.get('building_id') not in ['site-support','overture-part-f8bf5658-9a43-3a6c-a862-ad20426f4f84','overture-part-dfcdb3b0-d651-355b-bed0-8d4948217eea']:ob.hide_render=True
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('ContextWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.75,.8,.86,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.data.energy=2;bpy.context.object.rotation_euler=(.4,-.3,.6);target=Vector((297,-280,45));bpy.ops.object.camera_add(location=target+Vector((-120,-170,150)));s.camera=bpy.context.object;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=180;s.render.filepath=str(O/'context-review.png');bpy.ops.render.render(write_still=True)
print(json.dumps(rows,indent=2))
