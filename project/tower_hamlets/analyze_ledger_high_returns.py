"""Connected high-return patches; no equipment identity inferred."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.ndimage import label
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;source=(S/'analyze_ledger_lidar.py').read_text();ns={'__file__':str(S/'analyze_ledger_lidar.py')};exec(compile(source.split('rep=')[0],str(S/'analyze_ledger_lidar.py'),'exec'),ns)
for k in ['ROOT','x','y','z','masks']:globals()[k]=ns[k]
fit=json.loads((ROOT/'references/ledger_plane_fit.json').read_text());cx,cy=fit['plane_center_xy_m'];a,b,c=fit['plane_coefficients_odn_m'];plane=a+b*(x-cx)+c*(y-cy);high=masks['1']&(z-plane>.75);labels,n=label(high);groups=[]
for k in range(1,n+1):
 m=labels==k
 groups.append({'component':k,'cells':int(m.sum()),'xy_bounds_m':[float(x[m].min()),float(y[m].min()),float(x[m].max()),float(y[m].max())],'median_odn_m':float(np.median(z[m])),'max_odn_m':float(z[m].max()),'median_above_plane_m':float(np.median((z-plane)[m]))})
verts=[];faces=[];lookup={};area=0
for i in range(z.shape[0]-1):
 for j in range(z.shape[1]-1):
  for tri in [[(i,j),(i,j+1),(i+1,j+1)],[(i,j),(i+1,j+1),(i+1,j)]]:
   if not all(high[q] for q in tri) or np.ptp([z[q] for q in tri])>1.5:continue
   xy=np.array([[x[q],y[q]] for q in tri]);cross=float(np.linalg.det([xy[1]-xy[0],xy[2]-xy[0]]))
   if cross<0:tri.reverse()
   inds=[]
   for q in tri:
    if q not in lookup:lookup[q]=len(verts);verts.append([float(x[q]),float(y[q]),float(z[q]-4.28000021)])
    inds.append(lookup[q])
   faces.append(inds);area+=abs(cross)/2
obj=ROOT/'references/ledger_high_returns.obj';obj.write_text('# Native high-return observations, not identified roof equipment\n'+''.join('v '+' '.join(f'{a:.8f}' for a in p)+'\n' for p in verts)+''.join('f '+' '.join(str(a+1) for a in f)+'\n' for f in faces))
fig,ax=plt.subplots(figsize=(9,6));m=masks['0'];ax.scatter(x[m],y[m],c='.85',s=12);im=ax.scatter(x[high],y[high],c=(z-plane)[high],s=30,cmap='magma');fig.colorbar(im,ax=ax,label='Above conditional low plane (m)')
for q in groups:
 if q['cells']>=3:
  mask=labels==q['component'];ax.text(float(x[mask].mean()),float(y[mask].mean()),str(q['component']),color='cyan',fontsize=9)
ax.set(title='Ledger: native high-return components, 1m inward support',xlabel='Local east (m)',ylabel='Local north (m)',aspect='equal');fig.tight_layout();fig.savefig(ROOT/'references/ledger_high_returns.png',dpi=160)
r={'selection':'1m inset, native DSM > fitted low plane+0.75m;4-neighbor components','groups':groups,'mesh':{'obj':obj.name,'vertices':len(verts),'triangles':len(faces),'area_m2':area,'triangle_rule':'All vertices selected; DSM height range<=1.5m'},'source_sha256':hashlib.sha256((ROOT/'references/ea_dsm_1m.tif').read_bytes()).hexdigest(),'datum_odn_m':4.28000021,'limitations':['No equipment, parapet or roof-material identity inferred.','No optical corroboration; historical raster returns only.','Unsupported cells and gaps not connected.'],'visual_reviewed':False};(ROOT/'references/ledger_high_returns.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
