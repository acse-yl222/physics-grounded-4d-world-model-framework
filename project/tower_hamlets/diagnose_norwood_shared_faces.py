import json,struct,hashlib,itertools
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
R=Path('project/tower_hamlets/input/canary_wharf_20261007');out=R/'exports/facade-speckle-diagnostic-001'
p=Path('project/tower_hamlets/runs/canary_wharf_appearance_norwood_001/region.glb');b=p.read_bytes();n,t=struct.unpack_from('<II',b,12);g=json.loads(b[20:20+n]);start=20+n;ln,typ=struct.unpack_from('<II',b,start);data=b[start+8:start+8+ln]
def acc(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];sz={'SCALAR':1,'VEC3':3,'VEC2':2,'VEC4':4}[a['type']];return np.ndarray((a['count'],sz),dtype=dt,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*sz),np.dtype(dt).itemsize)).copy()
tris=[]
for node in g['nodes']:
 if not node.get('name','').startswith('Norwood_') or 'mesh' not in node:continue
 assert 'rotation' not in node and 'scale' not in node and 'matrix' not in node
 for prim in g['meshes'][node['mesh']]['primitives']:
  ps=acc(prim['attributes']['POSITION'])+np.array(node.get('translation',[0,0,0]));idx=acc(prim['indices']).ravel().reshape(-1,3)
  for ids in idx:
   v=ps[ids];normal=np.cross(v[1]-v[0],v[2]-v[0]);normal/=np.linalg.norm(normal);tris.append((node['name'],v,normal))
rows=[]
for (an,a,na),(bn,bb,nb) in itertools.combinations(tris,2):
 if an==bn or abs(np.dot(na,nb))<.999999:continue
 if np.max(abs((bb-a[0])@na))>1e-5:continue
 axis=np.argmax(abs(na));pa=Polygon(np.delete(a,axis,axis=1));pb=Polygon(np.delete(bb,axis,axis=1));area=pa.intersection(pb).area/abs(na[axis])
 if area>1e-6:rows.append({'a':an,'b':bn,'overlap_m2':area,'normal_dot':float(np.dot(na,nb))})
pairs={}
for r in rows:
 k=(r['a'],r['b']);v=pairs.setdefault(k,{'a':k[0],'b':k[1],'area_m2':0,'normal_dot':r['normal_dot']});v['area_m2']+=r['overlap_m2']
result={'glb_sha256':hashlib.sha256(b).hexdigest(),'norwood_triangle_count':len(tris),'coplanar_tolerance_m':1e-5,'overlap_pairs':list(pairs.values()),'same_facing_overlap_triangle_pairs':sum(r['normal_dot']>0 for r in rows),'opposite_facing_overlap_triangle_pairs':sum(r['normal_dot']<0 for r in rows),'note':'Opposite-facing coincident walls are internal interfaces of adjoining closed volumes. No same-facing duplicate surface found at tolerance. This does not rule out sub-tolerance shared-edge raster seams.'}
(out/'shared_faces.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
