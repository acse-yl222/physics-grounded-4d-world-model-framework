from pathlib import Path
import json
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union,triangulate
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_seam-comparison-001';a=json.load(open(O/'fff_seam-site-topology.json'));a=[q for q in a if q['props'].get('building_id')=='site-support'];(O/'fff_seam-site-topology.json').write_text(json.dumps(a,indent=2));g=next(q for q in a if q['name']=='ground');rows=json.load(open(R/'exports/fff_boundary-evidence-002/fff_boundary-terrain-report.json'))['samples'];xs=[p['x'] for p in rows];ys=[p['y'] for p in rows];patch=box(min(xs),min(ys),max(xs),max(ys));window=patch.buffer(5).envelope;original=unary_union([Polygon([g['mesh_vertices'][i][:2] for i in t]) for t in g['mesh_triangles']]);remainder=original.intersection(window).difference(patch);faces=[];vs=[]
for t in triangulate(remainder):
 if remainder.covers(t.representative_point()):
  idx=len(vs);vs.extend([[x,y,-.10000000149011612] for x,y in list(t.exterior.coords)[:-1]]);faces.append([idx,idx+1,idx+2])
actual=unary_union([Polygon([vs[i][:2] for i in t]) for t in faces]);assert actual.intersection(patch).area<1e-8;assert actual.symmetric_difference(remainder).area<1e-7
seam=[p for p in rows if (p['x'] in [min(xs),max(xs)] or p['y'] in [min(ys),max(ys)]) and original.covers(Point(p['x'],p['y']))];diff=[-.10000000149011612-p['dtm_scene_z'] for p in seam]
out={'patch_bounds':list(patch.bounds),'local_window_bounds':list(window.bounds),'original_ground_overlap_removed_m2':original.intersection(patch).area,'local_remaining_ground_m2':actual.area,'old_new_plan_overlap_m2':actual.intersection(patch).area,'triangles':faces,'vertices':vs,'seam_samples':seam,'old_minus_dtm_at_seam_range_m':[min(diff),max(diff)],'seam_decision':'Open independent display boundary; no physical slope/vertical wall inferred.','water_intersects':False,'global_source_unchanged':True};(O/'fff_seam-authoring.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['triangles','vertices','seam_samples']})
