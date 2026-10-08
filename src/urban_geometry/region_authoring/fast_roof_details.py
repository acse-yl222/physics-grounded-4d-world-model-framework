"""Small estimated flat-roof plant clusters. Blender CLI: -- config.json.
Config source_blend/source_sha256/load_names, targets[{id,owner_id,object_names}],
output_dir, optional preview. Native source unchanged; additive candidate.blend.
Footprints are checked by clipped horizontal triangle area, dense support rays and
existing-object AABBs. No imagery, measured plant claim, parapet or roof replacement.
"""
import importlib.util,json,math,sys,time,datetime,signal,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
O=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fast_exterior',O/'fast_exterior.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)

def clip(poly,axis,bound,sign):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=sign*(a[axis]-bound)>=0;ib=sign*(b[axis]-bound)>=0
  if ia:out.append(a)
  if ia!=ib:
   f=(bound-a[axis])/(b[axis]-a[axis]);out.append((a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])))
 return out

def area(poly):
 return abs(sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>2 else 0

def run(config):
 out=Path(config['output_dir']);out.mkdir(parents=True,exist_ok=True);start=time.monotonic();bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(config['source_blend'],link=False)as(a,b):b.objects=list(config['load_names'])
 for ob in b.objects:
  if ob is None:raise ValueError('Missing configured source object')
  bpy.context.collection.objects.link(ob)
 bpy.context.view_layer.update();originals=list(b.objects);records=[F.geometry_record(o)for o in originals if o.type=='MESH'];materials={'curb':F.material('Estimated roof curb',(.30,.32,.32),.15,.65),'plant':F.material('Estimated roof muted metal',(.43,.47,.47),.5,.38),'louver':F.material('Estimated roof dark louvres',(.13,.17,.17),.6,.4)};reports=[];added=[];previews=[]
 family_spent=dict(config.get('prior_family_seconds',{}))
 for target in config['targets']:
  begun=time.monotonic();objects=[];proof=[];status='skipped_no_safe_cluster';why=None;family_id=target.get('family_id',target['id']);prior_seconds=float(family_spent.get(family_id,0));remaining=59.-prior_seconds
  def alarm(*a):raise F.BudgetExpired()
  prev=signal.signal(signal.SIGALRM,alarm)
  try:
   if remaining<=.001:raise F.BudgetExpired()
   signal.setitimer(signal.ITIMER_REAL,remaining)
   candidates=[]
   for name in target['object_names']:
    rec=next(r for r in records if r['object'].name==name);ob=rec['object'];ob.data.calc_loop_triangles()
    assert ob.get('building_id')==target['owner_id']
    tris=[]
    for tri in ob.data.loop_triangles:
     vs=[rec['vertices'][i]for i in tri.vertices];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]);ar=normal.length/2
     if ar>.01 and normal.normalized().z>.9999 and max(v.z for v in vs)-min(v.z for v in vs)<.001 and abs(vs[0].z-target.get('topheight',rec['hi'].z))<.01:tris.append((vs,ar))
    seen_levels=set()
    for vs,ar in sorted(tris,key=lambda x:-x[1])[:24]:
     z=sum(v.z for v in vs)/3;level=[v for v,a in tris if abs(v[0].z-z)<.001]
     edges={}
     for triangle in level:
      for a,b in zip(triangle,triangle[1:]+triangle[:1]):
       key=tuple(sorted((tuple(round(c,4)for c in a),tuple(round(c,4)for c in b))))
       if key in edges:edges[key]=None
       else:edges[key]=b-a
     boundary=[e for e in edges.values()if e is not None]
     if not boundary:continue
     edge=max(boundary,key=lambda e:e.length);t=Vector((edge.x,edge.y,0)).normalized();n=Vector((t.y,-t.x,0));center=sum(vs,Vector())/3;center.z=0
     if round(z,3)not in seen_levels:
      weighted=[(tri,a)for tri,a in tris if abs(tri[0].z-z)<.001];total=sum(a for tri,a in weighted);centroid=sum((sum(tri,Vector())/3*a for tri,a in weighted),Vector())/total;centroid.z=0
      allvs=[v for tri in level for v in tri];bbox=Vector(((min(v.x for v in allvs)+max(v.x for v in allvs))/2,(min(v.y for v in allvs)+max(v.y for v in allvs))/2,0))
      candidates.extend([(rec,level,centroid,t,n,z,ar),(rec,level,bbox,t,n,z,ar)]);seen_levels.add(round(z,3))
     candidates.append((rec,level,center,t,n,z,ar))
   variants=[(item,False)for item in candidates]
   if config.get('allow_compact',False):variants += [(item,True)for item in candidates]
   for item,compact in variants:
    rec,tris,C,T,N,z,ar=item
    # The one modest cluster occupies7x4m; check8.6x5.6m support/setback.
    local=[[(T.dot(v-C),N.dot(v-C))for v in tri]for tri in tris];rect=(-2.,2.,-2.,2.) if compact else (-4.3,4.3,-2.8,2.8);covered=0
    for poly in local:
     for axis,bound,sign in [(0,rect[0],1),(0,rect[1],-1),(1,rect[2],1),(1,rect[3],-1)]:poly=clip(poly,axis,bound,sign)
     covered+=area(poly)
    expected=(rect[1]-rect[0])*(rect[3]-rect[2])
    if abs(covered-expected)>.0005:continue
    supported=True
    for i in range(10):
     for j in range(7):
      p=C+T*(rect[0]+i*(rect[1]-rect[0])/9)+N*(rect[2]+j*(rect[3]-rect[2])/6)+Vector((0,0,z+.2));q,no,idx,dist=rec['tree'].ray_cast(p,Vector((0,0,-1)),.4)
      if q is None or abs(dist-.2)>.0001 or no.z<.999:supported=False;break
     if not supported:break
    if not supported:continue
    corners=[C+T*x+N*y+Vector((0,0,zz))for x in ([-1.35,1.35] if compact else [-3.6,3.6])for y in ([-1.35,1.35] if compact else [-2.,2.])for zz in [z+.001,z+1.5]];lo=[min(v[k]for v in corners)for k in range(3)];hi=[max(v[k]for v in corners)for k in range(3)]
    blockers=[r['object'].name for r in records if r['object'].name!=rec['object'].name and all(r['hi'][k]>lo[k]+.002 and r['lo'][k]<hi[k]-.002 for k in range(3))]
    if blockers:continue
    buffers={}
    # Two aligned HVAC-like boxes; two shorter vent housings, no random scatter.
    depth=1.0 if compact else 1.4
    for x0,x1 in ([(-1.1,1.1)] if compact else [(-3.1,-.6),(.6,3.1)]):
     F.add_box(buffers,'curb',C,T,N,x0-.12,x1+.12,z,z+.16,-depth-.12,depth+.12)
     F.add_box(buffers,'plant',C,T,N,x0,x1,z+.16,z+1.25,-depth,depth)
     for k in range(5):
      zz=z+.35+k*.155;F.add_box(buffers,'louver',C,T,N,x0+.16,x1-.16,zz,zz+.055,-depth-.06,-depth+.005)
     F.add_box(buffers,'plant',C,T,N,x0+.65,x1-.65,z+1.25,z+1.43,-.6,.6)
     F.add_box(buffers,'louver',C,T,N,x0+.57,x1-.57,z+1.43,z+1.49,-.68,.68)
    for kind,(vs,fs)in buffers.items():
     name='RoofEstimated_'+hashlib.sha256(target['id'].encode()).hexdigest()[:12]+'_'+kind;me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);objects.append(ob);me.materials.append(materials[kind]);ob['building_id']=target['owner_id'];ob['research_object_id']='roof-estimated-v1::'+target['id']+'::'+kind;ob['basis']='Estimated low-density roof plant/curbs/louvres; not observed equipment';assert all(math.isfinite(c)for v in me.vertices for c in v.co);assert len(me.polygons)*4==len(me.vertices)*3
    proof={'source_object':rec['object'].name,'roof_z':z,'center':list(C),'t':list(T),'n':list(N),'support_rectangle':rect,'clipped_roof_triangle_area':covered,'expected_area':expected,'dense_horizontal_support_rays':70,'existing_AABB_obstacle_hits':blockers,'height_above_roof':1.49,'variant':'compact_one_unit' if compact else 'standard_two_units','cluster_footprint_m':[2.44,2.24] if compact else [6.44,3.04]};status='built';previews.append(proof);break
  except F.BudgetExpired:
   status='skipped_timeout'
   for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
   objects=[]
  except Exception as exc:
   status='skipped_error';why=repr(exc)
   for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
   objects=[]
  finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prev)
  elapsed=time.monotonic()-begun;family_spent[family_id]=prior_seconds+elapsed
  added+=objects;reports.append({'id':target['id'],'family_id':family_id,'family_cumulative_seconds':family_spent[family_id],'owner_id':target['owner_id'],'status':status,'error':why,'elapsed_seconds':elapsed,'budget_seconds':60,'add_names':[o.name for o in objects],'support':proof})
 if config.get('preview') and previews:
  p=previews[0];C=Vector(p['center'])+Vector((0,0,p['roof_z']));s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('roof review');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;bpy.ops.object.light_add(type='SUN');bpy.context.object.rotation_euler=(.3,-.5,.3);bpy.context.object.data.energy=2;bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.location=C+Vector(p['t'])*6-Vector(p['n'])*8+Vector((0,0,10));s.camera.rotation_euler=(C-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=12;s.render.filepath=str(out/'roof-preview.png');bpy.ops.render.render(write_still=True)
 for ob in originals:bpy.data.objects.remove(ob,do_unlink=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out/'candidate.blend'),compress=False)
 result={'source_blend':config['source_blend'],'source_sha256':config.get('source_sha256'),'targets':reports,'family_generation_seconds':family_spent,'replace_names':[],'add_names':[o.name for o in added],'source_geometry_unchanged':True,'total_with_IO_preview_seconds':time.monotonic()-start,'candidate_sha256':hashlib.sha256((out/'candidate.blend').read_bytes()).hexdigest(),'limitations':'Estimated roof plant only. Native Ccalls may defer SIGALRM; actual target elapsed reported. Horizontal support uses clipped native roof triangles plus70rays over larger setback rectangle. No measured equipment claim.'};(out/'summary.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':run(json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text()))
