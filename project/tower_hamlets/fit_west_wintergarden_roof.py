from pathlib import Path
import json,numpy as np
from scipy.optimize import least_squares
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';a=np.load('cache/tower_hamlets/west_wintergarden_roof.npz');u,v,z,m=[a[k] for k in ['u','v','z','mask']];uc,vc=float(np.median(u[m])),float(np.median(v[m]));U=u-uc;V=v-vc;A=np.stack([np.ones(u.shape),U,U*U,V,V*V],axis=-1)
def fit(mask):return least_squares(lambda c:A[mask]@c-z[mask],[23,0,-.01,0,0],loss='soft_l1',f_scale=.12).x
def metric(e):return {'cells':len(e),'rmse_m':float(np.sqrt(np.mean(e*e))),'median_abs_m':float(np.median(abs(e))),'p90_abs_m':float(np.percentile(abs(e),90))}
coef=fit(m);pred=np.einsum('...k,k->...',A,coef);hold=[]
for axis in [u,v]:
 fold=np.floor(axis/3).astype(int)%3;err=[]
 for k in range(3):
  train=m&(fold!=k);test=m&(fold==k);c=fit(train);err.extend((A[test]@c-z[test]).tolist())
 hold.append(metric(np.array(err)))
fig,ax=plt.subplots(1,3,figsize=(15,5),layout='constrained');im=ax[0].scatter(u[m],v[m],c=z[m],s=12,vmin=12,vmax=24);fig.colorbar(im,ax=ax[0]);im=ax[1].scatter(u[m],v[m],c=(z-pred)[m],s=12,vmin=-10,vmax=1,cmap='coolwarm');fig.colorbar(im,ax=ax[1]);ax[2].scatter(u[m],z[m],s=4,alpha=.3);uu=np.linspace(u[m].min(),u[m].max(),100);ax[2].plot(uu,coef[0]+coef[1]*(uu-uc)+coef[2]*(uu-uc)**2,c='red');ax[0].set_title('West Wintergarden nativeDSM ODN');ax[1].set_title('Fullcell residual incl easternlowstrip');ax[2].set_title('Estimated shallowquadratic profile');fig.savefig(R/'references/west_wintergarden_curve_fit.png',dpi=150)
main=m&(u<-27); cmain=fit(main); main_hold=[]
for axis in [u,v]:
 fold=np.floor(axis/3).astype(int)%3;err=[]
 for k in range(3):
  cc=fit(main&(fold!=k));mm=main&(fold==k);err.extend((A[mm]@cc-z[mm]).tolist())
 main_hold.append(metric(np.array(err)))
r={'building_id':'overture-building-5df0e794-2aeb-4f9f-970b-5f9c3bb14fac','basis':'ODN=c0+c1*(u-uc)+c2*(u-uc)^2+c3*(v-vc)+c4*(v-vc)^2; UV rotation -10degrees','center_uv':[uc,vc],'coefficients':coef.tolist(),'datum_offset_odn_m':4.28000021,'full4m_inset_residual':metric((z-pred)[m]),'spatial3m_strip_holdout_all_cells':hold,'eastern_strip_u_gt_minus26':metric((z-pred)[m&(u>-26)]),'geometric_main_u_lt_minus27':{'coefficients':cmain.tolist(),'cells':int(main.sum()),'spatial_holdout_all_test_returns':main_hold,'whole_inset_residual_against_main_fit':metric((np.einsum('...k,k->...',A,cmain)-z)[m]),'selection_limitation':'Geometricu<-27boundchosenafterviewingraster; exploratoryselection, notindependentvalidation.'},'decision':'Shallowcurveddominantsurface supported; loweasternstrip unresolved. NotEastWintergarden archcopy. Candidatewholeoutlinecurveshellwouldextrapolateacrosslowreturns; askcoordinatorreview beforegeometry. No median-onlyheightchange.','primary_text':[{'url':'https://www.entuitive.com/our-leaders/jonathan-hendricks','fact':'Engineers portfolio identifiesWestWintergarden assteel/glass publicsanctuary.'},{'url':'https://dome.mit.edu/entities/picture/cc83e105-0c0e-4d25-8010-444ad2df2913','fact':'Archive identifieshall connecting30BankStreet andformerLehmanheadquarters; construction2004. ImageCCBYNCnotacquired; metadataonly.'}],'limitations':['Actual raster capture vintage for this building is unresolved. Overlapping catalogue survey dates do not establish composite pixel provenance or mixed-survey use. Glazed roof returns may penetrate; current appearance is unverified.','Fulltestresidualsretained; robustfitdownweightingtrainingonly.','Loweasternstripnotprovenhole orseparateterace.','Shallowshape differsfromtallsemicircular arch; noframecadence evidence.']};(R/'references/west_wintergarden_curve_fit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
