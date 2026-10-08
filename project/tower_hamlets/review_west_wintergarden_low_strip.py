from pathlib import Path
import json,numpy as np
from scipy.ndimage import label
from shapely.geometry import Polygon
from shapely import contains_xy
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';a=np.load('cache/tower_hamlets/west_wintergarden_roof.npz');x,y,u,v,z,t,valid,m=[a[k] for k in ['x','y','u','v','z','t','valid','mask']];g=json.loads((R/'geometry.json').read_text());f=next(q for q in g['buildings'] if '5df0e794' in q['id']);p=Polygon(f['geometry'][0]['outer']);full=valid&contains_xy(p,x,y);low=m&(u>-26);fit=json.loads((R/'references/west_wintergarden_curve_fit.json').read_text());c=fit['geometric_main_u_lt_minus27']['coefficients'];uc,vc=fit['center_uv'];U=u-uc;V=v-vc;pred=c[0]+c[1]*U+c[2]*U*U+c[3]*V+c[4]*V*V
def stats(b):return {'cells':len(b),'p0_p10_p50_p90_p100':np.percentile(b,[0,10,50,90,100]).tolist()} if len(b) else {'cells':0}
regions={}
for name,q in [('eastern_104cells',low),('full_east_u_gt_minus26',full&(u>-26)),('main_4m_inset',m&(u<-27))]:regions[name]={'dsm_odn':stats(z[q]),'dtm_odn':stats(t[q]),'dsm_minus_dtm':stats((z-t)[q]),'curve_minus_dsm':stats((pred-z)[q]),'exact_dsm_dtm_within1cm_count':int(np.sum(q&(abs(z-t)<.01))),'near_ground_within0_5m_count':int(np.sum(q&(abs(z-t)<.5)))}
components=[]
for threshold in [15,16,18]:
 ll,n=label(full&(z<threshold));cc=[]
 for k in range(1,n+1):
  q=ll==k
  if q.sum()<3:continue
  cc.append({'cells':int(q.sum()),'uv_bounds':[float(u[q].min()),float(v[q].min()),float(u[q].max()),float(v[q].max())],'dsm_median_odn':float(np.median(z[q])),'dtm_median_odn':float(np.median(t[q]))})
 components.append({'threshold_odn_m':threshold,'components':cc})
neighbors=[]
for b in g['buildings']:
 if b['id'] in [f['id'],'site-support']:continue
 for part in b['geometry']:
  q=Polygon(part['outer'],part.get('holes',[]))
  if p.distance(q)<5:neighbors.append({'id':b['id'],'name':b.get('name'),'distance_m':p.distance(q),'overlap_m2':p.intersection(q).area,'shared_boundary_m':p.boundary.intersection(q.boundary).length})
fig,ax=plt.subplots(1,3,figsize=(16,5),layout='constrained')
for aa,data,title,lim in [(ax[0],z,'DSM ODN',(10,25)),(ax[1],t,'DTM ODN',(4,10)),(ax[2],z-t,'DSM minus DTM',(0,20))]:
 im=aa.scatter(u[full],v[full],c=data[full],s=15,vmin=lim[0],vmax=lim[1]);aa.axvline(-26,c='red',lw=1);aa.set(aspect='equal',title=title,xlabel='rotated u(m)',ylabel='rotated v(m)');fig.colorbar(im,ax=aa)
fig.savefig(R/'references/west_wintergarden_low_strip_review.png',dpi=150)
r={'building_id':f['id'],'regions':regions,'connected_components_native4connected':components,'neighbors':neighbors,'source_footprint_has_holes':False,'evidence_assessment':['Easternlowcells are spatiallycoherent withinmappedoutline, notmerelyoutsiderastercoverage.','DSM/DTMcomparison evaluates whetherreturns areterrainlike; elevatedreturns alonecannotdistinguishinnerfloor/glazedtransmission fromlowexternalroof.','Existingpermittedmainestatephotos donotprovideisolatedclearWestWintergardenroofview. No newimage acquired, noblockedrequestretried.','Maincurvature fit strongon618cells but spatialselectionexcludeseasternband; extrapolation is onlysmoothshapehypothesis, notobservationalproof.'],'decision':'UNRESOLVED: cannot distinguish glazedrooftransmission/interiorreturn versusreal loweredroofzone orsurveyartifact. Keepentiremappedroofextrapolation exploratory; do notintegrateasverifiedcurvedroof and do notcutroofhole/lowerterracefrombandalone.','geometry_modified':False,'existing_roof_only_study':'exports/west-wintergarden-roof-study-001','datum':'DSM/DTM ODN; sceneoffset4.28000021; localDTMnotreusedasscenebase','epoch':'Actual raster capture vintage for this building is unresolved. Overlapping catalogue survey dates do not establish composite pixel provenance or mixed-survey use. Glazed roof returns may penetrate; current appearance is unverified. Mapped OSM update is 2022; supplied snapshot is 2026.'};(R/'references/west_wintergarden_low_strip_review.json').write_text(json.dumps(r,indent=2));print(json.dumps(regions,indent=2));print(neighbors)
