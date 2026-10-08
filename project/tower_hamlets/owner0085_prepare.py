from pathlib import Path
exec(Path(__file__).with_name('owner0085_review.py').read_text().split('rows=[]')[0])
from shapely import constrained_delaunay_triangles
q=ps[0];review=json.loads((R/'references/owner0085_roof_review.json').read_text());row=review['parts'][0];fit=row['plane_fits']['2'];cf=fit['coefficients'];c=row['center_local_xy_m'];height=lambda x,y:cf[0]+cf[1]*(x-c[0])+cf[2]*(y-c[1])-4.28000021
grid_x=x.copy();grid_y=y.copy();vs=[];ix={};roof=[];walls=[];bottom=[]
def vi(x,y,h):
 key=tuple(round(float(v),7) for v in [x,y,h])
 if key not in ix:ix[key]=len(vs);vs.append(list(key))
 return ix[key]
for tri in constrained_delaunay_triangles(q).geoms:
 rr=list(tri.exterior.coords)[:-1];roof.append([vi(x,y,height(x,y)) for x,y in rr]);bottom.append([vi(x,y,0) for x,y in reversed(rr)])
for ring in [q.exterior,*q.interiors]:
 for (x,y),(xx,yy) in zip(ring.coords,list(ring.coords)[1:]):walls.append([vi(x,y,0),vi(xx,yy,0),vi(xx,yy,height(xx,yy)),vi(x,y,height(x,y))])
x,y=grid_x,grid_y
obj={'name':'Owner0085_shallow_roof','building_id':fs[0]['id'],'kind':'estimated','vertices':vs,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom};full=mask(q);pred=cf[0]+cf[1]*(x-c[0])+cf[2]*(y-c[1]);domains={}
for inset in [0,.5,1,1.5,2,3]:
 m=mask(q.buffer(-inset));domains[str(inset)]={'candidate':metric(z[m]-pred[m]),'original_flat':metric(z[m]-(9+4.28000021))}
out={'replacement_ids':[fs[0]['id']],'objects':[obj],'scope':'Owner0085 shallow planar roof estimate from existing EA DSM. Original footprint and base0 retained; facade unverified.','fit':fit,'full_domain_diagnostic':domains,'source_properties':fs[0]['source_properties'],'limitations':['No equipment, terrace, window or facade pattern inferred.','Roof edges extrapolate2m inset plane; exterior mixed returns remain in full metrics.','Plane slopes/elevation supported by native raster, actual flight date unknown.','Original z0 ground and plain material are illustrative; not surveyed foundation.','Shared1f92 highroof unchanged.']};(R/'references/owner0085_study.json').write_text(json.dumps(out,indent=2));print(json.dumps(domains,indent=2))
