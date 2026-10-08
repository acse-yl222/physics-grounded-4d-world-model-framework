"""Raleigh evidence-supported local roof triangles; no inferred envelope or walls."""
import runpy,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon
D=runpy.run_path(str(Path(__file__).with_name('analyze_raleigh_lidar.py')))
R=D['R'];xy=D['xy'];zz=D['zz'];p=D['p'];cx,cy=D['cx'],D['cy'];par=D['par'];datum=D['datum'];plt=D['plt']
def pred(q,xy):
 a,b,c,d,e,f=q
 return np.minimum(a+b*xy[:,0]+c*xy[:,1],d+e*xy[:,0]+f*xy[:,1])
top,sl,off,ang=par;n=np.array([-np.sin(ang),np.cos(ang)]);init=[top+sl*off,-sl*n[0],-sl*n[1],top-sl*off,sl*n[0],sl*n[1]]
fit=least_squares(lambda q:pred(q,xy)-zz,init,loss='soft_l1',f_scale=.3)
cv=[]
for label,hold in [('west',xy[:,0]<0),('east',xy[:,0]>=0),('south',xy[:,1]<0),('north',xy[:,1]>=0)]:
 ff=least_squares(lambda q:pred(q,xy[~hold])-zz[~hold],fit.x,loss='soft_l1',f_scale=.3)
 err=pred(ff.x,xy[hold])-zz[hold];cv.append(dict(side=label,rmse=float(np.sqrt(np.mean(err**2))),p95=float(np.percentile(abs(err),95))))
# Actual raster samples: retain triangles supported by local samples, never bridge
# roof/ground jumps or extrapolate onto uncertain footprint edges.
x,y,z,m=D['x'],D['y'],np.asarray(D['z']),D['m'];verts=[];faces=[];idx={}
# Roof gate is deliberately conservative, relative to local datum; rejected low
# samples remain unknown and do not denote measured openings.
valid=m&(z-datum>6.5)
for r in range(z.shape[0]-1):
 for c in range(z.shape[1]-1):
  for ids in [[(r,c),(r,c+1),(r+1,c)],[(r,c+1),(r+1,c+1),(r+1,c)]]:
   if not all(valid[a,b] for a,b in ids):continue
   heights=[z[a,b] for a,b in ids]
   if max(heights)-min(heights)>1.2:continue
   poly=Polygon([(x[a,b],y[a,b]) for a,b in ids])
   if not p.covers(poly):continue
   ff=[]
   for a,b in ids:
    if (a,b) not in idx:idx[a,b]=len(verts);verts.append([float(x[a,b]),float(y[a,b]),float(z[a,b]-datum)])
    ff.append(idx[a,b])
   vv=np.array([verts[k] for k in ff]);normal=np.cross(vv[1]-vv[0],vv[2]-vv[0]);faces.append(ff if normal[2]>0 else ff[::-1])
assert faces and all(p.covers(Polygon([verts[i][:2] for i in t])) for t in faces)
obj=R/'references/raleigh_observed_roof.obj'
obj.write_text('# Local ENU metres; open DSM roof patches, no inferred walls\n'+''.join('v %.9f %.9f %.9f\n'%tuple(v) for v in verts)+''.join('f %d %d %d\n'%tuple(i+1 for i in f) for f in faces))
report={'feature_id':D['f']['id'],'planes_odn_relative_centroid':fit.x.tolist(),'spatial_cross_validation':cv,'single_gable_spatial_cv':D['report']['spatial_holdouts'],'interpretation':'Asymmetric two-plane envelope remains a hypothesis; geometry uses actual retained DSM triangles, not extrapolated planes.','candidate':{'path':obj.name,'vertices':len(verts),'triangles':len(faces),'sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'open_surface':True,'all_triangles_within_exact_footprint':True,'datum_odn_m':datum,'minimum_roof_above_local_datum_m':6.5,'max_triangle_height_range_m':1.2},'limitations':['Southern protrusion and low/steep returns omitted as unresolved.','Patch gaps are absent accepted data, not architectural holes.','1m DSM mixed survey dates; no facades, full enclosure, or measured eave extrapolation.'],'source_hashes':D['report']['hashes'],'visual_reviewed':False}
fig,axs=plt.subplots(1,2,figsize=(12,6),layout='constrained');err=pred(fit.x,xy)-zz;im=axs[0].scatter(xy[:,0]+cx,xy[:,1]+cy,c=err,cmap='coolwarm',vmin=-1.5,vmax=1.5,marker='s');fig.colorbar(im,ax=axs[0],label='Two-plane residual m');axs[0].set_title('Asymmetric plane diagnostic');v=np.array(verts);axs[1].tripcolor(v[:,0],v[:,1],np.array(faces),v[:,2],shading='flat');axs[1].set_title('Observed roof patches: no inferred walls')
for ax in axs:ax.plot(*p.exterior.xy,c='black');ax.set_aspect('equal')
fig.savefig(R/'references/raleigh_multiplane.png',dpi=150);(R/'references/raleigh_multiplane.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
