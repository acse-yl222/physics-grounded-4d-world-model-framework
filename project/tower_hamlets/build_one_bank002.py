import bpy,json,math,sys,shutil
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/one-bank-photo-study-002';O.mkdir(exist_ok=False);D=json.loads((R/'references/207561_identity_audit.json').read_text());F=D['source_geometry'];ID=F['id'];P=[Vector((*p,0)) for p in F['geometry'][0]['outer']];C=P[3];U=(P[2]-C).normalized();V=(P[0]-C).normalized();W=(P[2]-C).length;L=(P[0]-C).length;curve=json.loads((R/'references/one_bank_curve002.json').read_text());levels=[(x[2],min(W,(Vector(x)-C).dot(U))) for x in curve['points']];levels[0]=(141.761015415,levels[0][1]);levels=list(reversed(levels));bpy.ops.wm.read_factory_settings(use_empty=True);obs=[]
def mat(n,color,metal=.0,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*color,1);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
glass=mat('Observed blue green western glass',(.065,.23,.285),.32,.28);dark=mat('Observed dark trading podium',(.10,.14,.16),.25,.35);silver=mat('Observed pale facade edge',(.48,.54,.56),.55,.3);neutral=mat('Unknown rear neutral glazing',(.18,.24,.25),.2,.4)
def pt(a,b,z):return C+U*a+V*b+Vector((0,0,z))
def mesh(n,verts,faces,m,scope):
 me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(m);ob['building_id']=ID;ob['source_owner_ids']=[ID];ob['scope']=scope;obs.append(ob);return ob
def loft(n,levs,mat,b0=0,b1=L,a0=0):
 verts=[pt(a,b,z) for z,w in levs for a,b in [(a0,b0),(w,b0),(w,b1),(a0,b1)]];faces=[(3,2,1,0)]
 for j in range(len(levs)-1):
  k=4*j
  for i in range(4):faces.append((k+i,k+(i+1)%4,k+4+(i+1)%4,k+4+i))
 k=4*(len(levs)-1);faces.append((k,k+1,k+2,k+3));return mesh(n,verts,faces,mat,'Photo-supported swept mass; dimensions and hidden faces estimated')
# Smooth interpolation of observed planar silhouette samples, not freehand curve.
from bisect import bisect_right
def width(z):
 i=max(0,min(len(levels)-2,bisect_right([a for a,b in levels],z)-1));za,wa=levels[i];zb,wb=levels[i+1];return wa+(wb-wa)*(z-za)/(zb-za)
levs=[(levels[0][0]+(levels[-1][0]-levels[0][0])*i/70,width(levels[0][0]+(levels[-1][0]-levels[0][0])*i/70)) for i in range(71)]
loft('OneBank upper swept body',levs,glass);loft('OneBank trading podium',[(8.5,W),(levels[0][0],W)],dark);loft('OneBank inset ground interface',[(0,W-5),(8.5,W-5)],neutral,4,L-4,4)
# Architectural divisions visible in photo; cadence/width are explicit estimates.
for z in [32.268+5.18*i for i in range(1,21)]:
 if z>=141.76:continue
 loft('OneBank subtle horizontal division '+str(round(z,2)),[(z,width(z)+.035),(z+.075,width(z+.075)+.035)],neutral)
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
report={'building_id':ID,'source_owner_ids':[ID],'identity':'One Bank Street','objects':[o.name for o in obs],'profile_levels_z_w':levels,'photo_observed':['West blue glazed facade curves outward toward trading podium','Pale continuous side edges','Dark low trading floors and inset ground frontage'],'estimated':['Camera fitted using other landmarks; no survey accuracy','South side plane assumed mapped boundary; lower silhouette clipped to mapped width produces~5px residual','North swept edge extrapolated behind Newfoundland occlusion','Rear and roof neutral; no inferred atrium cavities','Floor divisions5.18m estimated; ground inset4–5m and ground/podium interface8.5m estimated'],'vertical_datum':'Upperroof146.041015625ODN minus4.28000021; lowercurve heights solvedphoto-plane, not DSM ground returns','source_photo':'pexels-ollie-craig-11491155.jpeg','visual_reviewed':False};(O/'review.json').write_text(json.dumps(report,indent=2));shutil.copy2(__file__,O/'source.py')
