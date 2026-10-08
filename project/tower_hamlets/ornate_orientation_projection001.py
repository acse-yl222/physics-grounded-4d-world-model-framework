from pathlib import Path
exec(Path(__file__).with_name('ornate_orientation_independent001.py').read_text().split('rows=[]')[0])
r=json.loads((O/'direction_constraints.json').read_text());fit=next(a for a in r['bounded_sensitivity'] if a['principal_y']==960 and a['camera_z']==2);p=np.array(fit['parameters']);a,b=ring[11],ring[12];t=(b-a)/np.linalg.norm(b-a);inward=np.array([-t[1],t[0]])
fig,ax=plt.subplots(figsize=(8,12));ax.imshow(plt.imread(R/'references/pexels-altaf-shah-19330277.jpeg'),extent=[0,1280,1920,0]);preds=[]
for depth in [0,6,10]:
 for height in [59.02,64.15,71.81,74.11]:
  wp=np.array([[*(a+inward*depth),height],[*(b+inward*depth),height]]);uv,_=project(p,wp);preds.append({'inset':depth,'height_scene':height,'cornice_edge_projection':uv.tolist()});ax.plot(*uv.T,label=f'inset{depth} z{height}',lw=.7,alpha=.7)
for depth in [6,10]:
 wp=np.array([[*(a+t*18+inward*depth),74.11]]);uv,_=project(p,wp);ax.scatter(*uv.T,s=60,marker='x',c='yellow');preds.append({'inset':depth,'DSM_west_strip_peak_scene':74.11,'along18m_peak_projection':uv.tolist()})
# Held-out image observations, not fit correspondences.
obs={'pediment_apex_approx':[884,1442],'front_left_cornice_approx':[412,1610],'front_right_cornice_approx':[1118,1618]}
for k,v in obs.items():ax.scatter(*v,c='lime',marker='+',s=90);ax.text(*v,k,fontsize=7,color='lime')
ax.set(xlim=(0,1280),ylim=(1920,0),title='Independent OCS+vertical camera; target predictions only');ax.legend(fontsize=6,loc='upper left');fig.savefig(O/'source_height_projection.png',dpi=150)
(O/'source_height_projection.json').write_text(json.dumps({'camera':fit,'predictions':preds,'held_out_approx_observations':obs,'limitations':'Frontcornice endpoints have setbacks, do not equal mappededge11 corners necessarily. Peakalong18m/inset6–10 from inspected nativeDSM strip, not fitphotograph. No targetgeometrymodified. Roof/pediment relation unresolved.'},indent=2));print(json.dumps(preds[-2:],indent=2))
