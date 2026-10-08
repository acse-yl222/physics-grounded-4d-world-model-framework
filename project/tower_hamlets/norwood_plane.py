from pathlib import Path
exec(Path(__file__).with_name('norwood_review.py').read_text().split('rows=[]')[0])
q=ps[0];train=mask(q.buffer(-3));fit=lambda m:float(least_squares(lambda c:z[m]-c[0],[20],loss='soft_l1',f_scale=.1).x[0]);h=fit(train);rows=[]
for label,arr in [('east',x),('north',y)]:
 for k in range(3):
  tr=train&(np.floor(arr/3).astype(int)%3!=k);te=train&~tr;hh=fit(tr);rows.append({'axis':label,'fold':k,'ODN':hh,**metric(z[te]-hh)})
metrics={}
for inset in [0,1,2,3,4]:
 mm=mask(q.buffer(-inset));metrics[str(inset)]={'candidate':metric(z[mm]-h),'old':metric(z[mm]-fs[0]['height_m']-4.28000021)}
out={'fit_ODN':h,'scene_height':h-4.28000021,'holdout':rows,'inset_metrics':metrics,'method':'3m geometric inset robust flatplane using allcellvalues, no heightfilter; sixspatialholdouts. Fullfootprint extrapolation evaluated unfiltered.','decision':'Candidate heightstudy only until boundary/lowwing interpretation resolved.'};(R/'references/norwood_plane.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
