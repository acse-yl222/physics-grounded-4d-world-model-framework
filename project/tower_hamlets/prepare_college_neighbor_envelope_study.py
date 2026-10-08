"""Clean low envelope and explicitly estimated northwest raised region."""
from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());r=json.loads((R/'references/college_neighbor_regions.json').read_text());f=next(f for f in g['buildings'] if f['id']==r['building_id']);datum=4.28000021
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
repairs=[]
for region in r['regions']:
 q=region['partition_local_xy'];p=Polygon(q['outer'],q['holes']);before=p.area
 if not p.is_valid:
  from shapely import make_valid
  fixed=make_valid(p);polygons=[a for a in getattr(fixed,'geoms',[fixed]) if a.geom_type in ['Polygon','MultiPolygon']];p=unary_union(polygons);repairs.append({'name':region['name'],'repair':'make_valid; discard zero-area linework','area_before':before,'area_after':p.area});assert abs(before-p.area)<1e-6
 assert p.is_valid
 for i,part in enumerate(getattr(p,'geoms',[p])):
  top=r['appearance_levels_odn_m'][region['name']]-datum
  shell('College_neighbor_'+region['name']+'_'+str(i),part,lambda x,y:0,lambda x,y,h=top:h,'Estimated constant exterior roof level and full partition; imagery unverified. Central low roof not ground courtyard.')
out={'scope':'College neighbor three estimated exterior roof partitions; all roof levels, internal boundaries, facades and foundation datum are hypotheses. Central low roof retained elevated.','datum_odn_m':datum,'baseline_height_m':f['height_m'],'objects':rows,'geometry_integrated':False,'partition_repairs':repairs,'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/college_neighbor_regions.json','references/college_neighbor_review.json']}}
(R/'references/college_neighbor_envelope_study.json').write_text(json.dumps(out,indent=2)+'\n');print('shells',len(rows),'repairs',repairs)
