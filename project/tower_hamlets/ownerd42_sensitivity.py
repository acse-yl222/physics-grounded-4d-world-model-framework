from pathlib import Path
exec(Path(__file__).with_name('ownerd42_transition.py').read_text().split('fit=least_squares')[0])
r=json.loads((R/'references/ownerd42_transition.json').read_text());p=np.array(r['parameters']);notch=full&(u>8)&(u<16)&(v>-8)&(v<7);rows=[]
for slope in [1.,2.,3.,p[15],8.,100.]:
 pp=p.copy();pp[15]=slope;rows.append({'change':'notch_gradient','value':slope,'notch_all':metric((model(pp)-z)[notch]),'central_all':metric((model(pp)-z)[central])})
for index in [10,11,12,14]:
 for change in [-.5,.5]:
  pp=p.copy();pp[index]+=change;rows.append({'change':'parameter_'+str(index),'delta_m':change,'notch_all':metric((model(pp)-z)[notch]),'central_all':metric((model(pp)-z)[central])})
fig,ax=plt.subplots(2,2,figsize=(13,9),layout='constrained')
for aa,(v0,v1) in zip(ax.flat,[(-6,-4),(-2,0),(2,4),(6,8)]):
 mm=full&(v>=v0)&(v<v1)&(u>6)&(u<18);aa.scatter(u[mm],z[mm],c='k',s=17,label='all DSM strip samples')
 U=np.linspace(6,18,350);V=np.full(U.shape,(v0+v1)/2)
 for slope,col in [(2.,'orange'),(p[15],'teal'),(100.,'purple')]:
  pp=p.copy();pp[15]=slope;aa.plot(U,model(pp,U,V),color=col,label=f'notch slope {slope:.2f} m/m')
 aa.set(title=f'v {v0}..{v1} m; model at strip midpoint',xlabel='u / m',ylabel='ODN m');aa.legend(fontsize=8)
O=R/'exports/ownerd42-massing-001';fig.savefig(O/'notch_sensitivity.png',dpi=150)
report={'rows':rows,'notch_valid_cells':int(notch.sum()),'interpretation':'Coherent low eastern domain is supported. Full vertical discontinuity control slope100 is not preferred. Fitted steep ramps are a descriptive surface transition, not recovered wall/shaft geometry: 1m raster mixes edge returns. ±0.5m shifts and slopes test same-data sensitivity, not independent accuracy. Ledge outer limit is unstable in one spatial holdout; no window/parapet/shaft identity assigned.','all_central_points_used':int(central.sum())};(O/'notch_sensitivity.json').write_text(json.dumps(report,indent=2));print(json.dumps(rows,indent=2))
