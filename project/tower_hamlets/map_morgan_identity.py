from pathlib import Path
import json,hashlib
from shapely.geometry import Polygon
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());pid='f4658f14-725d-4769-a8fe-a01af160be18';fs=[f for f in g['buildings'] if f.get('parent_id')==pid or f['id']=='overture-building-'+pid]
def poly(f):return unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']])
ps=[poly(f) for f in fs];p=unary_union(ps);overlaps=[]
for i in range(len(fs)):
 for j in range(i+1,len(fs)):
  a=ps[i].intersection(ps[j]).area
  if a>.001:overlaps.append({'a':fs[i]['id'],'b':fs[j]['id'],'area_m2':a})
fig,ax=plt.subplots(figsize=(11,9));labels=[]
for f in g['buildings']:
 if not f['id'].startswith('overture'):continue
 pp=poly(f)
 if pp.centroid.x< -510 or pp.centroid.x>30 or pp.centroid.y< -200 or pp.centroid.y>150:continue
 for q in getattr(pp,'geoms',[pp]):ax.plot(*q.exterior.xy,color='gray',lw=.55)
for i,q in enumerate(ps):ax.fill(*q.exterior.xy,alpha=.17,color='tab:blue');ax.text(q.centroid.x,q.centroid.y,str(i+1),fontsize=8,color='navy')
for bid,name,color in [('overture-building-b0939932-881e-4c5c-8797-8a0a91c38f5c','Newfoundland','tab:red'),('overture-building-33773280-a363-4ff0-b5c0-62dbcac59c87','20 Cabot candidate','tab:orange'),('overture-building-fe8761d9-50b2-4877-9db3-e3d691cd831a','HM Government /10 South Colonnade','tab:green')]:
 f=next(f for f in g['buildings'] if f['id']==bid);q=poly(f);ax.fill(*q.exterior.xy,color=color,alpha=.25);ax.annotate(name,q.centroid.coords[0],xytext=(0,-35),textcoords='offset points',ha='center',fontsize=9,arrowprops={'arrowstyle':'->'});labels.append({'id':bid,'label':name,'centroid_xy':list(q.centroid.coords[0])})
ax.annotate('25 Cabot / Morgan Stanley parent group',p.centroid.coords[0],xytext=(-60,95),textcoords='offset points',ha='center',arrowprops={'arrowstyle':'->'},color='navy');ax.set(aspect='equal',xlabel='ENU east (m)',ylabel='ENU north (m)',title='Identity diagnostic: group extent and neighboring buildings\nOwner map used only for address/location, not geometry tracing');fig.tight_layout();fig.savefig(R/'references/morgan_identity_plan.png',dpi=150)
d={'requested_residual_id':'overture-building-'+pid,'residual_area_m2':ps[0].area,'part_count':len(fs)-1,'group_union_area_m2':p.area,'sum_part_area_m2':sum(q.area for q in ps),'part_overlaps':overlaps,'neighbors':labels,'primary_identity_sources':[{'url':'https://www.morganstanley.com/about-us/global-offices/europe-middle-east-africa/united-kingdom/','supports':'Morgan Stanley address25CabotSquare; not a footprint or photo facade match.'},{'url':'https://canarywharf.com/wp-content/uploads/2025/11/251118_store_guide_NOV_composite_v77_vec.pdf','supports':'Estate address directory MorganStanley25Cabot; HM Government20Cabot/10SouthColonnade.'}],'photo_source_id':'pexels_ollie_11491155','actual_photo_inspected':True,'mapping_assessment':{'25Cabot_group_identity':'high: source mappedname+Morgan official address+estate map location align','single_residual_whole_building':'rejected:0.0533m2 strip, not full building','central_low_curved_facade_exact_assignment':'unresolved:25Cabot southeastern curvedpodium versus eastern20Cabot silhouette; photo has foreground overlap and multiple buildings','confidence_for_whole_facade_reconstruction':'insufficient in this bounded review'},'height_assessment':'26.066m residual scalar not representative; MicrosoftML estimate. Mainpart2m-inset ODN medians83.805/85.466 vs baselines39/45. East curvedpodium mixed34–84ODN. DSM/DTM mixed2017–2020; no replacement heights accepted.','decision':'No architectural asset generated; group owner handling, overlap resolution and photo-to-wing match required before model. No original imagery included in any export.','source_hashes':{'geometry.json':hashlib.sha256((R/'geometry.json').read_bytes()).hexdigest(),'pexels_ollie_11491155':hashlib.sha256((R/'references/pexels-ollie-craig-11491155.jpeg').read_bytes()).hexdigest()}}
(R/'references/morgan_photo_identity.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'overlaps':overlaps,'union_area':p.area},indent=2))
