"""Inspect clipped transport centre lines; no road widths or elevations inferred."""
from pathlib import Path
import json,hashlib,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape,box,Polygon,mapping
from shapely.ops import transform
from pyproj import Transformer
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007';refs=root/'references';g=json.loads((root/'geometry.json').read_text());src=refs/'transport_segments.geojson';d=json.loads(src.read_text());tr=Transformer.from_crs(4326,g['crs'],always_xy=True);aoi=transform(tr.transform,box(-.0260,51.5008,-.0116,51.5098));features=[];counts=collections.Counter();fig,ax=plt.subplots(figsize=(12,12),layout='constrained')
for f in g['buildings']:
 if f['id']=='site-support':continue
 for geom in f['geometry']:
  p=Polygon(geom['outer'],geom.get('holes',[]));x,y=p.exterior.xy;ax.fill(x,y,color='#dde2e5',zorder=1)
for f in d['features']:
 p=f['properties'];q=transform(tr.transform,shape(f['geometry'])).intersection(aoi)
 if q.is_empty or p['subtype']=='water':continue
 lines=[q] if q.geom_type=='LineString' else [v for v in q.geoms if v.geom_type=='LineString']
 if not lines:continue
 category='rail' if p['subtype']=='rail' else 'walk_cycle' if p.get('class') in ['footway','steps','cycleway','pedestrian'] else 'road'
 grade=bool(p.get('level_rules') or any(set(r['values'])&{'is_bridge','is_tunnel','is_covered'} for r in p.get('road_flags',[])+p.get('rail_flags',[])))
 for i,line in enumerate(lines):
  x,y=line.xy;ax.plot(x,y,color={'road':'#374b61','walk_cycle':'#bb7b16','rail':'#8b499f'}[category],lw=1.4 if category=='road' else .65,ls='--' if grade else '-',zorder=2)
  features.append({'id':f['id']+'-clip-'+str(i),'source_id':f['id'],'geometry':mapping(line),'properties':p,'category':category,'vertical_review_required':grade})
 counts[category]+=1
ax.set_aspect('equal');ax.set(xlim=(aoi.bounds[0],aoi.bounds[2]),ylim=(aoi.bounds[1],aoi.bounds[3]),xlabel='Local east (m)',ylabel='Local north (m)',title='Canary Wharf — mapped transport centre lines\nBlue: roads; gold: walk/cycle; purple: rail; dashed: level/structure rules')
fig.savefig(refs/'transport_review.png',dpi=160)
report={'source_count':len(d['features']),'included_source_counts':dict(counts),'clipped_line_count':len(features),'crs':g['crs'],'origin_projected_m':g['origin_projected_m'],'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'2D centre lines only; widths and physical elevations unknown. Dashed lines have source level/structure rules, not surveyed heights. Access permissions not implied. Ferry/water lines excluded.','features':features}
(refs/'transport_local_review.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='features'})
