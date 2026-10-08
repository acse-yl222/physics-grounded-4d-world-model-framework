from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/ownerd42_diagnostic.json').read_text());c=np.array(a['center']);e=np.array(a['east_axis']);n=np.array(a['north_axis']);u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];q=ps[0];full=mask(q);domain=full&(u>-26)&(u<-12)&(v>-18)&(v<-3);h=24.80000114440918
start=[30,.045,0,-23,-15,-17,-5,4];lo=[27,-.3,-.3,-25,-17,-19,-8,1];hi=[34,.3,.3,-21,-13,-14,-3,8]
def model(p):return np.maximum(h,np.minimum.reduce([p[0]+p[1]*u+p[2]*v,h+p[7]*(u-p[3]),h+p[7]*(p[4]-u),h+p[7]*(v-p[5]),h+p[7]*(p[6]-v)]))
pf=least_squares(lambda p:(model(p)-z)[domain],start,bounds=(lo,hi),loss='soft_l1',f_scale=.2).x
res={'parameters':pf.tolist(),'in_sample':metric((model(pf)-z)[domain]),'domain':'−26<u<−12,−18<v<−3; all valid cells including footprint edge','holdout':{}}
for axis,arr in [('u',u),('v',v)]:
 folds=np.floor((arr-arr[domain].min())/2).astype(int)%3;errs=[];rows=[]
 for k in range(3):
  tr=domain&(folds!=k);te=domain&(folds==k);pfit=least_squares(lambda p:(model(p)-z)[tr],pf,bounds=(lo,hi),loss='soft_l1',f_scale=.2).x;ee=(model(pfit)-z)[te];errs.extend(ee);rows.append({'fold':k,'parameters':pfit.tolist(),**metric(ee)})
 res['holdout'][axis]={'pooled':metric(np.array(errs)),'folds':rows}
(R/'references/ownerd42_swfit.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
