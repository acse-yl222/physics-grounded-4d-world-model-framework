exec(__import__('pathlib').Path(__file__).with_name('owner1f92_ground_evidence.py').read_text().split('fig,ax=')[0])
O=R/'exports/owner1f92-ground-contact-001';O.mkdir(exist_ok=True)
mask=valid&np.array([p.buffer(3).covers(Point(e,n)) for e,n in zip(x.flat,y.flat)]).reshape(x.shape);idx={};verts=[]
for rr,cc in zip(*np.where(mask)):idx[(rr,cc)]=len(verts);verts.append([float(x[rr,cc]),float(y[rr,cc]),float(z[rr,cc])])
faces=[]
for (rr,cc),i in idx.items():
 if all(k in idx for k in [(rr+1,cc),(rr+1,cc+1),(rr,cc+1)]):
  j,k,l=[idx[t] for t in [(rr+1,cc),(rr+1,cc+1),(rr,cc+1)]];faces.extend([[i,j,k],[i,k,l]])
names=[n['name'] for n in gl['nodes'] if any(k in n.get('extras',{}).get('building_id','') for k in ['1f9270f4','00851081']) and 'mesh' in n]
d={'vertices':verts,'faces':faces,'source_names':names,'footprint_segments':[[list(a),list(b)] for q in polys for a,b in zip(list(q.exterior.coords),list(q.exterior.coords)[1:])],'dtm_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'datum':'ODN minus4.28000021m','missing_DTM_cells':0,'embed_m':.03};(O/'input.json').write_text(json.dumps(d));print(names,len(verts),len(faces))
