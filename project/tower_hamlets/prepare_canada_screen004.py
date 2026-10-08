from pathlib import Path
import json,math
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles,set_precision
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/one_canada_detail_gap004';O.mkdir(exist_ok=True);g=json.loads((R/'geometry.json').read_text());ID='overture-part-0c84e402-a7c0-399a-a2af-317cf479fcef';f=next(q for q in g['buildings'] if q['id']==ID);ring=f['geometry'][0]['outer'];p=Polygon(ring);c=(sum(q[0] for q in ring)/4,sum(q[1] for q in ring)/4);a,b=ring[:2];wedge=Polygon([c,(c[0]+3*(a[0]-c[0]),c[1]+3*(a[1]-c[1])),(c[0]+3*(b[0]-c[0]),c[1]+3*(b[1]-c[1]))]);screen=p.buffer(.12,join_style=2).difference(p.buffer(-.10,join_style=2));screen=set_precision(screen,1e-6);west=set_precision(screen.intersection(wedge),1e-6);other=set_precision(screen.difference(west),1e-6);verts=[];faces=[]
def extrusion(poly,lo,hi):
 for q in getattr(poly,'geoms',[poly]):
  index={}
  def vi(x,y,z):
   key=(round(x,8),round(y,8),round(z,8))
   if key not in index:index[key]=len(verts);verts.append(key)
   return index[key]
  for tri in constrained_delaunay_triangles(q).geoms:
   xy=list(tri.exterior.coords)[:-1];faces.append([vi(x,y,hi)for x,y in xy]);faces.append([vi(x,y,lo)for x,y in reversed(xy)])
  for line in [q.exterior,*q.interiors]:
   xy=list(line.coords)
   for (x,y),(xx,yy) in zip(xy,xy[1:]):faces.append([vi(x,y,lo),vi(xx,yy,lo),vi(xx,yy,hi),vi(x,y,hi)])
for i in range(5):extrusion(other,210+i*.32,210+i*.32+.09)
for i in range(6):extrusion(west,210+i*(1.28/5),210+i*(1.28/5)+.09)
# Exact source pyramid geometry retained from original authoring vertices, same base/apex.
off=len(verts);verts.extend([(x,y,210) for x,y in ring]+[(c[0],c[1],235)]);faces.append([off+i for i in reversed(range(4))]);faces.extend([[off+i,off+(i+1)%4,off+4]for i in range(4)])
d={'owner_id':ID,'vertices':verts,'faces':faces,'old_west_band_z':[[210+i*.32,210+i*.32+.09]for i in range(5)],'new_west_band_z':[[210+i*.256,210+i*.256+.09]for i in range(6)],'partition':{'screen_area':screen.area,'west_area':west.area,'other_area':other.area,'overlap_area':west.intersection(other).area,'missing_area':screen.difference(west.union(other)).area,'west_xy':list(west.exterior.coords)},'scope':'Six slats/five slots westface crossview estimate from Altaf; exactwestcountnotmeasured. Otherfacesretain originalfivebandheights. Pyramid unchanged.'};(O/'authoring.json').write_text(json.dumps(d,indent=2));print(d['partition'])
