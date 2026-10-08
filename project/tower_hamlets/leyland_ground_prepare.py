from pathlib import Path
exec(Path(__file__).with_name('leyland_review.py').read_text().split('rows=[]')[0])
# Native BNG pixel-centre surface; no ENU nearest-neighbour resampling.
sel=mask(ps[0].buffer(3));rows=[];idx={};verts=[]
for rr,cc in zip(*np.where(sel)):
 idx[(int(rr),int(cc))]=len(verts);verts.append([float(x[rr,cc]),float(y[rr,cc]),float(t[rr,cc]-4.28000021)])
faces=[]
for (rr,cc),i in idx.items():
 if all(k in idx for k in [(rr+1,cc),(rr+1,cc+1),(rr,cc+1)]):
  b,c,d=[idx[k] for k in [(rr+1,cc),(rr+1,cc+1),(rr,cc+1)]];faces.extend([[i,b,c],[i,c,d]])
# Also independent perimeter samples for current site coverage audit.
for a,b in zip(list(ps[0].exterior.coords),list(ps[0].exterior.coords)[1:]):
 length=np.linalg.norm(np.array(b)-a)
 for v in np.linspace(a,b,max(2,int(np.ceil(length/.5))),endpoint=False):rows.append({'x':float(v[0]),'y':float(v[1])})
with rasterio.open(R/'references/leyland_ea_dtm_1m_001.tif') as ds:
 for row,val in zip(rows,ds.sample([fw.transform(s['x'],s['y']) for s in rows])):row['dtm_scene_z']=float(val[0]-4.28000021)
mm=mask(ps[0]);ring=mask(ps[0].buffer(3))&~mm
out={'owner_id':fs[0]['id'],'terrain_vertices':verts,'terrain_faces':faces,'perimeter_samples':rows,'inside_footprint_dtm_scene_stats':stats((t-4.28000021)[mm]),'outside_3m_ring_dtm_scene_stats':stats((t-4.28000021)[ring]),'source_dtm_sha256':hashlib.sha256((R/'references/leyland_ea_dtm_1m_001.tif').read_bytes()).hexdigest(),'source_id':'leyland_dtm_001','datum':'ODN minus4.28000021m','capture_epoch':None,'terrain_note':'Native BNG pixel-centre triangles; surface truncated to3m ownerbuffer. Interpolation is estimated; no invented ramp/site blending.'}
(R/'references/leyland_ground_input.json').write_text(json.dumps(out,indent=2));print(out['inside_footprint_dtm_scene_stats'],out['outside_3m_ring_dtm_scene_stats'])
