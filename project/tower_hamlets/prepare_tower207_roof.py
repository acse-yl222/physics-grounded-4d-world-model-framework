"""Observed diagnostic roof only; no wall inference or assembly registration."""
import runpy,json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
HERE=Path(__file__).resolve().parent
s=runpy.run_path(str(HERE/'analyze_tower207_lidar.py'))
root=s['ROOT']; x,y,z,p=s['x'],s['y'],s['z'],s['p']; ground=s['rep']['ground_scalar_m_odn']
# 130m ODN separates coherent upper roof plateaux (138–149m) from low strip.
# Neighbour coherence rejects cliffs/dropouts without bridging unobserved cells.
mask=s['m']&(z>130)&(z<151)
verts=[];faces=[];lookup={}
for r in range(z.shape[0]-1):
 for c in range(z.shape[1]-1):
  for ij in [[(r,c),(r,c+1),(r+1,c+1)],[(r,c),(r+1,c+1),(r+1,c)]]:
   if not all(mask[i,j] for i,j in ij):continue
   zz=[float(z[i,j]) for i,j in ij]
   if max(zz)-min(zz)>1.5:continue
   tri=Polygon([(float(x[i,j]),float(y[i,j])) for i,j in ij])
   if not p.covers(tri):continue
   indices=[]
   for i,j in ij:
    if (i,j) not in lookup:
     lookup[i,j]=len(verts);verts.append([float(x[i,j]),float(y[i,j]),float(z[i,j])-ground])
    indices.append(lookup[i,j])
   v=np.array([verts[k] for k in indices]);
   if np.cross(v[1]-v[0],v[2]-v[0])[2]<0:indices.reverse()
   faces.append(indices)
obj=root/'references/tower207_observed_roof_candidate.obj'
with obj.open('w') as h:
 h.write('# Diagnostic observed roof surface; intentional open mesh; no inferred walls\n')
 for v in verts:h.write('v '+' '.join(f'{q:.8f}' for q in v)+'\n')
 for f in faces:h.write('f '+' '.join(str(k+1) for k in f)+'\n')
areas=[Polygon([(verts[k][0],verts[k][1]) for k in f]).area for f in faces]
report={'building_id':s['f']['id'],'role':'partial_diagnostic_observed_roof_not_integrated','source_ids':['ea_lidar_dsm_1m','ea_lidar_dtm_1m'],'source_hashes':s['rep']['source_hashes'],'selection':{'dsm_odn_range_m':[130,151],'maximum_triangle_vertex_height_range_m':1.5,'reason':'Upper roof plateaux form a separate coherent population around 138–149m ODN; 1.5m local threshold rejects cliffs and dropouts. It is a diagnostic filtering parameter, not architectural boundary detection.'},'ground_scalar_m_odn':ground,'vertices':len(verts),'triangles':len(faces),'projected_area_m2':sum(areas),'footprint_area_m2':p.area,'all_triangles_inside_source_footprint':all(p.covers(Polygon([(verts[k][0],verts[k][1]) for k in f])) for f in faces),'open_surface_intentional':True,'limitations':['No exterior wall or podium boundary inferred.','Excludes observed roof outside mapped footprint pending ownership/alignment evidence.','Missing surface is unknown, not a physical roof opening.','Native 1m mixed-date LiDAR; no parapet or plant reconstruction.'],'obj_sha256':hashlib.sha256(obj.read_bytes()).hexdigest()}
(root/'references/tower207_observed_roof_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
