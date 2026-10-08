from pathlib import Path
exec(Path(__file__).with_name('norwood_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
from shapely import constrained_delaunay_triangles,set_precision
q=ps[0];fits=json.loads((R/'references/norwood_domains.json').read_text());lookup={r['name']:r for r in fits};domains=[]
for r in fits:
 lo,hi=r['y_bounds'];minx=349.5 if r['name']=='south_connector' else (342.5 if r['name']=='north_connector' else 330);domains.append((r['name'],q.intersection(box(minx,lo,370,hi)),r))
 if minx>330:domains.append((r['name']+'_west_remainder',q.intersection(box(330,lo,minx,hi)),lookup['middle_wing' if r['name']=='south_connector' else 'north_wing']))
objs=[];areas=[]
for name,part,fit in domains:
 part=set_precision(part,1e-6)
 if part.is_empty:continue
 c=np.array(fit['coefficients']);center=fit['center'];height=lambda a,b:float(c@[1,a-center[0],b-center[1]]-4.28000021);vs=[];ix={};roof=[];walls=[];bottom=[]
 def vi(a,b,h):
  key=tuple(round(v,7) for v in [a,b,h])
  if key not in ix:ix[key]=len(vs);vs.append(list(key))
  return ix[key]
 for tri in constrained_delaunay_triangles(part).geoms:
  rr=list(tri.exterior.coords)[:-1];roof.append([vi(a,b,height(a,b)) for a,b in rr]);bottom.append([vi(a,b,0) for a,b in reversed(rr)])
 for ring in [part.exterior,*part.interiors]:
  for (a,b),(aa,bb) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(a,b,0),vi(aa,bb,0),vi(aa,bb,height(aa,bb)),vi(a,b,height(a,b))])
 objs.append({'name':f'Norwood_{name}','building_id':fs[0]['id'],'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom});areas.append(part.area)
out={'replacement_ids':[fs[0]['id']],'objects':objs,'scope':'Norwood House three spatially evidenced sloping wings plus two raised connector roof estimates. Full footprint retained; localstep boundariesestimated.','fit':fits,'checks':[{'footprint_area_m2':q.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-q.area}],'source_properties':fs[0]['source_properties'],'limitations':['1m raster establishes roofslopes but doesnot independently verify connectorbreaklines; narrowtransition strips remainestimated.','No equipment/dormer/facade detail invented.','MicrosoftML oldheight8.5719 isnot measured; OSM6floors provides compatible contextualhint only.','Common ODNoffset4.28000021,flatbase0illustrative,actualflightdateunknown.','Closed planarparts overlap onlyatsharedwallboundaries, internalwalls intentional.']};(R/'references/norwood_study.json').write_text(json.dumps(out,indent=2))
