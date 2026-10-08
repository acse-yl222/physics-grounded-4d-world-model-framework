from pathlib import Path
exec(Path(__file__).with_name('hipped_residential_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pair=ps[0].union(ps[1]);edge=np.array(fs[0]['geometry'][0]['outer'][1])-np.array(fs[0]['geometry'][0]['outer'][0]);e=edge/np.linalg.norm(edge);n=np.array([-e[1],e[0]]);uv=lambda xx,yy:(xx*e[0]+yy*e[1],xx*n[0]+yy*n[1]);xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);pq=transform(uv,pair);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];cut=float(np.array(fs[0]['geometry'][0]['outer'][0])@n);main=transform(xy,pq.intersection(box(-1000,cut,1000,1000)));wing=pair.difference(main);courtyard=Polygon(pair.interiors[0]) if pair.interiors else None
allbuild=unary_union([poly(f) for f in g['buildings'] if f.get('kind')!='site']);outer=pair.buffer(3).difference(pair).difference(allbuild)
zones={'wing_inset05':wing.buffer(-.5),'outside_unbuilt_0to3m':outer,'main_inset1':main.buffer(-1)}
if courtyard:zones['courtyard_inset05']=courtyard.buffer(-.5)
zones.update({
'east_outer_wing_strip':wing.intersection(transform(xy,box(-351.2,-1000,1000,1000))).buffer(-.1),
'south_wing_platform_domain':wing.intersection(transform(xy,box(-1000,-1000,-352,450))).buffer(-.1),
'west_long_wing_domain':wing.intersection(transform(xy,box(-1000,450,-357.5,cut))).buffer(-.1),
'outside_south_unbuilt':outer.intersection(transform(xy,box(-1000,-1000,1000,447)))
})
report={}
for name,q in zones.items():
 m=mask(q);dd=z[m]-t[m];report[name]={'selection_polygon_xy_bounds':list(q.bounds),'DSM_ODN':stats(z[m]),'DTM_ODN':stats(t[m]),'DSM_minus_DTM':stats(dd),'near_equal_01m_cells':int((abs(dd)<.1).sum()),'near_equal_001m_cells':int((abs(dd)<.01).sum()),'scene_DTM_z':stats(t[m]-4.28000021)}
fig,axs=plt.subplots(2,3,figsize=(15,10),layout='constrained');m=mask(pair.buffer(3))
for ax,a,title,lo,hi in zip(axs[0],[t,z,z-t],['DTM ODN','DSM ODN','DSM minus DTM'],[2,2,0],[4,10,7]):
 im=ax.scatter(x[m],y[m],c=a[m],s=35,marker='s',vmin=lo,vmax=hi);fig.colorbar(im,ax=ax);ax.plot(*pair.exterior.xy,'r-');
 for hole in pair.interiors:ax.plot(*hole.xy,'r-')
 ax.set(aspect='equal',title=title)
# Longitudinal profiles by narrow rotated-u bands through westwing, courtyard, eastwing.
for ax,uc,title in zip(axs[1],[-359,-355,-350.5],['West wing / exterior','Courtyard / main block','East wing / exterior']):
 mm=m&(abs(u-uc)<.6);order=np.argsort(v[mm]);vv=v[mm][order];ax.plot(vv,t[mm][order],'.-',label='DTM');ax.plot(vv,z[mm][order],'.-',label='DSM');ax.axhline(4.28000021,color='red',ls='--',label='Scene zero ODN');ax.axvline(cut,color='gray',ls=':');ax.set(title=title+' u='+str(uc),xlabel='Rotated north v (m)',ylabel='ODN (m)');ax.legend()
fig.savefig(R/'references/hipped_residential_ground.png',dpi=150);out={'zones':report,'coordinate_axes':{'u':e.tolist(),'v':n.tolist()},'common_scene_zero_ODN':4.28000021,'limitations':['Exterior region excludes mapped buildings but is not positively identified as road or surveyed ground.','DTM interpolates terrain; building-interior DTM is not foundation evidence.','Profiles are native1mcell-center strips within0.6m of three u positions, not surveyed sections.','Actual composite capture date unknown; DSM andDTM matching does not provephysicalopenings.'],'geometry_modified':False,'no_roof_prediction_in_this_plot':True,'zone_selection':'Geometric rotated-coordinate subdomains, selected from inspected spatial map. No elevation threshold selects reported cells. Eastouteru>-351.2; southplatformu<-352 andv<450; westwingu<-357.5 and450<v<cut. These are diagnostic sampling domains, not proposed construction boundaries.'};(R/'references/hipped_residential_ground.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
