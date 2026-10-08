import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-south-facade-002';reg=json.loads((R/'exports/morgan-facade-registration-002/proposal.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'morgan_south002.blend'));s=bpy.context.scene;c=s.camera;cp=reg['camera_preserved'];yaw,pitch,roll=cp[3:6];fw=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)));r=Vector((math.sin(yaw),-math.cos(yaw),0));u=r.cross(fw);rr=r*math.cos(roll)+u*math.sin(roll);uu=-r*math.sin(roll)+u*math.cos(roll);c.location=cp[:3];c.rotation_euler=Matrix((rr,uu,-fw)).transposed().to_euler();c.data.type='PERSP';c.data.sensor_fit='HORIZONTAL';c.data.sensor_width=36;c.data.lens=math.exp(cp[6])*36/1368;c.data.shift_x=0;c.data.shift_y=0;s.render.resolution_x=1368;s.render.resolution_y=1824;bpy.context.view_layer.update();a=Vector(reg['edge13'][0]);b=Vector(reg['edge13'][1]);along=(b-a).normalized();normal=Vector((along.y,-along.x));dg=bpy.context.evaluated_depsgraph_get();rows=[]
for ss in [1,3,5,7,9,10.5]:
 for z in [11.5,17,24,27]:
  xy=a+along*ss+normal*.27;p=Vector((xy.x,xy.y,z));v=p-c.location;hit,loc,n,ix,obj,mat=s.ray_cast(dg,c.location,v.normalized(),distance=v.length+.01);nd=world_to_camera_view(s,c,p);d=p-c.location;analytic=[684+math.exp(cp[6])*d.dot(rr)/d.dot(fw),912-math.exp(cp[6])*d.dot(uu)/d.dot(fw)];rows.append({'s':ss,'z':z,'target_enu':list(p),'first_hit':obj.name if obj else None,'hit_enu':list(loc) if hit else None,'polygon_index':ix if hit else None,'hit_owner':obj.get('building_id') if obj else None,'hit_face_vertices_enu':[list(obj.matrix_world@obj.data.vertices[j].co) for j in obj.data.polygons[ix].vertices] if hit else None,'remaining_distance_m':(p-loc).length if hit else None,'blender_pixel':[nd.x*1368,(1-nd.y)*1824],'analytic_pixel':analytic})
(O/'visibility-diagnostic.json').write_text(json.dumps({'camera':cp,'rays':rows,'conclusion':'Check whether preservedbody occludes proposedface under fittedcamera; no geometry altered'},indent=2));print([(r['s'],r['z'],r['first_hit'],round(r['remaining_distance_m'],3) if r['remaining_distance_m'] else None) for r in rows])

G=json.loads((R/'geometry.json').read_text())['buildings'];ring=next(q for q in G if 'b317a51d' in q['id'])['geometry'][0]['outer'];mapping=[]
for row in rows:
 if not row['hit_enu']:continue
 p=Vector(row['hit_enu'][:2]);ds=[]
 for i,aa in enumerate(ring):
  aa=Vector(aa);bb=Vector(ring[(i+1)%len(ring)]);dv=bb-aa;t=max(0,min(1,(p-aa).dot(dv)/dv.length_squared));ds.append(((p-(aa+t*dv)).length,i))
 row['nearest_mapped_edge']=min(ds)[1];row['mapped_edge_distance_m']=min(ds)[0]
(O/'visibility-diagnostic.json').write_text(json.dumps({'camera':cp,'rays':rows,'max_camera_projection_error_px':max(abs(r['blender_pixel'][i]-r['analytic_pixel'][i]) for r in rows for i in range(2)),'conclusion':'Preservedbody physically occludes most edge13; this is not camera conversion mismatch.'},indent=2));print('edgehits',[(r['s'],r.get('nearest_mapped_edge'),r['hit_enu']) for r in rows[::4]])
