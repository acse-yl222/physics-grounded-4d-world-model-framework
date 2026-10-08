"""Editable appearance hypothesis, explicitly separate from rejected measured fits."""
from pathlib import Path
import json,math,hashlib
from shapely.geometry import Polygon,box
from shapely.ops import unary_union,transform
from shapely import constrained_delaunay_triangles
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());seg=json.loads((R/'references/credit_main_regions.json').read_text());review=json.loads((R/'references/credit_group_review.json').read_text());fs=[f for f in g['buildings'] if f.get('parent_id')==review['parent_id']];theta=math.radians(-10);co,si=math.cos(theta),math.sin(theta);datum=4.28000021
forward=lambda x,y:(x*co+y*si,-x*si+y*co)
back=lambda u,v:(u*co-v*si,u*si+v*co)
rows=[];area_checks=[]
def shell(name,bid,p,height,basis):
 verts=[];roof=[];walls=[];bottom=[];ix={}
 def idx(x,y,z):
  key=tuple(round(float(a),8) for a in [x,y,z])
  if key not in ix:ix[key]=len(verts);verts.append(list(key))
  return ix[key]
 for t in constrained_delaunay_triangles(p).geoms:
  xy=list(t.exterior.coords)[:-1];roof.append([idx(x,y,height) for x,y in xy]);bottom.append([idx(x,y,0) for x,y in reversed(xy)])
 for ring in [p.exterior,*p.interiors]:
  for (x,y),(xx,yy) in zip(ring.coords,list(ring.coords)[1:]):walls.append([idx(x,y,0),idx(xx,yy,0),idx(xx,yy,height),idx(x,y,height)])
 rows.append({'name':name,'building_id':bid,'basis':basis,'vertices':verts,'roof_faces':roof,'wall_faces':walls,'bottom_faces':bottom,'area_m2':p.area,'height_scene_m':height})
for f in fs:
 p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in f['geometry']]);label=next(q['label'] for q in review['parts'] if q['id']==f['id'])
 if f['id']==seg['building_id']:
  uv=transform(forward,p);uc,vc=seg['u_cut'],seg['v_cut'];domains=[box(-1000,-1000,uc,1000),box(uc,-1000,1000,vc),box(uc,vc,1000,1000)];total=0
  for reg,domain in zip(seg['regions'],domains):
   xy=transform(back,uv.intersection(domain));total+=xy.area;shell('Main_'+reg['name'],f['id'],xy,reg['dsm_median_odn_m']-datum,'Estimated constant-height completion of exploratory region; break extrapolated to mapped perimeter. Not accepted measured roof fit.')
  assert abs(total-p.area)<1e-6;area_checks.append({'id':f['id'],'mapped_area_m2':p.area,'partition_area_m2':total})
 elif label in ['1','3','6']:
  med=next(q['insets']['2']['dsm_odn_m']['median'] for q in review['parts'] if q['id']==f['id']);shell('Part_'+label,f['id'],p,med-datum,'Estimated envelope based on dominant interior DSM level; extrapolated boundary, bumps and low returns omitted. Not verified roof surface.')
 else:shell('Unresolved_part_'+label,f['id'],p,f['height_m'],'Unchanged baseline height; inadequate or mixed LiDAR support. Grey material identifies unresolved mass.')
r={'scope':'Credit Suisse group appearance envelope hypothesis. Three broad main roof levels and three secondary dominant levels; two parts remain original baselines. Full geometric completion is estimated: rejected plane diagnostics remain rejected. No facade openings, equipment, entrances, or measured perimeter claims. Separate touching shells have internal coincident walls; unsuitable for volumetric simulation.','datum_odn_m':datum,'datum_status':'Illustrative shared datum, unsurveyed foundations.','objects':rows,'area_checks':area_checks,'source_hashes':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['geometry.json','references/credit_main_regions.json','references/credit_group_review.json']},'geometry_integrated':False}
(R/'references/credit_envelope_study.json').write_text(json.dumps(r,indent=2)+'\n');print('shells',len(rows),'area',sum(q['area_m2'] for q in rows))
