from pathlib import Path
import bpy,json,numpy as np,hashlib
from collections import Counter
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/penn-roof-detail-001';r=json.loads((R/'references/penn_roof_detail_study.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'penn.glb'));obs={o.name:o for o in bpy.data.objects if o.type=='MESH'};assert set(obs)=={q['name'] for q in r['objects']};checks=[]
for q in r['objects']:
 ob=obs[q['name']];assert ob.get('building_id')==q['building_id'];expected=np.array(q['vertices']);actual=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]);err=max(float(np.min(np.linalg.norm(actual-v,axis=1))) for v in expected);assert err<1e-3
 weld={};ids=[]
 for v in actual:
  key=tuple(np.round(v,5));ids.append(weld.setdefault(key,len(weld)))
 edges=Counter()
 for f in ob.data.polygons:
  seq=[ids[i] for i in f.vertices]
  for a,b in zip(seq,seq[1:]+seq[:1]):edges[tuple(sorted([a,b]))]+=1
 assert set(edges.values())=={2},(q['name'],Counter(edges.values()))
 checks.append({'name':q['name'],'building_id_verified':True,'max_vertex_error_m':err,'welded_edge_incidence':2,'material_slots':len(ob.data.materials)})
p=O/'verification.json';v=json.loads(p.read_text());v['independent_mesh_checks']=checks;v['limitations']='Separate closed shells retain internal shared walls; not a boolean union or validated simulation solid.';v['asset_sha256']={n:hashlib.sha256((O/n).read_bytes()).hexdigest() for n in ['penn.blend','penn.glb']};p.write_text(json.dumps(v,indent=2)+'\n');print('Verified',len(checks),'shells')
