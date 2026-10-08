import bpy,json,sys,math,shutil
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/water15-roof-study-001';O.mkdir(parents=True,exist_ok=False);D=json.loads((R/'references/water15_authoring001.json').read_text());ID=D['building_id'];sys.path.insert(0,str(R/'src'))
from buildings.crossrail_partial_assembly import slab_mesh
bpy.ops.wm.read_factory_settings(use_empty=True);pts=[p for t in D['zones'] for g in t['geometry'] for p in g['outer']];C=Vector((sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts),0));U=Vector((1,0,0));V=Vector((0,1,0))
def pt(a,b,z):return C+Vector((a,b,z))
def mat(n,c,rough=.5):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;return m
glass=mat('Deep grey recessed windows',(.075,.10,.105),.28);stone=mat('Neutral brick massing proxy',(.33,.20,.16),.7);piermat=mat('Brown grey upper piers',(.31,.28,.23),.72);roofmat=mat('Plain unknown roof surface',(.25,.27,.25),.8);obs=[];current=None

def mesh(n,v,f,m,scope):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(p) for p in v],[],f);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['building_id']=current or ID;ob['source_owner_ids']=[ID];ob['parent_group_id']=ID;ob['scope']=scope;ob['epoch_scope']='DSM-era candidate; final present-day roof unverified';obs.append(ob);return ob
verts=[];faces=[]
def beam(a,b,w,h):
 t=(b-a).normalized();side=t.cross(Vector((0,0,1)))
 if side.length<.01:side=U.copy()
 side.normalize();normal=side.cross(t).normalized();k=len(verts)
 for p in (a,b):
  for sw,sh in ((-1,-1),(1,-1),(1,1),(-1,1)):verts.append(p+side*sw*w/2+normal*sh*h/2)
 faces.extend(tuple(k+x for x in f) for f in ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,3,7,6),(3,0,4,7)))
def flush(n,m,scope):
 global verts,faces
 if verts:mesh(n,verts,faces,m,scope)
 verts=[];faces=[]
for number,t in enumerate(D['zones']):
 current=ID;h=t['height_m'];v=[];f=[]
 for part in t['geometry']:
  pv,pf=slab_mesh({'geometry':[part]},h,h);off=len(v);v.extend(pv);f.extend([[i+off for i in face] for face in pf])
 ob=mesh('15WaterStreet roof zone '+str(t['label']),v,f,stone,'DSM spatial roof massing only; zone boundaries estimated; no transferred facade')
 ob.data.materials.append(roofmat)
 for p in ob.data.polygons:
  if p.normal.z>.9:p.material_index=1
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.57,.64,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2;ld.angle=.2;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.3,-.5,-.8)
camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,tz,scale in [('photo-side',-115,15,95,36,125),('roof',-70,-70,140,35,120),('rear-unverified',100,-30,65,25,110)]:
 cam.location=pt(a,b,z);target=pt(0,0,tz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=scale
 if label=='photo-side':
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'water15.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for ob in obs:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'water15.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
ids=[o.name for o in obs];count=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs);bounds={o.name:[[min(v.co[i] for v in o.data.vertices) for i in range(3)],[max(v.co[i] for v in o.data.vertices) for i in range(3)]] for o in obs}
bpy.ops.wm.open_mainfile(filepath=str(O/'water15.blend'));assert all(n in bpy.data.objects for n in ids);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'water15.glb'));ms=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert sorted(o.name for o in ms)==sorted(ids);assert sum(len(o.data.polygons) for o in ms)==count
report={'building_id':ID,'source_owner_ids':[ID],'native_reopened':True,'glb_ids_triangles_verified':True,'triangles':count,'objects':ids,'bounds_enu_m':bounds,'height_scope':'Original DSM zone medians ODN minus shared4.28000021m; flat scene base remains0','geometry_scope':'Roof massing only, mapped full outline preserved; no facade reconstruction','zones':[{k:z[k] for k in ['label','height_m','roof_median_odn_m','area_m2','stable_residual_p95_m']} for z in D['zones']],'unverified':D['unverified'],'visual_reviewed':False};(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(__file__,O/'source.py');print('TWENTY_CABOT_VERIFIED',count)
