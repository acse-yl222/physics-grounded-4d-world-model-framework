from pathlib import Path
exec(Path(__file__).with_name('owner0085_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import LineString
q=ps[0];coords=np.array(q.exterior.coords);segments=[LineString([a,b]) for a,b in zip(coords[:-1],coords[1:])];indices=sorted(range(len(segments)),key=lambda i:segments[i].length,reverse=True)[:3];m=mask(q);xx=x[m];yy=y[m];zz=z[m];tt=t[m];points=[Point(a,b) for a,b in zip(xx,yy)];fig,ax=plt.subplots(1,3,figsize=(16,5),layout='constrained');rows=[]
for aa,i in zip(ax,indices):
 seg=segments[i];dist=np.array([seg.distance(p) for p in points]);along=np.array([seg.project(p) for p in points]);sel=dist<1.5
 aa.scatter(along[sel],zz[sel],c=dist[sel],vmin=0,vmax=1.5,s=30,label='DSM, color=distance inside');aa.scatter(along[sel],tt[sel],marker='x',s=20,label='DTM');aa.set(title=f'Footprint edge {i}, length {seg.length:.2f} m',xlabel='Distance along mapped edge m',ylabel='ODN m');aa.legend(fontsize=7);rows.append({'edge_index':i,'endpoints':list(map(list,seg.coords)),'length_m':seg.length,'cells':[{'along_m':float(a),'distance_to_edge_m':float(d),'dsm_odn_m':float(z),'dtm_odn_m':float(t)} for a,d,z,t in zip(along[sel],dist[sel],zz[sel],tt[sel])]})
fig.savefig(R/'references/owner0085_edge_segments.png',dpi=150);(R/'references/owner0085_edge_segments.json').write_text(json.dumps(rows,indent=2))
