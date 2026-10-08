from pathlib import Path
exec(Path('project/tower_hamlets/mcgraw_review_roof.py').read_text().split('rows=[]')[0])
from scipy.ndimage import label
ang=np.deg2rad(-10);u=x*np.cos(ang)+y*np.sin(ang);v=-x*np.sin(ang)+y*np.cos(ang);m=mask(p);central=m&(u>=168)&(u<=194)&(v>=-139)&(v<=-123)
out={'datum':'DSM ODN; scene ODN minus4.28000021; actual capture vintage unresolved','connectivity':{},'one_metre_profiles':{},'bands':[]}
for threshold in [72.25,72.5,73,74]:
 low=m&(z<threshold)&(z>70)
 for conn,structure in [('4',None),('8',np.ones((3,3)))]:
  labs,n=label(low,structure);comps=[]
  for i in np.unique(labs[central&low]):
   if i==0:continue
   k=labs==i;comps.append({'cells':int(k.sum()),'central_cells':int((k&central).sum()),'u_extent':[float(u[k].min()),float(u[k].max())],'v_extent':[float(v[k].min()),float(v[k].max())],'reaches_outer_ledge':bool(np.any(k&((u<148)|(u>216)|(v<-153)|(v>-103))))})
  out['connectivity'][f'{threshold}_{conn}']=comps
for axis,A,other,B,lo,hi in [('u',u,'v',v,168,194),('v',v,'u',u,-139,-123)]:
 out['one_metre_profiles'][axis]=[{'interval':[b,b+1],'dsm':stats(z[central&(A>=b)&(A<b+1)])} for b in range(lo,hi)]
# Geometric centers selected from raster; test independently in successive along-u cells.
for center in [-137.2,-131.1,-124.8]:
 for shift in [-.5,0,.5]:
  k=m&(u>=169)&(u<=193)&(abs(v-(center+shift))<=.5);rows=[]
  for a in range(169,193):
   kk=k&(u>=a)&(u<a+1);rows.append({'u':[a,a+1],'stats':stats(z[kk])})
  out['bands'].append({'center_v':center,'offset':shift,'width_m':1,'all_cells':stats(z[k]),'fraction_below_73':float(np.mean(z[k]<73)),'profiles':rows})
fig,axs=plt.subplots(1,3,figsize=(18,6),layout='constrained');k=m&(u>165)&(u<197)&(v>-142)&(v<-120)
im=axs[0].scatter(u[k],v[k],c=z[k],s=80,marker='s',vmin=71,vmax=80);fig.colorbar(im,ax=axs[0]);axs[0].set_aspect('equal');axs[0].set_title('Native 1m DSM; no upsampling')
for center in [-137.2,-131.1,-124.8]:
 kk=m&(u>=169)&(u<=193)&(abs(v-center)<=.5);ii=np.argsort(u[kk]);axs[1].plot(u[kk][ii],z[kk][ii],'.-',label=f'v={center}, width1m')
axs[1].legend();axs[1].set_title('Along-band returns, all cells');axs[1].set_ylabel('ODN m')
for center in [173,180,188]:
 kk=m&(abs(u-center)<=.5)&(v>=-140)&(v<=-122);ii=np.argsort(v[kk]);axs[2].plot(v[kk][ii],z[kk][ii],'.-',label=f'u={center}, width1m')
