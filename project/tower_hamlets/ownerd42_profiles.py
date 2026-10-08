from pathlib import Path
exec(Path(__file__).with_name('d42_review.py').read_text().split('rows=[]')[0])
a=json.loads((R/'references/ownerd42_diagnostic.json').read_text());c=a['center'];e=a['east_axis'];n=a['north_axis'];u=(x-c[0])*e[0]+(y-c[1])*e[1];v=(x-c[0])*n[0]+(y-c[1])*n[1];full=mask(ps[0]);fig,ax=plt.subplots(1,3,figsize=(17,5),layout='constrained');rows=[]
for lo,hi in [(-6,-4),(-2,0),(2,4),(6,8)]:
 m=full&(v>=lo)&(v<hi)&(u>6)&(u<19);ax[0].scatter(u[m],z[m],s=12,label=f'v {lo}..{hi}');rows.append({'v_band':[lo,hi],'east_notch_points':[[float(a),float(b),float(c)] for a,b,c in zip(u[m],v[m],z[m])]})
for lo,hi in [(-16,-14),(-12,-10),(-8,-6)]:
 m=full&(v>=lo)&(v<hi)&(u>-25)&(u<-12);ax[1].scatter(u[m],z[m],s=12,label=f'v {lo}..{hi}')
for lo,hi in [(-22,-20),(-20,-18),(-18,-16)]:
 m=full&(u>=lo)&(u<hi)&(v>-20)&(v<-3);ax[2].scatter(v[m],z[m],s=12,label=f'u {lo}..{hi}')
for aa,title,xlabel in zip(ax,['Central east notch: all raw strips','SW patch east profiles','SW patch north profiles'],['East-axis m','East-axis m','North-axis m']):aa.legend();aa.set(title=title,xlabel=xlabel,ylabel='DSM ODN m')
fig.savefig(R/'references/ownerd42_profiles.png',dpi=150);(R/'references/ownerd42_profiles.json').write_text(json.dumps(rows,indent=2))
