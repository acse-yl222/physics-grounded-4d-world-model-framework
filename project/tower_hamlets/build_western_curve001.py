import bpy,json,sys,math,shutil
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/western-curve-study-001';O.mkdir(parents=True,exist_ok=False);D=json.loads((R/'references/western_curve_authoring_input.json').read_text());ID='overture-building-'+D['parent_id'];sys.path.insert(0,str(R/'src'))
from buildings.crossrail_partial_assembly import slab_mesh
bpy.ops.wm.read_factory_settings(use_empty=True);pts=[p for t in D['territories'] for g in t['geometry'] for p in g['outer']];C=Vector((sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts),0));U=Vector((1,0,0));V=Vector((0,1,0))
def pt(a,b,z):return C+Vector((a,b,z))
def mat(n,c,rough=.5):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;return m
glass=mat('Deep grey recessed windows',(.075,.10,.105),.28);stone=mat('Warm pale stone bands',(.50,.47,.40),.7);piermat=mat('Brown grey upper piers',(.31,.28,.23),.72);roofmat=mat('Plain unknown roof surface',(.25,.27,.25),.8);obs=[];current=None

def mesh(n,v,f,m,scope):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(p) for p in v],[],f);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['building_id']=current or ID;ob['source_owner_ids']=D['source_owner_ids'];ob['parent_group_id']=ID;ob['scope']=scope;obs.append(ob);return ob
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
for number,t in enumerate(D['territories']):
 current=t['id'];h=t['height_m_estimated'];v,f=slab_mesh(t,h,h);ob=mesh('Tier '+str(number)+' nonoverlap body',v,f,glass,'Exact mapped nonoverlap territory, estimated DSM-normalized roof height; hidden facades unverified')
 ob.data.materials.append(roofmat)
 for p in ob.data.polygons:
  if p.normal.z>.9:p.material_index=1
 for edge in t['visible_facade_edges']:
  A=Vector((*edge['a'],0));B=Vector((*edge['b'],0));n=Vector((*edge['normal'],0));low=edge['exposed_low_m'];high=edge['high_m'];length=(B-A).length
  # Explicit masonry bars project from recessed glass envelope, preserving actual curve facets.
  levels=[z for z in [8.1+4.1*j for j in range(11)] if low+.1<z<high-.1]+[high-.2]
  for z in levels:beam(A+n*.17+Vector((0,0,z)),B+n*.17+Vector((0,0,z)),.34,.42 if z<high-.5 else .55)
  if low<.1:
   for z in (1.,8.1,12.2):
    if z<high:beam(A+n*.22+Vector((0,0,z)),B+n*.22+Vector((0,0,z)),.45,.64)
 flush('Tier '+str(number)+' horizontal cornices',stone,'Photo-supported horizontal stone hierarchy; widths and levels estimated')
 for edge in t['visible_facade_edges']:
  A=Vector((*edge['a'],0));B=Vector((*edge['b'],0));n=Vector((*edge['normal'],0));low=edge['exposed_low_m'];high=edge['high_m'];length=(B-A).length;count=max(1,round(length/2.6))
  for j in range(count+1):
   q=A+(B-A)*j/count+n*.19;beam(q+Vector((0,0,max(low,.5))),q+Vector((0,0,high-.2)),.33,.4)
   if j<count:
    mid=A+(B-A)*(j+.5)/count+n*.025;beam(mid+Vector((0,0,max(low,.5))),mid+Vector((0,0,high-.2)),.065,.08)
 flush('Tier '+str(number)+' window piers and mullions',piermat,'Photo-supported repetitive recessed windows; bay count estimated; shared lower walls omitted')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.57,.64,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2;ld.angle=.2;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.3,-.5,-.8)
camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,tz,scale in [('photo-side',-115,15,63,25,90),('roof',-70,-70,125,25,110),('rear-unverified',100,-30,65,25,110)]:
 cam.location=pt(a,b,z);target=pt(0,0,tz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=scale
 if label=='photo-side':
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'western-curve.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for ob in obs:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'western-curve.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
ids=[o.name for o in obs];count=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs);bounds={o.name:[[min(v.co[i] for v in o.data.vertices) for i in range(3)],[max(v.co[i] for v in o.data.vertices) for i in range(3)]] for o in obs}
bpy.ops.wm.open_mainfile(filepath=str(O/'western-curve.blend'));assert all(n in bpy.data.objects for n in ids);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'western-curve.glb'));ms=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert sorted(o.name for o in ms)==sorted(ids);assert sum(len(o.data.polygons) for o in ms)==count
report={'parent_id':ID,'source_owner_ids':D['source_owner_ids'],'native_reopened':True,'glb_ids_triangles_verified':True,'triangles':count,'objects':ids,'bounds_enu_m':bounds,'height_scope':D['roof_provenance'],'identity':'Western foreground candidate supported by camera depth and footprint silhouette; street-address naming not asserted','observed':['Curved polygonal west frontage','Stepping southern wing','Recessed dark glazing with stronger pale horizontal cornices and brown stone piers'],'estimated':['Roof heights localDSM normalized; common flatdatum assumption','Window count/pier widths/floor levels inferred','No hidden entrance or equipment or lighting fixtures fabricated'],'unverified':['Other elevations remain neutral dark baseline','No claim whole-building photo verification','Construction interfaces approximate'],'visual_reviewed':False};(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(__file__,O/'source.py');print('WESTERN_CURVE_VERIFIED',count)
