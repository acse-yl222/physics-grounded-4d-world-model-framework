from pathlib import Path
s=Path('project/tower_hamlets/prepare_water8_study.py').read_text().split('from shapely.geometry import box')[0].replace('36beb80b-ced9-4f18-a461-04680502f52e','def47cf3-2875-4e34-ae57-aad5a67e6fa1');exec(s)
from shapely.geometry import shape,box
r=json.loads((R/'references/kpmg15_study002.json').read_text());r['objects']=[];main=next(a for a in r['regions'] if a['name']=='main');top=main['candidate_constant_odn_m'];low=75.16050338745117;L,H,B,T=148.8,151.5,31.5,39.5;w=1.1;outer=box(L-w,B-w,H+w,T+w)
for reg in r['regions']:
 q=shape(reg['geometry_uv']);q=q.difference(outer) if reg['name']=='main' else q;r['objects'].append(make(set_precision(q,.000001),[reg['candidate_constant_odn_m'],0,0],'KPMG003_'+reg['name']))
D=(top-low)/w
panels=[('bottom',box(L,B,H,T),[low,0,0]),('west',Polygon([(L-w,B-w),(L,B),(L,T),(L-w,T+w)]),[low+D*L,-D,0]),('east',Polygon([(H,B),(H+w,B-w),(H+w,T+w),(H,T)]),[low-D*H,D,0]),('south',Polygon([(L-w,B-w),(H+w,B-w),(H,B),(L,B)]),[low+D*B,0,-D]),('north',Polygon([(L,T),(H,T),(H+w,T+w),(L-w,T+w)]),[low-D*T,0,D])]
for name,q,c in panels:r['objects'].append(make(q,c,'KPMG003_central_'+name))
r['scope']='KPMG003 descriptive roof withcentral lowplateau andfour slopedtransition planes. Nativeprofiles supportlow75.16ODN vsrim79.536ODN; exact1.1m transition width andrectangular corners estimated, not surveyed. Other roof/sharedFitch uncertainties unchanged.';r['central_transition']={'inner_bounds_uv':[L,B,H,T],'transition_width_m':w,'low_odn_m':low,'rim_odn_m':top,'role':'exploratory alternative to001verticalwalls and002smoothcontrol'};r['limitations']=[x for x in r['limitations'] if 'Central36cell' not in x]+['Lowdomain supported bymultipleprofiles; preciseedgewidthuncertain atnative1m. Slopedrectangle iscomparisonhypothesis, not calibratedarchitecture.'];(R/'references/kpmg15_study003.json').write_text(json.dumps(r,indent=2))
