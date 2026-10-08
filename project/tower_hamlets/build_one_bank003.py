import bpy,json,math,sys,shutil
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/one-bank-photo-study-003';O.mkdir(exist_ok=False);D=json.loads((R/'references/207561_identity_audit.json').read_text());F=D['source_geometry'];ID=F['id'];P=[Vector((*p,0)) for p in F['geometry'][0]['outer']];C=P[3];U=(P[2]-C).normalized();V=(P[0]-C).normalized();W=(P[2]-C).length;L=(P[0]-C).length;curve=json.loads((R/'references/one_bank_curve002.json').read_text());levels=[(x[2],min(W,(Vector(x)-C).dot(U))) for x in curve['points']];levels[0]=(141.761015415,levels[0][1]);levels=list(reversed(levels));bpy.ops.wm.read_factory_settings(use_empty=True);obs=[]
def mat(n,color,metal=.0,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*color,1);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
glass=mat('Observed blue green western glass',(.065,.23,.285),.32,.28);dark=mat('Observed dark trading podium',(.10,.14,.16),.25,.35);silver=mat('Observed pale facade edge',(.48,.54,.56),.55,.3);neutral=mat('Unknown rear neutral glazing',(.18,.24,.25),.2,.4)
def pt(a,b,z):return C+U*a+V*b+Vector((0,0,z))
def mesh(n,verts,faces,m,scope):
 me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']=scope;obs.append(ob);return ob
def loft(n,levs,mat,b0=0,b1=L,a0=0):
 verts=[pt(a,b,z) for z,w in levs for a,b in [(a0,b0),(w-(.4 if n in ['OneBank upper swept body','OneBank trading podium'] else 0),b0),(w-(.4 if n in ['OneBank upper swept body','OneBank trading podium'] else 0),b1),(a0,b1)]];faces=[(3,2,1,0)]
 for j in range(len(levs)-1):
  k=4*j
  for i in range(4):
   faces.append((k+i,k+(i+1)%4,k+4+(i+1)%4,k+4+i))
 k=4*(len(levs)-1);faces.append((k,k+1,k+2,k+3));return mesh(n,verts,faces,mat,'Photo-supported swept mass; dimensions and hidden faces estimated')
# Smooth interpolation of observed planar silhouette samples, not freehand curve.
from bisect import bisect_right
def width(z):
 i=max(0,min(len(levels)-2,bisect_right([a for a,b in levels],z)-1));za,wa=levels[i];zb,wb=levels[i+1];return wa+(wb-wa)*(z-za)/(zb-za)
levs=[(levels[0][0]+(levels[-1][0]-levels[0][0])*i/70,width(levels[0][0]+(levels[-1][0]-levels[0][0])*i/70)) for i in range(71)]
loft('OneBank upper swept body',levs,glass);loft('OneBank trading podium',[(8.5,W),(levels[0][0],W)],dark);loft('OneBank inset ground interface',[(0,W-5),(8.5,W-5)],neutral,4,L-4,4)
# West-facing curtainwall only; bay count/depth estimated from actual licensed view.
frame=mat('Opaque dark teal curtainwall frames',(.105,.145,.155),.4,.31)
# Closed swept strip sections have outer frame projection and glass behind it.
def strip(n,zs,b0,b1,inset0,inset1,m):
 verts=[];faces=[]
 for z in zs:
  w=width(z)
  for aa,bb in [(w+inset0,b0),(w+inset1,b0),(w+inset1,b1),(w+inset0,b1)]:verts.append(pt(aa,bb,z))
 faces=[(3,2,1,0)]
 for j in range(len(zs)-1):
  for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,j*4+4+(i+1)%4,j*4+4+i))
 k=len(verts)-4;faces.append((k,k+1,k+2,k+3));return mesh(n,verts,faces,m,'Visible-west frame or inset opaque glass pane; bay count/depth estimated, no photo texture')
zs=[z for z,w in levs];baycount=26;bay=L/baycount
for j in range(baycount+1):
 b=j*bay;half=.05 if j%4==0 else .035
 strip('OneBank west vertical mullion '+str(j),zs,max(0,b-half),min(L,b+half),-.16,.12,frame)
floors=[levels[0][0]+(levels[-1][0]-levels[0][0])*i/21 for i in range(22)]
# Individual panels: every panel is recessed .24m behind the frame outer face.
for k,(za,zb) in enumerate(zip(floors[:-1],floors[1:])):
 panelzs=[za+.025]+[z for z in zs if za+.025<z<zb-.025]+[zb-.025]
 for j in range(baycount):strip('OneBank west inset panel %02d %02d'%(k,j),panelzs,j*bay+.055,(j+1)*bay-.055,-.18,-.12,glass)
