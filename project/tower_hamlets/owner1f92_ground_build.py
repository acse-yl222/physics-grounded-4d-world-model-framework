from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';O=R/'exports/owner1f92-ground-contact-001';d=json.load(open(O/'input.json'));src=S/'runs/canary_wharf_appearance_owner1f92_001/region.blend';sourcehash=hashlib.sha256(src.read_bytes()).hexdigest();bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(src)) as (a,b):b.objects=[n for n in a.objects if n in d['source_names']]
objs=[]
for o in b.objects:bpy.context.collection.objects.link(o);objs.append(o)
assert len(objs)==5
me=bpy.data.meshes.new('Native DTM triangles');me.from_pydata(d['vertices'],[],d['faces']);me.update();t=bpy.data.objects.new('Local measured DTM open surface',me);bpy.context.collection.objects.link(t);m=bpy.data.materials.new('Measured terrain');m.diffuse_color=(.3,.4,.25,1);me.materials.append(m);t['datum']=d['datum'];t['dtm_sha256']=d['dtm_sha256'];tb=BVHTree.FromPolygons([Vector(v) for v in d['vertices']],d['faces'],all_triangles=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('World');s.world.color=(.7,.7,.7)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));bpy.context.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=65
light=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun','SUN'));bpy.context.collection.objects.link(light);light.data.energy=3;light.rotation_euler=(.4,-.5,-.3)
target=Vector((-485,329,5));cam.location=target+Vector((-65,-85,38));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
def render(name):s.render.filepath=str(O/name);bpy.ops.render.render(write_still=True)
render('before.png');checks=[]
def distance(pt):
 vals=[]
 for aa,bb in d['footprint_segments']:
  a,b=Vector(aa),Vector(bb);v=b-a;f=max(0,min(1,(pt-a).dot(v)/v.length_squared));vals.append((pt-a-f*v).length)
 return min(vals)
for o in objs:
 print('PROCESS',o.name,flush=True);upper=sorted(set(tuple(v.co) for v in o.data.vertices if v.co.z>1e-5));
 if '00851081' in o.name:
  vs=[v.co.copy() for v in o.data.vertices];print('NEAREST',sorted(set(round(min((v-w).length for j,w in enumerate(vs) if i!=j),9) for i,v in enumerate(vs))),flush=True)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);print("INITIAL",o.name,len(bm.verts),len(bm.faces),{n:sum(len(e.link_faces)==n for e in bm.edges) for n in range(5)},flush=True)
 for e in list(bm.edges):
  if e.is_valid and all(abs(v.co.z)<1e-5 for v in e.verts):
   cuts=max(0,math.ceil(e.calc_length()/.1)-1)
   if cuts:bmesh.ops.subdivide_edges(bm,edges=[e],cuts=cuts,use_grid_fill=False)
 for v in bm.verts:
  if abs(v.co.z)<1e-5:
   w=o.matrix_world@v.co;hit=tb.ray_cast(Vector((w.x,w.y,50)),Vector((0,0,-1)),100)[0];assert hit is not None;v.co.z=hit.z-.03
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));print('NONMANIFOLD',sum(not e.is_manifold for e in bm.edges),flush=True);closed=all(e.is_manifold for e in bm.edges);assert closed or '00851081' in o.name;bm.to_mesh(o.data);bm.free();assert upper==sorted(set(tuple(v.co) for v in o.data.vertices if v.co.z>1e-5))
 gaps=[];internal=[]
 for edge in o.data.edges:
  a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
  if a.z<0 and b.z<0:
   arr=gaps if distance(Vector(((a.x+b.x)/2,(a.y+b.y)/2)))<.0001 else internal
   for i in range(11):
    w=a.lerp(b,i/10);h=tb.ray_cast(Vector((w.x,w.y,50)),Vector((0,0,-1)),100)[0];assert h is not None;arr.append(w.z-h.z)
 checks.append({'name':o.name,'roof_upper_vertices_exactly_unchanged':True,'closed':closed,'inherited_open_upper_topology':not closed,'exterior_samples':len(gaps),'exterior_residual_minmax':[min(gaps),max(gaps)] if gaps else None,'exterior_positive':sum(v>1e-5 for v in gaps),'internal_cap_residual_minmax':[min(internal),max(internal)] if internal else None});assert not any(v>1e-5 for v in gaps)
 o['ground_contact']='Estimated lower walls extended to EA1m DTM minus0.03m display embed; roof unchanged; independent candidate, no regional seam integration'
render('after.png');cam.location=target+Vector((65,85,32));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();render('rear.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ground-contact.blend'));bpy.ops.object.select_all(action='DESELECT');expected={}
for o in objs+[t]:o.select_set(True);o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
bpy.ops.export_scene.gltf(filepath=str(O/'ground-contact.glb'),export_format='GLB',use_selection=True,export_extras=True);bpy.ops.wm.open_mainfile(filepath=str(O/'ground-contact.blend'));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'ground-contact.glb'));actual={o.name:len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'};assert actual==expected;assert hashlib.sha256(src.read_bytes()).hexdigest()==sourcehash
report={'source_native_sha256':sourcehash,'dtm_sha256':d['dtm_sha256'],'datum':d['datum'],'missing_terrain_projections':0,'source_unchanged':True,'native_reopened':True,'independent_glb_triangles_match':True,'checks':checks,'terrain':'Open native pixel-centre triangles bounded by union+3m; no skirts or invented ramps','embed_m':.03,'limits':['DTM1m and unknown capture epoch; wallbases estimated, not foundations','Internal bottomcap diagonals are not exterior ground contact','No original site merge; original horizontal slab differs from DTM by approximately1m','0085 retained9m roof preserved']};(O/'checks.json').write_text(json.dumps(report,indent=2));print('DONE',checks)
