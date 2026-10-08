"""5 Canada Square from its own footprint, photo hierarchy and DSM modes."""
import bpy,json,sys,math,shutil
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/five-canada-study-003';O.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(R/'src'))
from buildings.crossrail_partial_assembly import slab_mesh
D=json.loads((R/'references/five_canada_roof_review.json').read_text());feature=D['source_geometry'];ID=feature['id'];C=Vector((*D['centroid_enu_xy'],0));U=Vector((*D['axis_u_xy'],0));V=Vector((*D['axis_v_xy'],0));ring=[Vector((*p,0)) for p in feature['geometry'][0]['outer']];aa=[(p-C).dot(U) for p in ring];bb=[(p-C).dot(V) for p in ring];amin,amax=min(aa),max(aa);bmin,bmax=min(bb),max(bb)
bpy.ops.wm.read_factory_settings(use_empty=True)
def pt(a,b,z):return C+U*a+V*b+Vector((0,0,z))
def mat(n,col,rough=.5,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*col,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
glass=mat('Muted blue grey glazing observed',(.19,.30,.33),.24,.2);silver=mat('Pale projecting frame observed',(.55,.61,.60),.4,.5);neutral=mat('Unobserved facade baseline',(.24,.29,.29));roof=mat('Unresolved occupied roof',(.26,.28,.27),.8)
obs=[]
def mesh(n,v,f,m,scope):
 me=bpy.data.meshes.new(n);me.from_pydata([tuple(p) for p in v],[],f);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']=scope;obs.append(ob);return ob
v,f=slab_mesh(feature,79.4,79.4);mesh('Mapped footprint main body',v,f,neutral,'Mapped full outline; occupied top79.4 inferred from lower DSM mode; no atrium carved without view')
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
 mesh(n,verts,faces,m,scope);verts=[];faces=[]
# Only northern and western exterior wall planes observed from reconstructed viewpoint.
area=sum(a.x*b.y-b.x*a.y for a,b in zip(ring,ring[1:]+ring[:1]))
for index,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
 delta=b-a;normal=Vector((delta.y,-delta.x,0)).normalized()*(1 if area>0 else -1);mid=(a+b)/2
 observed=normal.dot(-U)>.7 or normal.dot(-V)>.7
 if not observed:continue
 A=a+normal*.045;B=b+normal*.045
 mesh('Observed glazing elevation '+str(index),[A+Vector((0,0,5)),B+Vector((0,0,5)),B+Vector((0,0,79.35)),A+Vector((0,0,79.35))],[(0,1,2,3)],glass,'Photo supports north/west glazing; plane inset behind projecting frame. Entrance below5m unmodelled.')
 for j in range(16):
  z=5+j*(74.4/15);beam(A+normal*.13+Vector((0,0,z)),B+normal*.13+Vector((0,0,z)),.40,.35)
 for j in range(1,15):
  z=5+j*(74.4/15)+1.05;beam(A+normal*.10+Vector((0,0,z)),B+normal*.10+Vector((0,0,z)),.09,.10)
 count=max(1,round(delta.length/6.2))
 for j in range(count+1):
  q=A+(B-A)*j/count+normal*.23;beam(q+Vector((0,0,5)),q+Vector((0,0,79.4)),.52,.78)
  if j<count:
   for sub in (1/3,2/3):
    q=A+(B-A)*(j+sub)/count+normal*.10;beam(q+Vector((0,0,5)),q+Vector((0,0,79.4)),.09,.13)
flush('Observed frame hierarchy, dimensions estimated',silver,'Photo-supported floor bands, major piers, minor mullions; 15 divisions/source floors, counts and widths estimated')
# Setback upper volume from photograph; no fabricated hidden roof plant.
def box(n,a0,a1,b0,b1,z0,z1,m):
 v=[pt(a,b,z) for z in (z0,z1) for a,b in ((a0,b0),(a1,b0),(a1,b1),(a0,b1))];return mesh(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m,'Photo-supported setback upper storey; offset and height estimated from separated DSM modes')
box('Inset upper glazed storey',amin+3.2,amax-3.2,bmin+3.2,bmax-3.2,79.4,85.7,glass)
for a0,a1,b0,b1 in [(amin+3.2,amin+3.2,bmin+3.2,bmax-3.2),(amin+3.2,amax-3.2,bmin+3.2,bmin+3.2)]:
 A=pt(a0,b0,79.4);B=pt(a1,b1,79.4);N=round((B-A).length/2)
 for j in range(N+1):
  q=A+(B-A)*j/N;beam(q,q+Vector((0,0,6.3)),.38 if j%3==0 else .10,.5 if j%3==0 else .10)
 beam(A+Vector((0,0,3)),B+Vector((0,0,3)),.12,.14)
flush('Observed upper setback glazing divisions',silver,'Estimated spacing; photo-supported upper glazing, no hidden atrium geometry')
# Photo-supported projecting canopy extends estimated3m beyond mapped wall outline.
# Footprint wall geometry remains unchanged; canopy extent is separately estimated.
A0,A1=amin-3.,amax+3.;B0,B1=bmin-3.,bmax+3.
for a in (A0,A1):beam(pt(a,B0,87.45),pt(a,B1,87.45),.38,.5)
for b in (B0,B1):beam(pt(A0,b,87.45),pt(A1,b,87.45),.38,.5)
for j in range(1,math.ceil((A1-A0)/.95)):
 a=A0+j*.95
 if a>=A1:break
 beam(pt(a,B0,87.42),pt(a,B1,87.42),.12,.22)
for b in [B0+6.2*i for i in range(1,int((B1-B0)/6.2)+1)]:beam(pt(A0,b,87.10),pt(A1,b,87.10),.20,.35)
flush('Open projecting roof trellis',silver,'Photo-supported slatted overhang; pitch/section estimated. Mapped87.7 maximum retained; roof projection3m beyond mapped wall footprint estimated, not measured.')
# Replace rods outside the setback body with four attached roof supports.
# Match existing continuous transverse trellis beams exactly at two b-stations.
cross_b=[B0+6.2*i for i in range(1,int((B1-B0)/6.2)+1)]
support_b=[b for b in cross_b if bmin+4<=b<=bmax-4]
support_b=[support_b[0],support_b[-1]]
support_records=[]
for a in (amin+4,amax-4):
 for b in support_b:
  base=pt(a,b,85.55);top=pt(a,b,87.10);beam(base,top,.24,.24)
  assert amin+3.2+.12<a<amax-3.2-.12 and bmin+3.2+.12<b<bmax-3.2-.12
  assert any(abs(b-q)<1e-8 for q in cross_b)
  support_records.append({'base_enu':list(base),'top_enu':list(top),'base_embed_into_roof_m':.15,'top_crossbeam_center_z_m':87.1,'matched_transverse_beam_b_m':b})
flush('Estimated connected canopy supports',silver,'Estimated construction: bases embed0.15m into upper storey roof and tops meet existing transverse roof beams; not measured as-built supports')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.57,.64,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2;ld.angle=.2;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.3,-.5,-.8)
camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,tz,scale in [('northwest',-125,-120,65,44,130),('roof',-100,-90,170,65,115),('rear-unverified',110,110,75,45,130),('support-detail',amin-14,bmin-18,87,86,31)]:
 cam.location=pt(a,b,z);target=pt(amin+4,support_b[0],86) if label=='support-detail' else pt(0,0,tz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=scale
 if label=='northwest':
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'five-canada.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for ob in obs:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'five-canada.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
 scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
ids=[o.name for o in obs];count=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs);bounds={o.name:[[min(v.co[i] for v in o.data.vertices) for i in range(3)],[max(v.co[i] for v in o.data.vertices) for i in range(3)]] for o in obs}
bpy.ops.wm.open_mainfile(filepath=str(O/'five-canada.blend'));assert all(n in bpy.data.objects for n in ids);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'five-canada.glb'));ms=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert sorted(o.name for o in ms)==sorted(ids);assert sum(len(o.data.polygons) for o in ms)==count
report={'building_id':ID,'native_reopened':True,'glb_ids_triangles_verified':True,'triangles':count,'objects':ids,'bounds_enu_m':bounds,'height_treatment':'Mapped87.7 retained as total scene height above existing z0 baseline. Main79.4 and setback85.7 are shape estimates anchored to that total, informed by relative spacing of local DSM modes and photo proportions. LiDAR ground scalar6.171545m ODN is evidence normalization only, NOT a surveyed common regional datum or measured scene roof plane.','observed_scope':'TomWhyte northwest upperfacades and projecting trellis feature classes only','unverified':['South/east facades remain neutral baseline','No entrance/hidden stacked atrium invented','Roof equipment unknown','Frame subdivisions, roof pitch and structural supports estimated'],'structural_connection_checks':{'previous_issue':'Old support bases at originalwall corners were3.2m outside upper setback body and floating','four_supports':support_records,'all_bases_inside_upper_roof':True,'all_tops_match_existing_crossbeams':True,'construction_is_estimated_not_photo_measured':True},'visual_reviewed':False};(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(__file__,O/'source.py');print('FIVE_CANADA_VERIFIED',count)
