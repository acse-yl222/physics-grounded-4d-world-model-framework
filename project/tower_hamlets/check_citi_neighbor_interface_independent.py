from pathlib import Path
import ast,json,hashlib,collections
import numpy as np
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';out=R/'exports/citi-neighbor-interface-independent-review';out.mkdir(exist_ok=True)
src=(P/'prepare_citi_envelope_photo_study.py').read_text().split('merged={}')[0]
hook=next(ast.literal_eval(n.value) for n in ast.parse((P/'prepare_citi_neighbor_interface.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hook' for t in n.targets))
a={'__file__':str(P/'prepare_citi_envelope_photo_study.py')};exec(src,a)
b={'__file__':a['__file__']};exec(src.replace('main=next(',hook+'\nmain=next(',1),b)
oldhash=collections.Counter(json.dumps(x,sort_keys=True) for x in a['rows']); untouched=b['_untouched'];exact=all(oldhash[json.dumps(x,sort_keys=True)]>0 for x in untouched)
untouched_ids={id(x) for x in untouched};pieces=[x for x in b['rows'] if id(x) not in untouched_ids]
bad=[];zero=[];min_clear=1e9
for j,q in enumerate(pieces):
 v=np.array(q['vertices']);edges=collections.Counter()
 for fi,f in enumerate(q['roof_faces']):
  pts=v[f];area=sum(np.linalg.norm(np.cross(pts[k]-pts[0],pts[k+1]-pts[0]))/2 for k in range(1,len(pts)-1))
  if area<1e-12:zero.append([j,fi,area])
  for u,w in zip(f,f[1:]+f[:1]):edges[tuple(sorted((u,w)))]+=1
 if any(n!=2 for n in edges.values()):bad.append([j,dict(collections.Counter(edges.values()))])
 for seg in b['_interface']['segments']:
  s0,s1=seg['s_m_from_a'];h0,h1=seg['top_scene_z_endpoints']
  for x,y,z in v:
   s=b['_along'](x,y)
   if s0+1e-6<s<s1-1e-6:min_clear=min(min_clear,z-(h0+(h1-h0)*(s-s0)/(s1-s0)))
report=dict(unchanged_rows_exact=exact,unchanged_count=len(untouched),old_count=len(a['rows']),new_count=len(b['rows']),affected_calls=len(b['_changed']),clipped_piece_count=len(pieces),zero_area_faces=zero,nonmanifold_piece_edges=bad,minimum_interior_clearance_m=min_clear,source_hashes={f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in ['prepare_citi_neighbor_interface.py','prepare_citi_envelope_photo_study.py']})
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
# Weld coincident coordinates within each material, as requested; count face incidences.
def welded_edge_counts(rows):
 groups={}
 for q in rows:
  faces=groups.setdefault(q['kind'],[]);v=q['vertices']
  for f in q['roof_faces']:faces.append([tuple(round(c,6) for c in v[i]) for i in f])
 result={}
 for kind,faces in groups.items():
  edges=collections.Counter(tuple(sorted((u,w))) for f in faces for u,w in zip(f,f[1:]+f[:1]) if u!=w)
  result[kind]=dict(collections.Counter(edges.values()))
 return result
report['welded_material_edge_incidence_original']=welded_edge_counts(a['rows'])
report['welded_material_edge_incidence_updated']=welded_edge_counts(b['rows'])
report['limitations']='Per clipped solid manifold passes. Global material welding may merge touching independent closed solids and yield >2 incident faces; no union/cleanup is performed by builder. This report distinguishes these conditions.'
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if 'welded' in k},indent=2))
ss=[b['_along'](v[0],v[1]) for q in pieces for v in q['vertices']]
report['shared_endpoint_range_m']=[min(ss),max(ss)]
report['expected_range_m']=[0,b['_length']]
report['intervals_contiguous']=all(abs(x['s_m_from_a'][1]-y['s_m_from_a'][0])<1e-9 for x,y in zip(b['_interface']['segments'],b['_interface']['segments'][1:]))
report['corner_scope']='Only exact oriented shared edge is intercepted. All other edge ornaments, including adjacent endpoint ornaments, are preserved exactly. No claim of boolean subtraction against full neighbor volume: endpoint neighbor extrusion needs its full 3D volume to test.'
report['crossing_behavior']='Generator splits at both roof=lo and roof=hi; removes above-hi pieces and reduces repeated wall indices at zero-height ends. Current dataset has no resulting zero-area face. Step boundaries keep separate closed caps, causing welded manifold issue.'
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('endpoint range',report['shared_endpoint_range_m'],'length',b['_length'])
import struct
def glb(path):
 data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];return json.loads(data[20:20+n])
