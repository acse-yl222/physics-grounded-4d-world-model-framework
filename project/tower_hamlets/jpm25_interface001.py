from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,shape,Point,box
from shapely.ops import transform
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/jpm25-evidence-001';a=json.load(open(O/'jpm25-audit.json'));d=json.load(open(R/'references/jpm25-authoring001.json'));A=np.array(d['axes']);p=Polygon(a['source_geometry']['geometry'][0]['outer']);tower=Polygon(np.array(d['objects'][1]['uv_polygon'])@A);out=[]
for n in a['nearby_raw_owners']:
 if n['id'] in d['owner_id']:continue
 q=shape(n['geometry_local']);line=p.boundary.intersection(q.boundary);out.append({'id':n['id'],'shared_m':line.length,'positive_plan_overlap_m2':p.intersection(q).area,'shared_geometry':line.__geo_interface__,'shared_tower_boundary_m':line.intersection(tower.buffer(1e-7)).length,'podium_top_scene':d['heights_odn'][0]-d['datum_odn'],'note':'No decoration extends beyond original footprint; adjacent owner untouched. Ground/platform clearance unresolved, no external facade claim at shared boundary.'})
s=np.load(O/'jpm25-samples.npz');m=s['inside']&s['valid'];uv=np.c_[s['x'][m],s['y'][m]]@A.T;z=s['z'][m];cent=Polygon(d['objects'][2]['uv_polygon']);cm=np.array([cent.covers(Point(q)) for q in uv]);res=[]
for delta in [-1,0,1]:
 t=Polygon(np.array(p.exterior.coords)@A.T).intersection(box(-126+delta,-288.5+delta,1000,1000)).difference(box(-65.5+delta,-1000,1000,-274.5+delta));tm=np.array([t.covers(Point(q)) for q in uv]);pred=np.where(cm,d['heights_odn'][2],np.where(tm,d['heights_odn'][1],d['heights_odn'][0]));res.append({'breakline_shift_m':delta,'all_cell_rmse':float(np.sqrt(np.mean((pred-z)**2))),'tower_area':t.area})
(O/'jpm25-interface.json').write_text(json.dumps({'neighbors':out,'full_original_footprint_area':p.area,'candidate_base_area':Polygon(np.array(d['objects'][0]['uv_polygon'])@A).area,'symdiff_m2':p.symmetric_difference(Polygon(np.array(d['objects'][0]['uv_polygon'])@A)).area,'breakline_sensitivity':res,'limitation':'Plan overlap test plus contained-prism construction excludes positive-volume crossings into disjoint neighbor footprints; not a simulation union.'},indent=2));print(out);print(res)
