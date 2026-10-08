from pathlib import Path
s=Path('project/tower_hamlets/prepare_water8_study.py').read_text().split('from shapely.geometry import box')[0].replace('36beb80b-ced9-4f18-a461-04680502f52e','fcc7f76d-8a32-4c4b-93cf-528a3bdf79e3');exec(s)
from shapely.geometry import shape
r=json.loads((R/'references/barclays_tower_structure.json').read_text());reg=r['regions'][0];q=shape(reg['geometry_uv']);c0,cu,cv=reg['plane_odn'];C=c0-310*cu-35*cv;ob=make(q,[C,cu,cv],'BarclaysTower_north_roof_skin')
for vertex in ob['vertices']:
 if vertex[2]==0:
  u,v=uv(vertex[0],vertex[1]);vertex[2]=C+cu*u+cv*v-datum-.12
r.update({'objects':[ob],'building_id':bid,'replacement_ids':[],'scope':'Roof-only northplateau skin, not wholeowner replacement. Native972cells supports nearflat northroof;0.12m skinthickness artistestimate. Original156m body remains separate baseline, southern roofunresolved.','datum_odn_m':datum,'limitations':r['limitations']+['Empty replacementIDs: this roof-only asset must not replace buildingbody. No regional integration.','Shared ODNminus4.28000021;0.12m thickness unmeasured.']});(R/'references/barclays_tower_study.json').write_text(json.dumps(r,indent=2))
