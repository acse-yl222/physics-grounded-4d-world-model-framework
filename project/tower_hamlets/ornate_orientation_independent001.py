from pathlib import Path
import json,hashlib
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/ornate_orientation_independent001';O.mkdir(exist_ok=True);g=json.loads((R/'geometry.json').read_text())['buildings'];f=next(q for q in g if 'f9ed6834' in q['id']);ring=np.array(f['geometry'][0]['outer']);ocs=next(q for q in g if 'f6f56e18' in q['id']);rr=np.array(ocs['geometry'][0]['outer']);roof=next(q for q in g if '0c84e402' in q['id']);apex=np.array(roof['geometry'][0]['outer']).mean(axis=0)
# Independently read 1280x1920 scaled full Altaf image. These are approximate
# body-roofcorners, NOT the unidentified far-left dome or ornate-front anchors.
world=np.array([[*rr[0],210],[*rr[4],210],[*rr[1],210],[*apex,235]])
image=np.array([[527,775],[919,839],[379,927],[640,677]],float)
# Counter-hypothesis: swap screenleft/right footprintcorner assignments.
world_correct=world.copy();world_correct[[1,2]]=world_correct[[2,1]]
def project(p,pts,zcam=2.):
 x,y,yaw,pitch,roll,foc=p;ca=np.array([x,y,zcam]);fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);rt=np.array([np.sin(yaw),-np.cos(yaw),0]);up=np.cross(rt,fw);r=rt*np.cos(roll)+up*np.sin(roll);uu=-rt*np.sin(roll)+up*np.cos(roll);d=pts-ca;den=d@fw;return np.column_stack([640+foc*(d@r)/den,960-foc*(d@uu)/den]),den
rows=[]
for label,wp in [('NW_visible_north_left_west_right',world_correct),('swapped_corner_control',world)]:
 best=None
 for xx in [-500,-350,-270]:
  for yy in [110,200,320]:
   p0=[xx,yy,-.5,.3,0,1500];lo=[-900,0,-1.5,-.1,-.15,300];hi=[-90,700,.1,1.1,.15,6000]
   fit=least_squares(lambda p:(project(p,wp)[0]-image).ravel(),p0,bounds=(lo,hi),max_nfev=4000)
   if best is None or np.linalg.norm(fit.fun)<np.linalg.norm(best.fun):best=fit
 p=best.x;uv,depth=project(p,wp);corners=np.column_stack([ring,np.full(len(ring),30.)]);proj,dd=project(p,corners);row={'hypothesis':label,'camera_parameters_x_y_yaw_pitch_roll_focal':p.tolist(),'camera_z_m':2,'ocs_reprojection_rmse_px':float(np.sqrt(np.mean(best.fun**2))),'ocs_landmarks_projection':uv.tolist(),'foreground_roof30m_projection':proj.tolist(),'minimum_landmark_depth':float(depth.min()),'forecast_front_edge11':proj[[11,12]].tolist(),'forecast_north_edge6':proj[[6,7]].tolist()};rows.append(row)
 fig,ax=plt.subplots(figsize=(8,12));ax.imshow(plt.imread(R/'references/pexels-altaf-shah-19330277.jpeg'),extent=[0,1280,1920,0]);ax.scatter(image[:,0],image[:,1],c='lime',marker='+',s=70,label='OCS manually read');ax.scatter(uv[:,0],uv[:,1],c='red',s=25,label='OCS model');ax.plot(*np.vstack([proj,proj[0]]).T,'cyan',lw=1);ax.plot(*proj[[11,12]].T,color='yellow',lw=3,label='candidate westedge11 @30m');ax.plot(*proj[[6,7]].T,color='orange',lw=3,label='candidate northedge6 @30m');ax.set(xlim=(0,1280),ylim=(1920,0),title=f'{label}: OCS RMSE {row["ocs_reprojection_rmse_px"]:.1f}px');ax.legend(fontsize=7);fig.savefig(O/(label+'.png'),dpi=150);plt.close(fig)
report={'source_photo_sha256':hashlib.sha256((R/'references/pexels-altaf-shah-19330277.jpeg').read_bytes()).hexdigest(),'landmark_pixels_at_1280x1920':image.tolist(),'world_landmarks_variants':[world_correct.tolist(),world.tolist()],'models':rows,'interpretation':'Independent OCS-only camera diagnostic; foreground corners are predictions and held out. Photographic top/roof dimensions not precisely surveyed. Principalpoint fixed imagecenter, streetcamera2m, no distortionmodel. Landmarkmanual uncertainty and topgeometry errors must be considered. Never use unidentified dome asanchor.'};(O/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(rows,indent=2))
