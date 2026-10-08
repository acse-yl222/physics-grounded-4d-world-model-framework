from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0].replace("['d42f49e8']","['f9ed6834']"))
from shapely.geometry import LineString
O=R/'exports/ornate_orientation_independent001';q=ps[0];full=mask(q);ring=np.array(fs[0]['geometry'][0]['outer']);front=LineString(ring[[11,12]]);groups={}
for name,domain in [('whole',q),('inner4',q.buffer(-4)),('inner10',q.buffer(-10))]+[(f'westedge_{lo}_{hi}',q.intersection(front.buffer(hi)).difference(front.buffer(lo))) for lo,hi in [(0,2),(2,4),(4,6),(6,10)]]:
 m=mask(domain);groups[name]={'cells':int(m.sum()),'DSM_ODN':stats(z[m]),'DTM_ODN':stats(t[m]),'DSM_minus_DTM':stats((z-t)[m]),'near_DTM_10cm':int((abs(z[m]-t[m])<.1).sum())}
fig,ax=plt.subplots(1,2,figsize=(13,7),layout='constrained');im=ax[0].scatter(x[full],y[full],c=z[full],s=7,marker='s',vmin=35,vmax=80);fig.colorbar(im,ax=ax[0],label='ODN m');ax[0].plot(*q.exterior.xy,'k');ax[0].plot(ring[[11,12],0],ring[[11,12],1],'r',lw=3);ax[0].set(aspect='equal',title='Exact owner footprint: all7088native cells')
for lo,hi in [(0,2),(2,4),(4,6),(6,10)]:
 m=mask(q.intersection(front.buffer(hi)).difference(front.buffer(lo)));ab=ring[12]-ring[11];along=((x-ring[11,0])*ab[0]+(y-ring[11,1])*ab[1])/np.linalg.norm(ab);ax[1].scatter(along[m],z[m],s=6,label=f'{lo}–{hi}m inward')
ax[1].legend();ax[1].set(title='West face inward strips, no elevation rejection',xlabel='Along face / m',ylabel='DSM ODN m');fig.savefig(O/'height_spatial_audit.png',dpi=150)
neighbors=[]
for f in g['buildings']:
 if f['id']==fs[0]['id'] or f.get('kind')=='site':continue
 p=poly(f)
 if p.distance(q)<12:neighbors.append({'id':f['id'],'distance':p.distance(q),'overlap':p.intersection(q).area,'name':f.get('name'),'height':f.get('height_m')})
r={'owner':fs[0]['id'],'mapped_area_m2':q.area,'groups':groups,'neighbors_within12':neighbors,'source_hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'geometry.json',R/'references/ea_dsm_1m.tif',R/'references/ea_dtm_1m.tif']},'conclusion':'Sampling recomputed inside exact target mappedpolygon. Broad interior elevated surfaces persist at4m/10minset, not adjacenttower-point spillover. Edge mixedreturns and captureepoch mismatch remain. No photoheight fitting. Datum ODN−4.28000021. Actualflightdateunknown.'};(O/'height_spatial_audit.json').write_text(json.dumps(r,indent=2));print(json.dumps(groups,indent=2))
