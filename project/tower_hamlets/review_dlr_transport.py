from pathlib import Path
import json
import matplotlib.pyplot as plt
from shapely.geometry import Polygon,shape,mapping
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());t=json.loads((R/'references/transport_local_review.json').read_text());fid='overture-part-7749b3ac-a94f-3524-8984-bd87bd73129f';f=next(b for b in g['buildings'] if b['id']==fid);p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);region=p.buffer(25);rows=[];fig,ax=plt.subplots(figsize=(9,9),layout='constrained')
for b in g['buildings']:
 for q in b['geometry']:
  poly=Polygon(q['outer'],q.get('holes',[]))
  if poly.intersects(region):
   x,y=poly.exterior.xy;ax.fill(x,y,color='#dddddd',alpha=.35)
x,y=p.exterior.xy;ax.plot(x,y,color='black',linewidth=2,label='Mapped central canopy')
for f in t['features']:
 if f['category'] not in ['rail','walk_cycle']:continue
 line=shape(f['geometry']);cut=line.intersection(region)
 if cut.is_empty:continue
 props=f['properties'];name=(props.get('names') or {}).get('primary');rows.append({'id':f['id'],'category':f['category'],'name':name,'class':props.get('class'),'geometry':mapping(cut),'source_properties':props,'intersects_canopy':line.intersects(p),'vertical_review_required':f['vertical_review_required']})
 for seg in [cut] if cut.geom_type=='LineString' else getattr(cut,'geoms',[]):
  if seg.geom_type!='LineString':continue
  xx,yy=seg.xy;ax.plot(xx,yy,color='#d34e30' if f['category']=='rail' else '#2994b0',linewidth=1.5,alpha=.8)
ax.set_aspect('equal');ax.set(xlim=(region.bounds[0],region.bounds[2]),ylim=(region.bounds[1],region.bounds[3]),xlabel='Local east (m)',ylabel='Local north (m)',title='DLR station plan: red rail, blue walk/cycle\n2D evidence only; elevations and platform edges unknown');ax.legend();fig.savefig(R/'references/dlr_transport_plan.png',dpi=150)
report={'canopy_id':fid,'features':rows,'scope':'Source lines clipped to25m canopy neighborhood. No elevations, platform widths or rail gauge inferred. Underground/overhead separation unresolved.','rail_intersecting_canopy':[q['id'] for q in rows if q['category']=='rail' and q['intersects_canopy']]};(R/'references/dlr_transport_plan.json').write_text(json.dumps(report,indent=2));print('nearby',len(rows),'rail under canopy',len(report['rail_intersecting_canopy']));print([(q['name'],q['class'],q['vertical_review_required']) for q in rows if q['category']=='rail'])
