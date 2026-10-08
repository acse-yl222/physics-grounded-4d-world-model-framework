from pathlib import Path
exec(Path(__file__).with_name('abd75_review.py').read_text().split('rows=[]')[0])
q=ps[0];neighbors=sorted([{'id':f['id'],'name':f['name'],'distance_m':poly(f).distance(q),'center_xy':list(poly(f).centroid.coords[0])} for f in g['buildings'] if f['id']!=fs[0]['id'] and f.get('kind')!='site'],key=lambda t:t['distance_m'])[:15];fig,ax=plt.subplots(figsize=(12,10));
for f in g['buildings']:
 pp=poly(f)
 if pp.distance(q)>160:continue
 parts=list(pp.geoms) if hasattr(pp,'geoms') else [pp]
 for ppp in parts:ax.plot(*ppp.exterior.xy,color='.65',lw=.6)
 if f['name'] and f['name']!=f['id'].replace('overture-building-','').replace('overture-part-',''):ax.text(pp.centroid.x,pp.centroid.y,f['name'],fontsize=7,ha='center')
ax.fill(*q.exterior.xy,color='tab:orange',alpha=.5);ax.text(q.centroid.x,q.centroid.y,'abd75 / inferred16–19CanadaSquare',fontsize=10,ha='center');ax.set(aspect='equal',xlim=(-60,370),ylim=(-260,120),xlabel='ENUeast(m)',ylabel='ENUnorth(m)');fig.savefig(R/'references/abd75_identity_context.png',dpi=150);(R/'references/abd75_identity_neighbors.json').write_text(json.dumps(neighbors,indent=2));print(json.dumps(neighbors,indent=2))
