"""Clean low envelope and explicitly estimated northwest raised region."""
from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/roof_cc2_regions.json').read_text());f=next(f for f in g['buildings'] if f['id']==r['building_id']);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);main=r['regions'][0];c,a,b=main['plane_odn_intercept_slope_u_slope_v'];uc,vc=main['center_uv_m'];co,si=math.cos(r['axis_rotation_radians']),math.sin(r['axis_rotation_radians']);datum=4.28000021
fw=lambda x,y:(x*co-y*si,x*si+y*co)
bk=lambda u,v:(u*co+v*si,-u*si+v*co)
def low(x,y):
 u,v=fw(x,y);return c+a*(u-uc)+b*(v-vc)-datum
rows=[]
def shell(name,p,base,top,basis):
 verts=[];roofs=[];walls=[];bottom=[];lookup={}
 def idx(x,y,z):
  key=tuple(round(float(t),8) for t in [x,y,z])
  if key not in lookup:lookup[key]=len(verts);verts.append(list(key))
  return lookup[key]
 for tri in constrained_delaunay_triangles(p).geoms:
  xy=list(tri.exterior.coords)[:-1];roofs.append([idx(x,y,top(x,y)) for x,y in xy]);bottom.append([idx(x,y,base(x,y)) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  xy=list(ring.coords)
  for (x,y),(xx,yy) in zip(xy,xy[1:]):walls.append([idx(x,y,base(x,y)),idx(xx,yy,base(xx,yy)),idx(xx,yy,top(xx,yy)),idx(x,y,top(x,y))])
 rows.append({'name':name,'building_id':f['id'],'basis':basis,'vertices':verts,'roof_faces':roofs,'wall_faces':walls,'bottom_faces':bottom,'area_m2':p.area})
shell('College_cc2_main',p,lambda x,y:0,low,'Central/south conditional plane extended to whole footprint as estimated envelope. No facade or base verification.')
# Observed northwest high band; straight cuts and level are appearance choices, not fitted boundaries.
raised=transform(bk,transform(fw,p).intersection(box(-1000,r['cut_v_m'],-39.5,1000)))
shell('College_cc2_northwest_hypothesis',raised,low,lambda x,y:27.45-datum,'Artistically completed northwest high zone. u<-39.5 and v>395.7738 are unverified straight boundary choices;27.45ODN descriptive high level, not accepted plane fit.')
out={'scope':'Unnamed mapped college cc2 appearance hypothesis: low main envelope and bounded northwest raised region. Northeast stays low. Roof boundary, upper outline, facades and foundations estimated; north plane fit remains rejected.','datum_odn_m':datum,'baseline_height_m':f['height_m'],'objects':rows,'geometry_integrated':False,'upper_region_parameters':{'u_max_m':-39.5,'v_min_m':r['cut_v_m'],'top_odn_m':27.45,'estimated_area_m2':raised.area},'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/roof_cc2_regions.json','references/roof_cc2_review.json']}}
(R/'references/cc2_envelope_study.json').write_text(json.dumps(out,indent=2)+'\n');print('footprint',p.area,'raised estimate',raised.area)
