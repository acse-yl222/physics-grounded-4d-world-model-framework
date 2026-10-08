from pathlib import Path
import json,math
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';src=json.loads((R/'references/morgan_replacement_interface_proposed.json').read_text());theta=math.radians(-10);co,si=math.cos(theta),math.sin(theta);datum=4.28000021
uv=lambda x,y:(x*co+y*si,-x*si+y*co)
xy=lambda u,v:(u*co-v*si,u*si+v*co)
rows=[];zones=[]
def prism(p,lo,hi,owner,label,estimated):
 verts=[];faces=[];index={}
 def vi(x,y,z):
  k=(round(x,7),round(y,7),round(z,7))
  if k not in index:index[k]=len(verts);verts.append(list(k))
  return index[k]
 for q in getattr(p,'geoms',[p]):
  if q.geom_type!='Polygon':continue
  for tri in constrained_delaunay_triangles(q).geoms:
   a=list(tri.exterior.coords)[:-1];faces.append([vi(x,y,hi) for x,y in a]);faces.append([vi(x,y,lo) for x,y in reversed(a)])
  for ring in [q.exterior,*q.interiors]:
   a=list(ring.coords)
   for (x,y),(xx,yy) in zip(a,a[1:]):faces.append([vi(x,y,lo),vi(xx,yy,lo),vi(xx,yy,hi),vi(x,y,hi)])
 rows.append(dict(name='Morgan_'+label,kind='estimated' if estimated else 'unresolved',building_id=owner,vertices=verts,roof_faces=faces,wall_faces=[],bottom_faces=[]))
def polys(p):return [{'outer':list(q.exterior.coords),'holes':[list(h.coords) for h in q.interiors]} for q in getattr(p,'geoms',[p]) if q.geom_type=='Polygon']
for q in src['domains']:
 owner=q['owner'];p=unary_union([Polygon(a['outer'],a['holes']) for a in q['exclusive_domains']]);pu=transform(uv,p);short=owner.split('-')[2]
 if short=='39303788':
  parts=[('south_terrace',pu.intersection(box(-1000,-1000,1000,-124)),78.1405),('north_terrace',pu.intersection(box(-1000,-124,1000,1000)),83.805)]
 elif short=='31757561':
  core=pu.buffer(-4,join_style=2);parts=[('north_outer',pu.difference(core),83.805),('north_high_body',core,89.5)]
 elif short=='3ae95773':
  parts=[('east_upper_contiguous',pu,59.6635)]
 elif short=='b317a51d':
  parts=[('podium_west_high',pu.intersection(box(-1000,-145,-332,1000)),78.1400),('podium_west_south',pu.intersection(box(-1000,-1000,-332,-145)),59.6635),('podium_north',pu.intersection(box(-332,-121,1000,1000)),59.6635),('podium_curved_low',pu.intersection(box(-332,-1000,1000,-121)),33.9670)]
 else:
  prism(p,0,q['source_height_m'],owner,short+'_baseline',False);continue
 total=0
 for label,domain,odn in parts:
  pxy=transform(xy,domain);total+=pxy.area;prism(pxy,0,odn-datum,owner,label,True);zones.append({'name':label,'owner':owner,'odn_m':odn,'scene_z_m':odn-datum,'area_m2':pxy.area,'support_xy':polys(pxy),'basis':'Coherent descriptive full-domain completion based on DSM spatial patterns; boundaries/levels estimated, not accepted measured plane.'})
 assert abs(total-p.area)<1e-5
r={'objects':rows,'zones':zones,'datum_odn_m':datum,'scope':'25Cabot/Morgan group standalone descriptive massing hypothesis. Corrects materially low baseline main39/45m using spatial DSM levels rather than wholebuildingmedian.393 split south78.1405/north83.805ODN;317 outer83.805 and estimated4m-inset highbody89.5ODN;curvedpodium westhigh78.14/north59.6635/eastlow33.967ODN. This is estimated architectural completion, not accepted roofplanefit: global spatialholdout failures retained in morgan_roof_regions.json. Adjacent3ae95773 corrected to59.6635ODN to make roof continuous withpodium northband, supported668native2m-insetcells median59.6635ODN; westernmixedreturns unresolved. Other7ownership domains unchanged baselines(gray), even where DSM indicates possible discrepancy. Sharedregional datumODN−4.28000021; groundfoundationunsurveyed. No facade windows/doors or photo-side identification claims.','ownership_interface':src,'roof_fit_evidence':'references/morgan_roof_regions.json','limitations':['Spatial steps cleaned to simplegeometric bands; mechanicalreturns/slopes/roofextensions cannot be separately identified.','Mainnorth4m inset is estimated supportshape, not surveyed roofedge.','Separate adjoining shells have internal coincidentwalls, not booleanunion solids.','Photo25vs20Cabotfacade exactmatch unresolved.']}
(R/'references/morgan_massing_study_002.json').write_text(json.dumps(r,indent=2)+'\n');print(len(rows),'objects',len(zones),'estimatedzones')