axs[2].legend();axs[2].set_title('Across-band profiles');fig.savefig(R/'references/mcgraw_low_bands.png',dpi=150)
out['limitations']=['Native1m grid at rotated roof axes; apparent narrow-band breadth includes subpixel phase and mixed returns.','Geometric centers exploratory, not independently surveyed. All selected cells retained.','Low elevations not interpreted as equipment, holes or ground.']
(R/'references/mcgraw_low_bands.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'connectivity':out['connectivity'],'bands':[{k:v for k,v in a.items() if k!='profiles'} for a in out['bands']]},indent=2))
base=json.loads((R/'references/mcgraw_study.json').read_text());from shapely.geometry import shape
pred=np.full(z.shape,np.nan)
for reg in base['regions']:
 q=shape(reg['geometry_uv']);kk=m&np.array([q.covers(Point(uu,vv)) for uu,vv in zip(u.flat,v.flat)]).reshape(u.shape);c=reg['plane_odn_c0_cu_cv'];pred[kk]=c[0]+c[1]*(u[kk]-180)+c[2]*(v[kk]+130)
out['two_band_surface_sensitivity']=[]
for width in [.5,1,1.5,2]:
 for shift in [-.5,0,.5]:
  k=m&(u>=171)&(u<=192)&((abs(v-(-124.8+shift))<=width/2)|(abs(v-(-131.1+shift))<=width/2));pp=pred.copy();pp[k]=71.95
  out['two_band_surface_sensitivity'].append({'width':width,'offset':shift,'selected_cells':int(k.sum()),'selected_all_errors':metric(z[k]-pp[k]),'whole_owner_all_errors':metric(z[m]-pp[m]),'central_all_errors':metric(z[central]-pp[central])})
out['interpretation']='Two northern/middle low-return strips are spatially repeatable near71.95ODN, but no raster-connected path to exterior ledge. South strip is strongly subpixel-boundary sensitive and excluded from this hypothesis. Narrow stepped two-band surfaces can be compared without asserting functional identity; boundaries and actual transition wall slopes unresolved.'
(R/'references/mcgraw_low_bands.json').write_text(json.dumps(out,indent=2))
print([(a['width'],a['offset'],round(a['central_all_errors']['rmse_m'],3)) for a in out['two_band_surface_sensitivity']])
out['continuous_valley_sensitivity']=[]
domain=m&(u>=171)&(u<=192)&(v>=-135)&(v<=-121)
for half in [.5,1]:
 for ramp in [1,2,3]:
  dist=np.minimum(abs(v+124.8),abs(v+131.1));weight=np.clip(1-(dist-half)/ramp,0,1);weight*=((u>=171)&(u<=192));pp=pred*(1-weight)+71.95*weight
  checks={}
  for axis,A in [('u',u),('v',v)]:
   folds=np.floor(A/3).astype(int)%3;errors=[]
   for fold in range(3):
    te=domain&(folds==fold);tr=domain&~te
    # Fit only low/high levels, fixed repeated profile geometry; evaluate all held cells.
    design=np.stack([1-weight,weight],axis=-1);c=least_squares(lambda c:design[tr]@c-z[tr],[78.7,71.95],loss='soft_l1',f_scale=.25).x;errors.extend(z[te]-design[te]@c)
   checks[axis]=metric(np.array(errors))
  out['continuous_valley_sensitivity'].append({'low_flat_halfwidth_m':half,'ramp_width_each_side_m':ramp,'whole_owner_all_errors':metric(z[m]-pp[m]),'central_all_errors':metric(z[central]-pp[central]),'conditional_spatial_holdout_all_domain_cells':checks})
out['continuous_model_limitations']='Profile-domain edges at u171/192 are exploratory; hard lateral ends are not validated. Repeated troughs do not identify roof function. Spatial holdout conditions on inspected boundary choices.'
(R/'references/mcgraw_low_bands.json').write_text(json.dumps(out,indent=2));print([(a['low_flat_halfwidth_m'],a['ramp_width_each_side_m'],a['central_all_errors']['rmse_m'],a['conditional_spatial_holdout_all_domain_cells']['u']['rmse_m']) for a in out['continuous_valley_sensitivity']])
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,uc in zip(axs,[173,180,188]):
 k=m&(abs(u-uc)<=.5)&(v>=-136)&(v<=-121);ii=np.argsort(v[k]);ax.plot(v[k][ii],z[k][ii],'o-',label='All native cells,1m strip');vv=np.linspace(-136,-121,400);dist=np.minimum(abs(vv+124.8),abs(vv+131.1));ax.plot(vv,np.where(dist<=1,71.95,78.674),label='002 stepped2m');w=np.clip(1-(dist-.5)/2,0,1);ax.plot(vv,78.674*(1-w)+71.95*w,label='Continuous1m bottom+2m ramps');ax.set_title(f'u≈{uc}');ax.set_ylabel('ODN m');ax.legend(fontsize=8)
fig.savefig(R/'references/mcgraw_profile_comparison.png',dpi=150)
