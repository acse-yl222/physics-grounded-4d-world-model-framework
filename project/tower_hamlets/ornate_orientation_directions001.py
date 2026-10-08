from pathlib import Path
exec(Path(__file__).with_name('ornate_orientation_independent001.py').read_text().split('rows=[]')[0])
# Approximate visible upper-band vertical continuations only; no assumed height
# for the second image point. Lower points define image lines, not 3D landmarks.
vertical_second=np.array([[533,915],[928,991],[375,1038]],float)
lines=[]
for a,b in zip(image[:3],vertical_second):
 d=b-a;nn=np.array([-d[1],d[0]])/np.linalg.norm(d);lines.append((a,nn))
records=[]
for ppy in [720.,960.,1200.]:
 for zcam in [2.,10.]:
  def proj(p,wp):
   uv,dd=project(p,wp,zcam);uv[:,1]+=ppy-960.;return uv,dd
  lowworld=world_correct[:3].copy();lowworld[:,2]=194
  def residual(p):
   uv,dd=proj(p,world_correct);lp,ld=proj(p,lowworld);dirs=np.array([(v-a)@n for v,(a,n) in zip(lp,lines)]);return np.r_[(uv-image).ravel(),dirs*3]
  fit=least_squares(residual,[-350,170,-.5,.4,0,2200],bounds=([-900,0,-1.5,-.1,-.15,300],[-90,700,.1,1.1,.15,6000]),max_nfev=1500);p=fit.x;fore={}
  for height in [30,59.02,64.15,71.81,74.11]:fore[str(height)]=proj(p,np.column_stack([ring,np.full(len(ring),height)]))[0][[11,12]].tolist()
  uv,_=proj(p,world_correct);lp,_=proj(p,lowworld);records.append({'principal_y':ppy,'camera_z':zcam,'parameters':p.tolist(),'ocs_rmse_px':float(np.sqrt(np.mean((uv-image)**2))),'vertical_line_distances_px':[float((v-a)@n) for v,(a,n) in zip(lp,lines)],'front_edge11_by_height':fore})
report={'vertical_lines':{'top':image[:3].tolist(),'second_point':vertical_second.tolist(),'note':'Approximate upperbandcorner lines only, second point heights not used. No lowerbodycorners across setback used.'},'bounded_sensitivity':records,'limitation':'Six bounded fits only, principalpoint/cameraheight varied. Vertical line manual uncertainty severalpixels; model roofheight/datum and photographic perspective correction unresolved. No target facade fitted.'};(O/'direction_constraints.json').write_text(json.dumps(report,indent=2));print(json.dumps(records,indent=2))
