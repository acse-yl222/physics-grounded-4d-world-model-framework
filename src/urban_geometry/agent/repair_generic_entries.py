"""Re-select 13 occluded estimated doors without changing mapped geometry.
Run with south_kensington/.venv/bin/python. Uses local footprints only.
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json, math
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
ROOT=authoring_path()
TARGETS=['way-'+str(n) for n in [638460209,638465763,638656831,638697359,638697371,809386103,809386104,844902096,850052648,851362839,638451652,638460205,638460208]]
def shape(parts):return unary_union([Polygon(p['outer'],p.get('holes',[])) for p in parts])
def main():
 data=json.loads((ROOT/'geometry.json').read_text());features={f['id']:f for f in data['buildings']}
 obstacles=[];owners=[]
 for f in data['buildings']:
  if f.get('assembly_only') or f.get('base_m',0)>2.5:continue
  obstacles.append(shape(f['geometry']));owners.append(f['id'])
 # Include inherited campus as immutable obstacles, transformed into authoring XY.
 coef=np.array(json.loads((ROOT/'coordinate_contract.json').read_text())['source_xy_to_campus_affine']);inv=np.linalg.inv(np.vstack([coef,[0,0,1]]))
 def to_source(x,y,z=None):return inv[0,0]*np.asarray(x)+inv[0,1]*np.asarray(y)+inv[0,2],inv[1,0]*np.asarray(x)+inv[1,1]*np.asarray(y)+inv[1,2]
 campus=json.loads((ROOT.parent/'references/campus/campus_geometry.json').read_text())
 for f in campus['buildings']:
  obstacles.append(transform(to_source,shape(f['geometry'])));owners.append('campus::'+str(f['id']))
 tree=STRtree(obstacles)
 context=json.loads((ROOT/'context.json').read_text());roads=unary_union([shape(f['geometry']) for f in context['features'] if f['kind'] in ['road','path']])
 audit=[]
 for oid in TARGETS:
  f=features[oid];base=float(f.get('base_m',0));dp=f.setdefault('detail_parameters',{});own=shape(f['geometry']);candidates=[]
  for index,e in enumerate(f.get('facade_edges',[])):
   a,b=np.array(e['a']),np.array(e['b']);L=float(np.linalg.norm(b-a))
   if L<=3 or e.get('neighbor_height_m',0)>base+.1 or e.get('wall_start_m',base)>base+.01:continue
   t=(b-a)/L;n=np.array([t[1],-t[0]]);count=int(L/float(dp.get('window_spacing',3.3)))
   if not count:continue
   for bay in range(count):
    p=a+t*((bay+.5)*L/count)
    if own.contains(Point(p+n*.5)):continue
    # A full-width approach plus facade-projection allowance. Existing module
    # cornices are high; a 0.20 m side allowance covers modest trim/pier relief.
    half=1.05/2+.20;poly=Polygon([p-t*half+n*.025,p+t*half+n*.025,p+t*half+n*1.25,p-t*half+n*1.25])
    if own.intersection(poly).area>1e-6:continue
    blocked=False
    for j in tree.query(poly.buffer(.18)):
     if owners[j]==oid:continue
     if obstacles[j].buffer(.18).intersection(poly).area>1e-6:blocked=True;break
    if blocked:continue
    road_distance=roads.distance(Point(p+n*1.25)) if not roads.is_empty else 0
    candidates.append((road_distance,-L,abs(bay-count//2),index,bay,p.tolist(),n.tolist()))
  candidates.sort()
  if candidates:
   rd,neg_length,_,edge,bay,p,n=candidates[0]
   dp['entrance_override']={'edge_index':edge,'bay_index':bay,'threshold_xy':p,'outward_normal_xy':n,'clear_width_m':1.05,'approach_depth_m':1.25,'neighbor_buffer_m':.18,'status':'estimated exterior door; mapped approach checked, not image located'}
  else:
   dp['entrance_override']=None
   dp['entrance_status']='No unobstructed candidate found; no invented entrance generated'
  audit.append({'building_id':oid,'valid_candidates':len(candidates),'selected':dp.get('entrance_override'),'road_distance_m':candidates[0][0] if candidates else None})
 (ROOT/'geometry.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'docs/generic_entry_repairs.json').write_text(json.dumps({'basis':'Existing footprint obstacles, including inherited campus; no plan edits. Door positions remain artistic estimates.','results':audit},indent=2)+'\n')
 print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
