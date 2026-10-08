import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';REG=Path(__file__).resolve().parent/'runs/canary_wharf_appearance_owner407_001/region.blend';O=R/'exports/owner836-roof-study-001';D=json.loads((R/'references/owner836_authoring001.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(REG));dlr=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 props=str(dict(o.items()));name=o.name.lower()
 if ('7d217ccd' in props or '95a2d5db' in props):dlr.append(o)
print('NEIGHBORCOUNT',len(dlr),flush=True)
# Pure geometric membership in source zones, no third-party triangulation assumptions.
def inring(x,y,pts):
 c=False
 for a,b in zip(pts,pts[1:]+pts[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c
def distance2d(x,y,pts):
 best=1e30
 for a,b in zip(pts,pts[1:]+pts[:1]):
  dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0;best=min(best,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
 return best
def penetration(v):
 x,y,z=v;best=0
 for zone in D['zones']:
  if z<=0 or z>=zone['height_m']:continue
  for g in zone['geometry']:
   if inring(x,y,g['outer']) and not any(inring(x,y,h) for h in g['holes']):
    dd=min([distance2d(x,y,g['outer'])]+[distance2d(x,y,h) for h in g['holes']]);best=max(best,min(dd,z,zone['height_m']-z))
 return best
with bpy.data.libraries.load(str(O/'owner836.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('Office836 roof zone')]
new=[o for o in dst.objects if o]
for o in new:bpy.context.scene.collection.objects.link(o)
def worldmesh(o):
 o.data.calc_loop_triangles();v=[o.matrix_world@p.co for p in o.data.vertices];f=[tuple(t.vertices) for t in o.data.loop_triangles];return v,f
nw=[(o,*worldmesh(o)) for o in new];nb=[(o,BVHTree.FromPolygons(v,f,all_triangles=True)) for o,v,f in nw];rows=[]
for o in dlr:
 v,f=worldmesh(o);mins=[min(q[i] for q in v) for i in range(3)];maxs=[max(q[i] for q in v) for i in range(3)]
 if maxs[0]<-360 or mins[0]>-175 or maxs[1]<-320 or mins[1]>-190:continue
 tree=BVHTree.FromPolygons(v,f,all_triangles=True);cross={n.name:len(tree.overlap(b)) for n,b in nb};samples=list(v)
 for face in f:
  a,b,c=[v[k] for k in face];samples.append((a+b+c)/3)
  for p,q in [(a,b),(b,c),(c,a)]:
   steps=min(100,max(1,math.ceil((q-p).length)))
   samples.extend(p.lerp(q,i/steps) for i in range(1,steps))
 depths=[penetration(q) for q in samples];deep=[(dep,tuple(q)) for dep,q in zip(depths,samples) if dep>.05];deep.sort(reverse=True)
 rows.append({'object':o.name,'building_id':o.get('building_id'),'source_owner_ids':list(o.get('source_owner_ids',[])),'bounds':[mins,maxs],'triangle_surface_cross_pairs':cross,'sample_count':len(samples),'samples_inside_gt5cm':len(deep),'max_interior_depth_m':max(depths,default=0),'worst_samples':deep[:8]});print(o.name,len(deep),max(depths,default=0),cross,flush=True)
rep={'region_file':str(REG),'candidate_file':str(O/'owner836.blend'),'method':'Actual world-space retained west and east campus neighbor meshes: BVH triangle-surface intersection plus vertices/triangle-centroids/edge samples <=1m spacing (100steps cap) tested within candidate closed roof prisms. Interior depth is min roof/ground/zone-plan boundary distance; excludes touches<=5cm. Sampling not exact volume Boolean.','neighbor_objects_identified':len(dlr),'near_interface_rows':rows,'max_penetration_m':max([r['max_interior_depth_m'] for r in rows],default=0),'geometry_modified':False};(R/'references/owner836_interface001.json').write_text(json.dumps(rep,indent=2));print('DONE',flush=True)
OUT=R/'exports/owner836-interface-001';OUT.mkdir(exist_ok=True)
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.hide_render=o not in dlr+new
for o in new:
 m=bpy.data.materials.new('Diagnostic new Cabot West blue');m.diffuse_color=(.15,.35,.6,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.15,.35,.6,1);o.data.materials.clear();o.data.materials.append(m)
 for face in o.data.polygons:face.material_index=0
camd=bpy.data.cameras.new('Interface diagnostic camera');cam=bpy.data.objects.new('Interface diagnostic camera',camd);bpy.context.collection.objects.link(cam);scene=bpy.context.scene;scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
for name,pos,target,scale in [('interface-overview',(-360,-320,130),(-270,-250,25),190)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=scale;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)

import hashlib
rep['input_sha256']={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [REG,O/'owner836.blend',O/'owner836.glb',R/'references/owner836_authoring001.json']}
rep['classification']='Boundary contacts; no sampled interior deeper than5cm. See measured maximum depth in report. No exact volume Boolean claimed.'
rep['render_visual_reviewed']=False
bpy.ops.wm.open_mainfile(filepath=str(REG))
rep['target_native_metadata']=[{'name':o.name,'properties':{k:str(v) for k,v in o.items()},'max_z_m':max((o.matrix_world@v.co).z for v in o.data.vertices)} for o in bpy.data.objects if o.type=='MESH' and '8360e6b8' in str(dict(o.items()))]
(R/'references/owner836_interface001.json').write_text(json.dumps(rep,indent=2))
