from pathlib import Path
import json,numpy as np
from shapely.geometry import Polygon,box
from shapely import set_precision
s=Path(__file__).with_name('prepare_water8_study.py').read_text();exec(s.split('from shapely.geometry import box')[0].replace('overture-building-36beb80b-ced9-4f18-a461-04680502f52e','overture-building-aace8b76-3b8c-44f1-8ed8-ed8e2c326cfe'))
fit=json.loads((R/'references/aace_regions_fit.json').read_text());th=np.deg2rad(16);co,si=np.cos(th),np.sin(th);uv=lambda x,y:(x*co+y*si,-x*si+y*co);xy=lambda u,v:(u*co-v*si,u*si+v*co);objects=[];area=0
for r in fit['regions']:
 uc,vc=r['center_uv'];c=r['coefficients']
 for k,support in enumerate(r['support_uv']):
  pp=Polygon(support['outer']);area+=pp.area
  for j,(su,sv) in enumerate([(-1,-1),(1,-1),(1,1),(-1,1)]):
   b=box(uc if su>0 else -1000,vc if sv>0 else -1000,1000 if su>0 else uc,1000 if sv>0 else vc);part=set_precision(pp.intersection(b),.000001)
   for z,q in enumerate(getattr(part,'geoms',[part])):
    if q.geom_type!='Polygon' or q.area<1e-5:continue
    coeff=[c[0]-c[1]*su*uc-c[2]*sv*vc,c[1]*su,c[2]*sv];objects.append(make(q,coeff,f'Aace_{r["name"]}_{k}_{j}_{z}'))
r={'building_id':bid,'objects':objects,'baseline_mesh':make(transform(uv,p),[7.35591983795166+datum,0,0],'Aace_baseline'),'scope':'Multiwing exploratory descriptive roof: three higher sloped wings and low connecting remainder. Piecewise planes fitted to all geometric domain samples with robust training, all testresiduals retained. No facade/equipment reconstruction.','fit':fit,'checks':{'source_area_m2':p.area,'partition_area_m2':area,'difference_m2':area-p.area},'replacement_ids':[bid],'limitations':['Geometric wing boundaries and peakcentres are exploratory, not calibrated architectural lines.','Shared regioninterfaces can contain estimated heightsteps; separatelyclosed sectors retaininternalcoincidentwalls.','Southwing18mODN highpoints not modeled as equipment; localized returns unexplained.','Northwestern/centralfits have metre-scale residuals; lowerflat/slopingroofdetails unresolved.','Actual raster capture vintage unknown. Scenez=ODNminus4.28000021,flatbase remainsestimated.']};(R/'references/aace_study.json').write_text(json.dumps(r,indent=2))
