import runpy,json,numpy as np
from scipy.optimize import least_squares
from pathlib import Path
x=runpy.run_path(str(Path(__file__).with_name('morgan_south_refine001.py')));R=x['R'];O=x['O'];proj=x['proj'];obs=x['obs'];g=json.load(open(R/'geometry.json'))['buildings'];poly=np.array(next(q for q in g if '33773280' in q['id'])['geometry'][0]['outer']);rows=[]
for li in [4,8,9,11,13,15]:
 for ri in [0,1,2,3]:
  for height in [45.003,57.70]:
   xyz=np.array([[-47,-41,235],[63,-149,200],[*poly[li],3],[*poly[ri],3],[*poly[li],height],[*poly[ri],height]])
   sol=least_squares(lambda a:(proj(xyz,a)-obs).ravel(),[-385,-200,3,.546,.188,0,6.983],bounds=([-650,-400,0,-.3,-.1,-.15,6.2],[-280,-100,15,1.4,.7,.15,8]),max_nfev=400)
   residual=np.linalg.norm(proj(xyz,sol.x)-obs,axis=1);rows.append({'left_index':li,'right_index':ri,'roof':height,'rms_scalar_px':float(np.sqrt(np.mean((proj(xyz,sol.x)-obs)**2))),'point_residuals':residual.tolist(),'parameters':sol.x.tolist()})
rows.sort(key=lambda q:q['rms_scalar_px']);(O/'morgan_south-corner-sensitivity.json').write_text(json.dumps({'fits':rows,'limitation':'Searching alternative mapped endpoints demonstrates assignment ambiguity; lowest residual is not independently confirmed correspondence.'},indent=2));print(rows[:3])
from PIL import Image,ImageDraw
im=Image.open(R/'references/pexels-zak-h-36533700.jpeg').resize((1368,1824));dr=ImageDraw.Draw(im);m=json.load(open(R/'references/morgan_photo_study_003.json'));envelopes=[]
for q in m['zones']:
 if not any(k in q['owner'] for k in ['39303788','3ae95773','b317a51d']):continue
 xyz=[[v[0],v[1],q['scene_z_m']] for v in q['support_xy'][0]['outer']];uv=proj(xyz,np.array(rows[0]['parameters']));color='red' if '3930' in q['owner'] else ('cyan' if '3ae9' in q['owner'] else 'lime');dr.line([tuple(v) for v in uv],fill=color,width=3);dr.text(tuple(uv.mean(axis=0)),q['name'],fill=color);envelopes.append({'name':q['name'],'owner':q['owner'],'best_pixels':uv.tolist(),'alternative_pixels':[proj(xyz,np.array(f['parameters'])).tolist() for f in rows[:6]]})
im.save(x['C']/'corner-search-projection.png');(O/'morgan_south-corner-envelopes.json').write_text(json.dumps(envelopes,indent=2))
