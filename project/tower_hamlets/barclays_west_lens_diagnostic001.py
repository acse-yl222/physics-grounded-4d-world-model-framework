from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/barclays-west-registration-001';d=json.loads((O/'control-fit.json').read_text());ctrl=np.array(d['world']);obs=np.array(d['photo_px']);a0=np.array(d['parameters']);G=json.loads((R/'geometry.json').read_text())['buildings'];ring=np.array(next(b for b in G if 'fcc7f76d' in b['id'])['geometry'][0]['outer']);target=np.r_[ring[21],156]
def project(p,a,pp):
 cam=np.array([a[0],a[1],6]);yaw,pitch,roll=a[2:5];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);r=np.array([np.sin(yaw),-np.cos(yaw),0]);u=np.cross(r,fw);rr=r*np.cos(roll)+u*np.sin(roll);uu=-r*np.sin(roll)+u*np.cos(roll);q=np.array(p)-cam;return np.c_[pp[0]+np.exp(a[5])*(q@rr)/(q@fw),pp[1]-np.exp(a[5])*(q@uu)/(q@fw)]
lo=[-400,50,-1.8,-.7,-.3,np.log(250)];hi=[50,600,0,1.2,.3,np.log(6000)];rows=[]
for cx in [320,480,640,800,960]:
 for cy in [240,480,720,960,1200,1440,1680]:
  pp=[cx,cy];s=least_squares(lambda a:(project(ctrl,a,pp)-obs).ravel(),a0,bounds=(lo,hi),max_nfev=2000);pr=project([target],s.x,pp)[0];rows.append({'principal_point_px':pp,'parameters':s.x.tolist(),'scalar_rms_px':float(np.sqrt(np.mean(s.fun**2))),'heldout_barclays21_px':pr.tolist(),'heldout_error_px':float(np.linalg.norm(pr-[224,840]))})
# Image-only approximate vertical lines, kept independent of any known lower absolute z.
lines=np.array([[[477,474],[459,656]],[[647,526],[646,605]],[[224,878],[190,1060]]],float)
A=[];B=[]
for l in lines:
 p,q=l;v=q-p;n=np.array([v[1],-v[0]]);n=n/np.linalg.norm(n);A.append(n);B.append(n@p)
vp=np.linalg.lstsq(A,B,rcond=None)[0];dist=np.array(A)@vp-np.array(B)
# This is a qualitative check only: rounded boundaries, perspective and manual line picks are uncertain.
out={'assumptions':'Fixed camera z6m; no radial distortion; principal point profiled; four roof controls nearly coplanar199.5/200m. Target not fitted.','profile':rows,'controls_height_range_m':[float(ctrl[:,2].min()),float(ctrl[:,2].max())],'vertical_lines_px':lines.tolist(),'vertical_lines_labels':['HSBC approximate nearest vertical','HSBC approximate right vertical','Barclays broad-left facade line'],'vertical_vanishing_point_px':vp.tolist(),'line_distance_residuals_px':dist.tolist(),'vertical_warning':'Image-only manually picked lines; not surveyed lower corners. Rounded facade boundaries and short segments cause uncertainty. Target vertical direction informs optics but not roof position.','conclusion':'Profile is sensitivity, not proof of physical camera. A shifted principal point may explain some off-plane error; evaluate all fits and no target-selected winner.'};(O/'lens-diagnostic.json').write_text(json.dumps(out,indent=2));print('VP',vp,dist);print('best control',sorted(rows,key=lambda r:r['scalar_rms_px'])[:2]);print('range',min(r['heldout_error_px'] for r in rows),max(r['heldout_error_px'] for r in rows))
def vanishing(a,pp):
 yaw,pitch,roll=a[2:5];fw=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)]);r=np.array([np.sin(yaw),-np.cos(yaw),0]);u=np.cross(r,fw);rr=r*np.cos(roll)+u*np.sin(roll);uu=-r*np.sin(roll)+u*np.cos(roll);return np.array([pp[0]+np.exp(a[5])*rr[2]/fw[2],pp[1]-np.exp(a[5])*uu[2]/fw[2]])
def residual(a,ls):
 v=vanishing(a[:6],a[6:]);lr=[]
 for p,q in ls:lr.append(p[0]+(q[1]-p[1])*(v[0]-p[0])/(v[1]-p[1])-q[0])
 return np.r_[(project(ctrl,a[:6],a[6:])-obs).ravel(),lr]
fits=[]
for label,ls in [('HSBC two lines only',lines[:2]),('HSBC plus Barclays direction',lines)]:
 for cy in [480,960,1440]:
  a=np.r_[a0,640,cy];s=least_squares(lambda x:residual(x,ls),a,bounds=(lo+[0,-1000],hi+[1280,2500]),max_nfev=3000);pr=project([target],s.x[:6],s.x[6:])[0];fits.append({'label':label,'initial_cy':cy,'parameters':s.x.tolist(),'roof_controls_residuals_px':np.linalg.norm(project(ctrl,s.x[:6],s.x[6:])-obs,axis=1).tolist(),'vertical_line_endpoint_residuals_px':s.fun[8:].tolist(),'principal_point_px':s.x[6:].tolist(),'predicted_vanishing_point_px':vanishing(s.x[:6],s.x[6:]).tolist(),'heldout_barclays21_px':pr.tolist(),'heldout_error_px':float(np.linalg.norm(pr-[224,840]))})
out['vertical_constrained_fits']=fits;(O/'lens-diagnostic.json').write_text(json.dumps(out,indent=2));print('constrained',fits)
