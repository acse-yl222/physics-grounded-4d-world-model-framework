from pathlib import Path
exec(Path(__file__).with_name('owner1f92_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
from shapely import constrained_delaunay_triangles,set_precision
from shapely.affinity import affine_transform
q=ps[0];a=json.loads((R/'references/owner1f92_fourth.json').read_text());c=a['center'];e=a['east_axis'];n=a['north_axis'];b1,b2=a['boundaries_v_m'];cut=a['middle_west_boundary_u_m'];bn=a['fourth_north_boundary_v_m'];be=a['fourth_east_boundary_u_m'];uv=affine_transform(q,[e[0],e[1],n[0],n[1],-np.dot(e,c),-np.dot(n,c)])
d0=uv.intersection(box(-100,-100,100,b1));d1=uv.intersection(box(cut,b1,100,b2));remaining=uv.difference(unary_union([d0,d1]));d3=remaining.intersection(unary_union([box(-100,bn,100,100),box(be,b2,100,100)]));d2=remaining.difference(d3);parts=[d0,d1,d2,d3];objs=[];areas=[]
for j,pp in enumerate(parts):
 part=set_precision(affine_transform(pp,[e[0],n[0],e[1],n[1],c[0],c[1]]),1e-6);height=a['heights_odn_m'][j]-4.28000021
 for k,poly in enumerate(list(part.geoms) if hasattr(part,'geoms') else [part]):
  vs=[];ix={};roof=[];walls=[];bottom=[]
  def vi(x,y,h):
   key=tuple(round(float(v),7) for v in [x,y,h])
   if key not in ix:ix[key]=len(vs);vs.append(list(key))
   return ix[key]
  for tri in constrained_delaunay_triangles(poly).geoms:
   rr=list(tri.exterior.coords)[:-1];roof.append([vi(x,y,height) for x,y in rr]);bottom.append([vi(x,y,0) for x,y in reversed(rr)])
  for ring in [poly.exterior,*poly.interiors]:
   for (x,y),(xx,yy) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(x,y,0),vi(xx,yy,0),vi(xx,yy,height),vi(x,y,height)])
  objs.append({'name':f'Owner1f92_tier{j}_{k}','building_id':fs[0]['id'],'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom});areas.append(poly.area)
out={'replacement_ids':[fs[0]['id']],'objects':objs,'scope':'Owner1f92 four estimated stepped roof levels from EA DSM; original full footprint and base preserved. Partial exterior massing, facades unverified.','fit':a,'checks':[{'footprint_area_m2':q.area,'partition_area_m2':sum(areas),'difference_m2':sum(areas)-q.area}],'source_properties':fs[0]['source_properties'],'limitations':a['limitations']};(R/'references/owner1f92_study.json').write_text(json.dumps(out,indent=2))
