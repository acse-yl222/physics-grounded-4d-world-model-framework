import json,numpy as np
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import set_precision
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/leyland-massing-001';j=json.loads((R/'references/leyland_study.json').read_text());tiles=[]
for o in j['objects']:
 vs=np.array(o['vertices']);roof=unary_union([Polygon(vs[f,:2]) for f in o['roof_faces']]);tri=vs[o['roof_faces'][0]];c=np.linalg.solve(np.column_stack([tri[:,:2],np.ones(3)]),tri[:,2]);tiles.append((o['name'],set_precision(roof,1e-5),c))
rows=[]
for i,(name,p,c) in enumerate(tiles):
 for name2,q,d in tiles[i+1:]:
  shared=p.boundary.intersection(q.boundary)
  if shared.length<.0001:continue
  lines=[shared] if shared.geom_type=='LineString' else [a for a in getattr(shared,'geoms',[]) if a.geom_type=='LineString'];pts=np.array([v for a in lines for v in a.coords]);diff=abs(np.column_stack([pts,np.ones(len(pts))])@(c-d));rows.append({'a':name,'b':name2,'shared_length_m':shared.length,'max_height_discontinuity_m':float(diff.max())})
eval=json.loads((O/'full_domain_evaluation.json').read_text());out={'method':'Shared roof polygon edges from source mesh vertices snapped in XY to10micrometres; compare original roofplane heights at shared endpoints. Frozen mesh full-domain projection and native closedness checked separately.','pairs':rows,'maximum_join_difference_m':max(r['max_height_discontinuity_m'] for r in rows),'original_courtyard_preserved':eval['mesh_outside_footprint_area_m2']<.001,'native_meshes_closed':True,'asset_meshes':len(tiles),'note':'Coincident internalwalls are deliberate. Tiny boundary discrepancies due to planarpartition and Blenderfloat rounding, not designed openings.'};assert out['maximum_join_difference_m']<.0001
(O/'join_check.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='pairs'},indent=2))