for k,z in enumerate(floors[1:-1]):strip('OneBank west horizontal transom '+str(k),[z-.025,z+.025],0,L,-.15,.04,frame)
# Podium has three wider glazing rows and thirteen estimated bays, not tower cadence.
def podiumbox(n,a0,a1,b0,b1,z0,z1,m):
 vv=[pt(a,b,z) for z in [z0,z1] for a,b in [(a0,b0),(a1,b0),(a1,b1),(a0,b1)]]
 return mesh(n,vv,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m,'Photo-supported dark podium glazing hierarchy; bay13/row3 and sections estimated')
for j in range(14):
 b=j*L/13;podiumbox('OneBank podium vertical frame '+str(j),W-.28,W+.12,max(0,b-.14),min(L,b+.14),8.5,levels[0][0],frame)
for k,(za,zb) in enumerate(zip([8.5,16.1,24.2],[16.1,24.2,levels[0][0]])):
 for j in range(13):podiumbox('OneBank podium inset pane %d %d'%(k,j),W-.28,W-.2,j*L/13+.16,(j+1)*L/13-.16,za+.35,zb-.35,glass)
# Projecting pale continuous side edges, true thickness, follow identical sweep.
for b in [0,L-1.8]:
 verts=[];faces=[]
 for z,w in levs:
  for aa,bb in [(w-.24,b),(w+.10,b),(w+.10,b+1.8),(w-.24,b+1.8)]:verts.append(pt(aa,bb,z))
 faces=[(3,2,1,0)]
 for j in range(len(levs)-1):
  for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,j*4+4+(i+1)%4,j*4+4+i))
 k=len(verts)-4;faces.append((k,k+1,k+2,k+3));mesh('OneBank pale sweep edge '+str(round(b)),verts,faces,silver,'Observed pale side rim;0.34x1.8m section estimated from visible pale rim')
# Pale top cap and two broad dark podium spandrels seen in the west view.
loft('OneBank pale top rim',[(140.8,levels[-1][1]+.12),(141.761015415,levels[-1][1]+.12)],silver,a0=levels[-1][1]-.25)
for z in [16.1,24.2]:loft('OneBank podium horizontal band '+str(z),[(z,W+.10),(z+.65,W+.10)],neutral,a0=W-.15)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2;ld.angle=.2;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.3,-.5,-.8);camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);scene.collection.objects.link(cam);scene.camera=cam;center=pt(W/2,L/2,0)
for label,offset in [('photo-side',(-180,-30,135)),('roof',(-140,-100,230)),('rear-unverified',(130,30,145))]:
 cam.location=center+Vector(offset);target=center+Vector((0,0,65));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=185
 if label=='photo-side':
  bpy.ops.wm.save_as_mainfile(filepath=str(O/'one-bank.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT')
  for ob in obs:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(O/'one-bank.glb'),export_format='GLB',use_selection=True,export_extras=True)
 scene.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
a=json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf'];yaw,pitch,roll=a[3:6];fw=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)));right=Vector((math.sin(yaw),-math.cos(yaw),0));up=right.cross(fw);r=right*math.cos(roll)+up*math.sin(roll);u=-right*math.sin(roll)+up*math.cos(roll);cam.location=a[:3];cam.rotation_euler=Matrix((r,u,-fw)).transposed().to_euler();cam.data.type='PERSP';cam.data.sensor_width=36;cam.data.sensor_fit='HORIZONTAL';cam.data.lens=math.exp(a[6])*36/1921;scene.render.resolution_x=1921;scene.render.resolution_y=1280;scene.render.film_transparent=True;scene.render.filepath=str(O/'matched-camera.png');bpy.ops.render.render(write_still=True)
report={'building_id':ID,'source_owner_ids':[ID],'identity':'One Bank Street','objects':[o.name for o in obs],'profile_levels_z_w':levels,'photo_observed':['West blue glazed facade curves outward toward trading podium','Pale continuous side edges','Dark low trading floors and inset ground frontage'],'estimated':['Camera fitted using other landmarks; no survey accuracy','South side plane assumed mapped boundary; lower silhouette clipped to mapped width produces~5px residual','North swept edge extrapolated behind Newfoundland occlusion','Rear and roof neutral; no inferred atrium cavities','Floor divisions5.18m estimated; ground inset4–5m and ground/podium interface8.5m estimated'],'vertical_datum':'Upperroof146.041015625ODN minus4.28000021; lowercurve heights solvedphoto-plane, not DSM ground returns','source_photo':'pexels-ollie-craig-11491155.jpeg','curtainwall_estimates':{'west_bays':26,'west_rows':21,'glass_front_offset_m':-.12,'frame_front_offset_m':.12,'relative_recess_m':.24,'vertical_mullion_width_m':[.07,.10],'podium_bays':13,'podium_rows':3,'podium_recess_m':.32,'alpha':1.0,'material_mode':'Opaque procedural glazing proxy; no sunset-light patterns'},'visual_reviewed':False};(O/'review.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,O/'source.py')
