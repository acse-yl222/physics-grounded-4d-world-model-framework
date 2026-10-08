"""Spatially validated asymmetric roof and measured surface candidate for Blake."""
import runpy,json
import numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Point,Polygon
ns=runpy.run_path(str(__import__('pathlib').Path(__file__).with_name('analyze_blake_lidar.py')))
R=ns['R'];p=ns['p'];x,y,z=ns['x'],ns['y'],np.asarray(ns['z']);valid=ns['valid'];cx,cy=ns['cx'],ns['cy'];datum=ns['datum'];rr,cc=ns['rr'],ns['cc']
# Select exact main-body polygon geometrically: remove only mapped southern tab.
ring=ns['f']['geometry'][0]['outer'];body=Polygon(ring[:6]+ring[8:]);interior=body.buffer(-1.5)
m=valid&np.array([interior.contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);xy=np.column_stack([x[m]-cx,y[m]-cy]);zz=z[m]
def pred(q,xy):
 h,sl,sr,offset,angle=q;b=-np.sin(angle)*xy[:,0]+np.cos(angle)*xy[:,1]-offset;return h-sl*np.maximum(-b,0)-sr*np.maximum(b,0)
a=ns['par'][3];start=[18.4,.3,.55,-3.7,a];bounds=([15,0,0,-6,a-.15],[21,2,2,0,a+.15]);fit=least_squares(lambda q:pred(q,xy)-zz,start,bounds=bounds,loss='soft_l1',f_scale=.2)
# Hold out whole longitudinal strips, so validation is spatial rather than checkerboard.
long=np.cos(a)*xy[:,0]+np.sin(a)*xy[:,1];cuts=np.quantile(long,[0,.25,.5,.75,1]);checks=[]
for k in range(4):
 test=(long>=cuts[k])&(long<=cuts[k+1]);train=~test;ff=least_squares(lambda q:pred(q,xy[train])-zz[train],fit.x,bounds=bounds,loss='soft_l1',f_scale=.2);err=pred(ff.x,xy[test])-zz[test];checks.append({'strip':k,'test_count':int(test.sum()),'rmse_m':float(np.sqrt(np.mean(err**2))),'p95_absolute_error_m':float(np.percentile(abs(err),95))})
# Preserve observed pixel elevations; no interpolation over unsupported cells.
allxy=np.column_stack([x.ravel()-cx,y.ravel()-cy]);predicted=pred(fit.x,allxy).reshape(x.shape);inside=valid&np.array([body.buffer(-.5).contains(Point(a,b)) for a,b in zip(x.flat,y.flat)]).reshape(x.shape);supported=inside&(abs(z-predicted)<=.6)
verts=[];faces=[];lookup={}
for r in range(z.shape[0]-1):
 for c in range(z.shape[1]-1):
  for tri in [[(r,c),(r,c+1),(r+1,c)],[(r+1,c),(r,c+1),(r+1,c+1)]]:
   if not all(supported[t] for t in tri):continue
   pts=[(float(x[t]),float(y[t])) for t in tri]
   if not body.covers(Polygon(pts)):continue
   if (pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])<0:tri.reverse()
   ids=[]
   for t in tri:
    if t not in lookup:lookup[t]=len(verts);verts.append([float(x[t]),float(y[t]),float(z[t]-datum)])
    ids.append(lookup[t])
   faces.append(ids)
obj=R/'references/blake_multiplane_roof.obj';obj.write_text('# EA DSM observed roof patches; open surface; no walls or southern tab\n'+''.join('v %.9f %.9f %.9f\n'%tuple(v) for v in verts)+''.join('f %d %d %d\n'%tuple(i+1 for i in f) for f in faces))
import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');axs[0].scatter(x[inside],y[inside],c=z[inside],s=35,marker='s');axs[0].plot(*p.exterior.xy,c='red');axs[0].plot(*body.exterior.xy,c='black');axs[0].set_aspect('equal');axs[0].set_title('Main body black; exact footprint red')
b=-np.sin(fit.x[4])*xy[:,0]+np.cos(fit.x[4])*xy[:,1];axs[1].scatter(b,zz,s=12);order=np.argsort(b);axs[1].plot(b[order],pred(fit.x,xy)[order],c='red');axs[1].set_title('Asymmetric two-plane fit');axs[1].set(xlabel='Across ridge m',ylabel='DSM ODN m')
axs[2].scatter(x[inside],y[inside],c='lightgray',s=30,marker='s');axs[2].scatter(x[supported],y[supported],c='teal',s=30,marker='s');axs[2].plot(*p.exterior.xy,c='red');axs[2].set_aspect('equal');axs[2].set_title('Retained returns teal; missing stays unknown');fig.savefig(R/'references/blake_multiplane_review.png',dpi=150)
report={'feature_id':ns['f']['id'],'source_ids':ns['report']['source_ids'],'source_hashes':ns['report']['hashes'],'fit_parameters':dict(zip(['ridge_odn_m','north_slope','south_slope','offset_m','axis_angle_rad'],map(float,fit.x))),'ground_scalar_odn_m':datum,'spatial_holdout_four_strips':checks,'main_body_selection':'Mapped outer ring excluding vertices6,7 of southern tab; exact full outline retained as reference only.','candidate':{'file':obj.name,'vertices':len(verts),'triangles':len(faces),'supported_pixel_count':int(supported.sum()),'inside_pixel_count':int(inside.sum()),'max_fit_difference_m':.6,'actual_dsm_vertex_elevations':True,'open_surface':True,'contains_walls':False,'southern_tab_reconstructed':False},'limitations':['No roof edge extrapolation, walls, ridge cap, openings, or closure.','Filtered pixels do not define true architectural holes.','Approximate gridded returns; source dates and ground scalar limitations inherited.'],'visual_reviewed':False}
(R/'references/blake_multiplane_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
