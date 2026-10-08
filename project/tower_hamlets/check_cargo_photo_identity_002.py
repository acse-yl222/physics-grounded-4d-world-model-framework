from pathlib import Path
import runpy,json,numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Polygon,LineString
D=runpy.run_path(str(Path(__file__).with_name('fit_cargo_photo_camera_002.py')));R=D['R'];xyz=D['xyz'];pix=D['pix'];a=D['sol'].x;project=D['project'];fs=D['fs'];f=next(f for f in fs if '2e7e0c13' in f['id']);p=Polygon(f['geometry'][0]['outer']);r=np.array(f['geometry'][0]['outer']);target=np.array([[*((r[13]+r[0])/2),45]]);rng=np.random.default_rng(25);trials=[]
for i in range(40):
 xx=xyz+rng.normal(0,[2,2,2],xyz.shape);pp=pix+rng.normal(0,5,pix.shape);fit=least_squares(lambda a:(project(xx,a)-pp).ravel(),a,max_nfev=700);trials.append(project(target,fit.x)[0])
rep=json.loads((R/'references/cargo_photo_identity_002.json').read_text());rep['selected_wall_center_sensitivity_px']={'sample_count':40,'p05':np.percentile(trials,5,axis=0).tolist(),'p50':np.percentile(trials,50,axis=0).tolist(),'p95':np.percentile(trials,95,axis=0).tolist(),'method':'2mGaussianworldcoordinate/5pximagepick perturbations, notsurveyconfidence.'};near=[];edge=LineString([r[13],r[0]])
for ff in fs:
 if ff['id']==f['id']:continue
 pp=Polygon(ff['geometry'][0]['outer'])
 if p.distance(pp)<1:near.append({'id':ff['id'],'name':ff.get('name'),'height_m':ff.get('height_m'),'overlap_area':p.intersection(pp).area,'shared_length':p.boundary.intersection(pp.boundary).length,'selected_edge_shared_length':edge.intersection(pp.boundary).length})
rep['adjacent_owners']=near;rep['identity_assessment']='Comparativecamera+mappedplan supportsCargo inphotofarright, moderate confidence forNEedge13broadlightglass; noexactcorner/sillmeasurementclaim. Centralcanopy attributionexplicitlywithdrawn.';rep['other_candidates_note']='Mapped nearbyOCSroofparts behindCargo muchtaller; lowadjacentb68e3m cannotexplain79.8mglazedfacade. Photo has foregroundobjects; no bottomfin/entranceassignment.';(R/'references/cargo_photo_identity_002.json').write_text(json.dumps(rep,indent=2));print(rep['selected_wall_center_sensitivity_px']);print(near)
