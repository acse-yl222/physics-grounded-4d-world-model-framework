import bpy,bmesh,json
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/twenty-cabot-photo-study-001';out={}
for state,path in [('before',R/'exports/twenty-cabot-roof-study-002/twenty-cabot.blend'),('after',O/'twenty_cabot.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));roofs={};frames=[]
 for ob in bpy.data.objects:
  if ob.type!='MESH':continue
  if ob.name.startswith('20Cabot roof zone'):
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.normal_update()
   for f in bm.faces:
    if f.normal.z>.99 and min(v.co.z for v in f.verts)>44.3:roofs.setdefault(str(round(sum(v.co.z for v in f.verts)/len(f.verts),4)),[]).append([[float(v.co.x),float(v.co.y)] for v in f.verts])
   bm.free()
  if ob.name=='TwentyCabot_frame':
   bm=bmesh.new();bm.from_mesh(ob.data);pending=set(bm.verts)
   while pending:
    seed=pending.pop();vs={seed};stack=[seed]
    while stack:
     v=stack.pop()
     for e in v.link_edges:
      w=e.other_vert(v)
      if w in pending:pending.remove(w);vs.add(w);stack.append(w)
    es={e for v in vs for e in v.link_edges};fs={f for v in vs for f in v.link_faces};frames.append({'vertices':len(vs),'edges':len(es),'faces':len(fs),'nonmanifold_edges':sum(not e.is_manifold for e in es),'zero_area_faces':sum(f.calc_area()<1e-10 for f in fs)})
   bm.free()
 out[state]={'roof_polygons_by_height':roofs,'frame_connected_components':frames}
(O/'topology_raw.json').write_text(json.dumps(out))
