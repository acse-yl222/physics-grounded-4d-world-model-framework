"""Photo-informed terminal study; dimensions inferred, no regional replacement."""
import bpy,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent/'input/canary_wharf_20261007'
OUT=ROOT/'exports/crossrail-photo-study-001';OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(ROOT/'src'))
from buildings.crossrail_diagrid_candidate import mesh_data
from buildings.crossrail_partial_assembly import slab_mesh
rep=json.loads((ROOT/'references/crossrail_lidar_review.json').read_text()); geo=json.loads((ROOT/'geometry.json').read_text()); feature=next(x for x in geo['buildings'] if x['id']==rep['building_id'])
u=Vector((*rep['axis_local_xy'],0));vv=Vector((-u.y,u.x,0));center=Vector((*rep['mapped_part_extent']['centroid_local_xy'],0));fit=rep['upper_envelope_circle_fit'];r=fit['radius_m'];zc=fit['circle_center_z_odn_m']-rep['ground_scalar_m_odn'];bc=fit['cross_axis_center_m']
def xyz(a,b,z):return center+a*u+b*vv+Vector((0,0,z))
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color,rough=.5,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
wood=mat('Photo-supported warm timber, approximate tone',(.49,.29,.13));silver=mat('Photo-supported pale silver rim',(.48,.53,.54),.27,.7);dark=mat('Photo-supported dark lower panels',(.055,.067,.071),.6);deckmat=mat('Provisional terrace',(.33,.34,.31),.8)
objects=[]
def add(name,verts,faces,material):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material);ob['source_id']='pexels_tom_whyte_10391373';ob['accuracy']='Visual feature class supported; dimensions and layout estimated';objects.append(ob);return ob
v,f,p=mesh_data(feature);add('Existing estimated diagonal timber members',v,f,wood)
V=[];F=[]
def beam(a,b,width,depth):
 a,b=Vector(a),Vector(b);t=(b-a).normalized();side=t.cross(Vector((0,0,1))).normalized();normal=side.cross(t).normalized();start=len(V)
 for q in [a,b]:
  for sw,sd in [(-1,-1),(1,-1),(1,1),(-1,1)]:V.append(tuple(q+side*sw*width/2+normal*sd*depth/2))
 F.extend(tuple(start+i for i in face) for face in [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
# Third grid direction: joins existing inferred nodes, visible triangles supported by photo.
endpoints=p['members_endpoints'];nodes={tuple(round(c,6) for c in q) for edge in endpoints for q in edge};rows={}
for q in nodes:
 b=(Vector(q)-center).dot(vv);rows.setdefault(round(b,4),[]).append(q)
count=0
for row in rows.values():
 row.sort(key=lambda q:(Vector(q)-center).dot(u))
 for a,b in zip(row,row[1:]):
  if 5.95<math.dist(a,b)<6.05:beam(a,b,.20,.36);count+=1
add('Photo-supported third timber direction, inferred positions',V,F,wood)
# East terminal silver rim represented on inward raked plane; all plan coordinates
# deliberately within mapped central part. Not a surveyed terminal overhang.
amin=rep['mapped_part_extent']['long_axis_range_m'][0];V=[];F=[]
angles=[-.77+1.54*i/80 for i in range(81)]
points=[]
for angle in angles:
 b=bc+r*math.sin(angle);z=zc+r*math.cos(angle);a=amin+1.2+(fit['apex_scene_z_m']-z)*.45;points.append(xyz(a,b,z))
for a,b in zip(points,points[1:]):beam(a,b,.46,.55)
add('Silver terminal arch, estimated rake and section',V,F,silver)
# Three dark inset banks visible below terrace; with real geometric border bars.
# Only shallow panels, never falsely extruded to a full station wall.
V=[];F=[]
for i in range(3):
 left=-10.5+i*7.0;right=left+6.5;low=5.4;high=12.9
 a=xyz(amin+8,left,low);b=xyz(amin+8,right,low);c=xyz(amin+5,right,high);d=xyz(amin+5,left,high)
 idx=len(V);V.extend(map(tuple,[a,b,c,d]));F.append((idx,idx+1,idx+2,idx+3))
add('Three observed lower dark banks, approximate geometry',V,F,dark);V=[];F=[]
for i in range(3):
 left=-10.5+i*7.;right=left+6.5;corners=[xyz(amin+8,left,5.4),xyz(amin+8,right,5.4),xyz(amin+5,right,12.9),xyz(amin+5,left,12.9)]
 for a,b in zip(corners,corners[1:]+corners[:1]):beam(a,b,.22,.25)
add('Pale panel borders, inferred dimensions',V,F,silver)
surfaces=json.loads((ROOT/'references/crossrail_assembly_surfaces.json').read_text());d=surfaces['deck'];v,f=slab_mesh(feature,d['top_scene_z_m'],d['thickness_m_estimated']);add('Existing provisional deck',v,f,deckmat)
# Existing measured roof remains independent; no interpolation across missing LiDAR cells.
roofmat=mat('Measured roof patches, subdued off-white',(.71,.74,.70),.46)
record=surfaces['features'][feature['id']];add('Retained measured roof patches',record['vertices'],record['faces'],roofmat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Soft studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.52,.58,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
light=bpy.data.lights.new('Sun','SUN');light.energy=2;light.angle=.25;lo=bpy.data.objects.new('Sun',light);scene.collection.objects.link(lo);lo.rotation_euler=(.4,-.6,-.7)
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
for label,a,b,z,targeta,targetz,scale in [('terminal',amin-48,-37,24,amin+8,15,64),('roof',-20,-120,150,0,15,315)]:
 cam.location=xyz(a,b,z);target=xyz(targeta,0,targetz);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=scale
 if label=='terminal':
  bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'crossrail-study.blend'),compress=False)
  bpy.ops.object.select_all(action='DESELECT')
  for ob in objects:ob.select_set(True)
  bpy.ops.export_scene.gltf(filepath=str(OUT/'crossrail-study.glb'),export_format='GLB',use_selection=True,export_draco_mesh_compression_enable=False)
 scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
expected=sum(sum(len(poly.vertices)-2 for poly in ob.data.polygons) for ob in objects);names=[o.name for o in objects]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'crossrail-study.blend'));assert all(n in bpy.data.objects for n in names)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'crossrail-study.glb'));actual=sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH');assert actual==expected
report={'source_id':'pexels_tom_whyte_10391373','attribution':'Tom Whyte / Pexels','url':'https://www.pexels.com/photo/building-in-canary-wharf-business-complex-in-london-10391373/','license_url':'https://www.pexels.com/license/','actually_inspected':True,'capture_date':None,'texture_export':'none; original photo not bundled','observations':['Triangular timber grid visible beneath terminal roof','Silver thick curved terminal rim','Three dark inclined lower banks with pale framing below terrace'],'changes':['Added third timber direction using existing inferred nodes','Added estimated silver arch within central mapped part','Added three shallow dark panel banks and geometric borders'],'third_direction_members':count,'limitations':['Terminal rake and all new dimensions inferred; original shape not metrically recovered','Mapped central part only; terminal ownership extent preserved by inward placement, actual overhang not calibrated','Terminal lower wall coverage partial; no signage, glazing detail, stairs or foundations','Roof patches retain LiDAR gaps; no complete membrane invented'],'master_reopened':True,'glb_triangles_checked':actual,'visual_reviewed':False}
(OUT/'observation-review.json').write_text(json.dumps(report,indent=2)+'\n')
print('CROSSRAIL_PHOTO_STUDY_VERIFIED',actual)
