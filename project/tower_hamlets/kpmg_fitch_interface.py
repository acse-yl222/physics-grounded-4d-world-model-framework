from pathlib import Path
exec(Path('project/tower_hamlets/kpmg_fitch_common.py').read_text())
from scipy.ndimage import label
ang=np.deg2rad(-10);u=x*np.cos(ang)+y*np.sin(ang);v=-x*np.sin(ang)+y*np.cos(ang);m=mask(p);shared=ps[0].boundary.intersection(ps[1].boundary)
pts=np.array(shared.coords);U=pts[:,0]*np.cos(ang)+pts[:,1]*np.sin(ang);V=-pts[:,0]*np.sin(ang)+pts[:,1]*np.cos(ang);print('shared',U,V)
out={'source_ids':[f['id'] for f in fs],'datum':'DSM/DTM ODN; scene ODN-4.28000021, actual raster capture vintage unknown','shared_xy':shared.__geo_interface__,'shared_u':U.tolist(),'shared_v':V.tolist(),'cross_edge_5m_segments':[]}
# Signed distance follows ordered sharedline: positive west/KPMG, negative east/Fitch.
A,B=pts;d=B-A;norm=np.array([d[1],-d[0]])/np.linalg.norm(d);distance=(x-A[0])*norm[0]+(y-A[1])*norm[1];along=((x-A[0])*d[0]+(y-A[1])*d[1])/np.linalg.norm(d)
for start in np.arange(0,shared.length,5):
 row={'along_m':[float(start),float(min(start+5,shared.length))],'strips':[]}
 for lo,hi in [(-8,-4),(-4,-2),(-2,0),(0,2),(2,4),(4,8),(8,14)]:
  k=m&(along>=start)&(along<start+5)&(distance>=lo)&(distance<hi);row['strips'].append({'signed_distance':[lo,hi],'dsm':stats(z[k]),'dtm':stats(t[k]),'equal_dtm_1cm_cells':int((abs(z[k]-t[k])<.01).sum())})
 out['cross_edge_5m_segments'].append(row)
low=m&(z<20);labs,n=label(low,np.ones((3,3)));comps=[]
for j in range(1,n+1):
 k=labs==j
 if k.sum()<10:continue
 comps.append({'cells':int(k.sum()),'DSM':stats(z[k]),'DTM':stats(t[k]),'AGL':stats((z-t)[k]),'equal_DTM1cm':int((abs(z[k]-t[k])<.01).sum()),'both_sides':bool(np.any(distance[k]<0) and np.any(distance[k]>0)),'distance_range':[float(distance[k].min()),float(distance[k].max())],'along_range':[float(along[k].min()),float(along[k].max())]})
out['low_components_under20ODN']=comps
fig,axs=plt.subplots(1,3,figsize=(18,7),layout='constrained')
for ax,values,lim,title in [(axs[0],z,(10,81),'DSM ODN; both owners'),(axs[1],t,(4,13),'DTM ODN; both owners'),(axs[2],z-t,(0,75),'DSM−DTM, not scene z')]:
 im=ax.scatter(u[m],v[m],c=values[m],s=9,marker='s',vmin=lim[0],vmax=lim[1]);fig.colorbar(im,ax=ax);ax.plot(U,V,'r-',lw=2);ax.set_aspect('equal');ax.set_title(title)
fig.savefig(R/'references/kpmg_fitch_interface.png',dpi=150);(R/'references/kpmg_fitch_interface.json').write_text(json.dumps(out,indent=2));print(json.dumps(comps,indent=2))
