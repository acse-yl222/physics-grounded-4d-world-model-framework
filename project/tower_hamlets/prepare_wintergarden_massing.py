from pathlib import Path
import json,hashlib
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union,split,transform
from shapely import constrained_delaunay_triangles
from pyproj import Transformer
from collections import Counter
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());pid='50661885-b2a8-40ca-a0ed-c5e23e253b61';bs=[q for q in g['buildings'] if q.get('parent_id')==pid];fit=json.loads((R/'references/wintergarden_arch_fit.json').read_text());o=np.array(fit['origin']);u=np.array(fit['u']);v=np.array(fit['v']);c=fit['coefficients'];rad=fit['halfwidth_m']+abs(c[2])+c[3];datum=4.28000021;d=np.load(R/'references/wintergarden_samples.npz')
def poly(b):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']])
def arch(x,y):
 a=(x-o[0])*u[0]+(y-o[1])*u[1];vv=(x-o[0])*v[0]+(y-o[1])*v[1];inside=1-((a-c[2])/rad)**2;assert np.all(inside>0),'No clipping or flat tail permitted inside mapped domain';return c[0]-c[1]*(1-np.sqrt(inside))+c[4]*vv
rows=[];metrics=[]
for b in bs:
 p=poly(b);isarch='7998359d' in b['id'];roof=arch if isarch else lambda x,y:np.zeros_like(x)+ (16.35 if 'd8c9283a' in b['id'] else 16.38)
 cells=[p]
 if isarch:
  for a in np.arange(-11.25,11.5,.25):
   line=LineString([o+a*u-50*v,o+a*u+50*v]);cells=[piece for old in cells for piece in split(old,line).geoms]
 verts=[];faces=[];index={};boundary=Counter()
 def vi(x,y,z):
  key=tuple(round(float(t),8) for t in [x,y,z])
  if key not in index:index[key]=len(verts);verts.append(list(key))
  return index[key]
 for cell in cells:
  for tri in constrained_delaunay_triangles(cell).geoms:
   xy=list(tri.exterior.coords)[:-1];ids=[vi(x,y,float(roof(x,y))-datum) for x,y in xy];faces.append(ids);faces.append([vi(x,y,0) for x,y in reversed(xy)])
   for a,bv in zip(ids,ids[1:]+ids[:1]):boundary[tuple(sorted((a,bv)))]+=1
 for (a,bv),n in boundary.items():
  if n!=1:continue
  ax,ay,az=verts[a];bx,by,bz=verts[bv];faces.append([vi(ax,ay,0),vi(bx,by,0),bv,a])
 rows.append(dict(name=('central_curved_roof_estimated' if isarch else ('east_side_roof_estimated' if 'd8c9283a' in b['id'] else 'west_side_roof_estimated')),building_id=b['id'],aggregate_alias_id=pid,kind='estimated_curved_massing' if isarch else'estimated_massing',vertices=verts,roof_faces=faces,wall_faces=[],bottom_faces=[]))
 m=d['valid']&np.array([p.contains(Point(x,y)) for x,y in zip(d['x'].flat,d['y'].flat)]).reshape(d['x'].shape);err=d['z'][m]-roof(d['x'][m],d['y'][m]);metrics.append(dict(id=b['id'],area_m2=p.area,all_cells=int(m.sum()),within1m=int((abs(err)<=1).sum()),rmse_m=float(np.sqrt(np.mean(err**2))),median_abs_m=float(np.median(abs(err))),excluded_cells=0))
whole=unary_union([poly(b) for b in bs]);raw=json.loads((R/'references/buildings.geojson').read_text());parent=next(q for q in raw['features'] if q.get('id')==pid or q['properties'].get('id')==pid);from shapely.geometry import shape
mapped=transform(Transformer.from_crs(4326,g['crs'],always_xy=True).transform,shape(parent['geometry']));interfaces=[]
for b in bs:
 p=poly(b)
 for q in g['buildings']:
  if q['id']==b['id'] or q.get('kind')=='site':continue
  pp=poly(q)
  if p.distance(pp)>1e-6:continue
  sh=p.boundary.intersection(pp.boundary);interfaces.append(dict(owner=b['id'],neighbor=q['id'],shared_length_m=sh.length,shared_geometry=sh.__geo_interface__,overlap_m2=p.intersection(pp).area));assert p.intersection(pp).area<1e-7
r=dict(objects=rows,parent_id=pid,replace_ids=[b['id'] for b in bs],scope='East Wintergarden / The Pelligon three-part partial roof/body study. Exact mapped owner footprints, estimated curved central envelope from native DSM, flat side roofs. No glazing divisions, entrances, supports or interiors reconstructed.',datum_odn_m=datum,architectural_height_m=27,architectural_height_warning='Primary27m is an architectural relative height, not ODN or scene elevation. Curve crown~35.6ODN (~31.3scene); inherited bodybase0scene illustrative, actual public floor unresolved.',arch_fit=fit,zone_diagnostics=metrics,interfaces=interfaces,parent_union_symdiff_m2=whole.symmetric_difference(mapped).area,original_parts=[{k:v for k,v in q.items() if k!='geometry'} for q in bs],original_parent_properties=parent['properties'],source_ids=['overture_buildings_20260923','overture_building_parts_20260923','ea_lidar_dsm_1m','ea_lidar_dtm_1m'],primary_sources=[dict(url='https://cwg.com/press-release/east-wintergarden-brought-to-life-through-360-degree-virtual-reality-140218/',publication='2018-02-14',capture_date=None,facts='Whole venue27m-high arched roof and glass exterior.'),dict(url='https://canarywharf.com/wp-content/uploads/2024/11/FESTIVE-PACK-2024_V9_d.pdf',publication='2024 festive brochure, URLstorage2024-11; exact publication day unknown',capture_date=None,facts='The Pelligon at43BankStreet with27m glass dome. Primary corroboration of current identity and roof type; no images derived.')],limitations=['Composite DSM acquisition vintage unresolved. No per-building capture date inferred from overlapping catalog surveys.','Curved profile uses all2m-inset cells with robustloss; all full-footprint residuals and spatial holdouts retained. Boundary mixed returns and fitted endpoints remain uncertain. No residual rejection.','Strict positive ellipse radicand across mapped domain prevents prior clipped flat tail; continuous elliptical form is an estimated envelope, not exact glazing geometry.','All owner boundaries preserved. NorthernTrust neighboring body57.81999979scene unchanged, eastside roof12.06999979scene.','Material is opaque neutral display proxy for primary-text-reported glass roof; no measured optical parameters, panes or frames.','Local licensed Ollie photo previously inspected supplies no attributable measurable whole venue frontage. No new imagery acquired or copyright photos derived.','Closed per-owner architectural components retain coincident shared walls; no global boolean-union simulation volume claim.'],source_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['geometry.json','references/buildings.geojson','references/building_parts.geojson','references/ea_dsm_1m.tif','references/ea_dtm_1m.tif','references/wintergarden_arch_fit.json']})
(R/'references/wintergarden_massing_study.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(zones=metrics,parent_symdiff=r['parent_union_symdiff_m2'],interfaces=interfaces),indent=2))
