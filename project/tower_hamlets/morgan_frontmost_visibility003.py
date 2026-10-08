import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-frontmost-registration-003';bpy.ops.wm.open_mainfile(filepath=str(R/'exports/morgan_south-facade-001/morgan_south.blend'))
for o in list(bpy.data.objects):
 if o.type=='MESH' and o.name.startswith('morgan_south_'):bpy.data.objects.remove(o,do_unlink=True)
reg=json.loads((R/'exports/morgan-facade-registration-002/proposal.json').read_text());g=json.loads((R/'geometry.json').read_text())['buildings'];ring=next(b for b in g if 'b317a51d' in b['id'])['geometry'][0]['outer'];fits=json.loads((O/'hypothesis-fits.json').read_text());rows=[];dg=bpy.context.evaluated_depsgraph_get()
for edge in [5,7,8,13]:
 a=Vector(ring[edge]);b=Vector(ring[(edge+1)%len(ring)]);v=(b-a).normalized();n=Vector((v.y,-v.x))
 for cam_name,cp in [('prior_fixed',reg['camera_preserved']),('exploratory_refit',next(f['camera'] for f in fits if f['edge']==edge))]:
  camera=Vector(cp[:3]);samples=[]
  for t in [.1,.3,.5,.7,.9]:
   for z in [11,17,24,28]:
    xy=a.lerp(b,t)+n*.001;p=Vector((xy.x,xy.y,z));dv=p-camera;hit,loc,nor,ix,obj,mat=bpy.context.scene.ray_cast(dg,camera,dv.normalized(),distance=dv.length+.05);delta=(p-loc).length if hit else None;visible=(not hit) or delta<.10;samples.append({'edge_fraction':t,'z':z,'visible':visible,'hit_object':obj.name if obj else None,'hit_polygon':ix if hit else None,'hit_enu':list(loc) if hit else None,'distance_from_target_m':delta})
  rows.append({'edge':edge,'camera_type':cam_name,'camera':cp,'visible_samples':sum(s['visible'] for s in samples),'total':len(samples),'samples':samples})
(O/'visibility-gate.json').write_text(json.dumps({'source':'morgan_south-facade-001 body only, olddetails removed in memory; source unchanged','tests':rows},indent=2));print([(r['edge'],r['camera_type'],r['visible_samples']) for r in rows])