oldp=R/'exports/citi-envelope-photo-study-001/citi.glb';newp=R/'exports/citi-neighbor-interface-001/citi.glb';og=glb(oldp);ng=glb(newp)
report['glb_check']={'original_sha256':hashlib.sha256(oldp.read_bytes()).hexdigest(),'updated_sha256':hashlib.sha256(newp.read_bytes()).hexdigest(),'materials_exact_equal':og['materials']==ng['materials'],'mesh_count':len(ng['meshes']),'building_ids':sorted({n.get('extras',{}).get('building_id','') for n in ng['nodes'] if 'mesh'in n}),'position_bounds_gltf':[{k:ng['accessors'][p['attributes']['POSITION']][k] for k in ['min','max']} for m in ng['meshes'] for p in m['primitives']]}
report['glb_check']['bounds_exact_equal']=report['glb_check']['position_bounds_gltf']==[{k:og['accessors'][p['attributes']['POSITION']][k] for k in ['min','max']} for m in og['meshes'] for p in m['primitives']]
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('GLB',report['glb_check']['materials_exact_equal'],report['glb_check']['bounds_exact_equal'],report['glb_check']['building_ids'])
from shapely.geometry import MultiPoint,Polygon
neighbor_path=R/'references/citi_neighbor_study.json';neighbor=json.loads(neighbor_path.read_text());roofpatches=[]
for q in neighbor['objects']:
 v=np.array(q['vertices'])
 for f in q['roof_faces']:
  vv=v[f]
  if min(vv[:,2])<50:continue
  poly=Polygon(vv[:,:2])
  if not poly.is_valid or poly.area<1e-9:continue
  co=np.linalg.lstsq(np.column_stack([np.ones(len(vv)),vv[:,:2]]),vv[:,2],rcond=None)[0]
  roofpatches.append((poly,co))
collisions=[]
for index,q in enumerate(untouched):
 if q['kind']=='backing':continue
 v=np.array(q['vertices']);lo=max(54,float(min(v[:,2])));hi=min(84,float(max(v[:,2])))
 if hi<=lo:continue
 poly=MultiPoint(v[:,:2]).convex_hull
 for patch,co in roofpatches:
  inter=poly.intersection(patch)
  if inter.area<1e-8:continue
  c=inter.representative_point();top=min(hi,float(co@[1,c.x,c.y]))
  if top<=lo:continue
  collisions.append(dict(untouched_index=index,name=q['name'],kind=q['kind'],intersection_area_m2=inter.area,overlap_z_m=[lo,top],approx_volume_m3=inter.area*(top-lo),xy_bounds=list(inter.bounds)))
report['corner_neighbor_volume_test']={'neighbor_source_sha256':hashlib.sha256(neighbor_path.read_bytes()).hexdigest(),'roof_patches':len(roofpatches),'unchanged_ornament_positive_overlaps':collisions,'method':'Projected original prism footprint intersect actual neighbor roof patches; test z54..84. Roof plane evaluated inside overlap; volume estimate only (nearly flat). Ignores <=1e-8m2 numerical contacts.'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('CORNER',json.dumps(collisions))
