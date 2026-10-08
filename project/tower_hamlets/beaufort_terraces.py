from pathlib import Path
exec(Path(__file__).with_name('beaufort_review.py').read_text().split('rows=[]')[0])
from shapely.geometry import box
pr=json.loads((R/'references/beaufort_profiles.json').read_text());e=np.array(pr['axis_u']);n=np.array(pr['axis_v']);u=x*e[0]+y*e[1];v=x*n[0]+y*n[1];xy=lambda u,v:(u*e[0]+v*n[0],u*e[1]+v*n[1]);q=ps[0];mm=mask(q.buffer(-1));fig,ax=plt.subplots(figsize=(10,10));im=ax.scatter(u[mm],v[mm],c=z[mm],s=65,marker='s',cmap='tab10',vmin=0,vmax=33);fig.colorbar(im,ax=ax,label='DSM ODN');
for aa,bb,zz in zip(u[mm],v[mm],z[mm]):
 if aa>-468:ax.text(aa,bb,f'{zz:.1f}',fontsize=4,ha='center',va='center')
ax.set(aspect='equal',xlim=(-470,-453),title='Beaufort outer terraces: all 1m inset samples');fig.savefig(R/'references/beaufort_terraces.png',dpi=200)
