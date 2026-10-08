from pathlib import Path
exec(Path(__file__).with_name('owner87aa_review.py').read_text().split('rows=[]')[0])
q=ps[0];r=[]
for f in g['buildings']:
 if any(t in f['id'] for t in ['11cf1095','a749164c']):
  pp=poly(f);shared=q.boundary.intersection(pp.boundary);r.append({'id':f['id'],'mapped_xy_overlap_m2':q.intersection(pp).area,'shared_boundary_length_m':shared.length,'mapped_distance_m':q.distance(pp),'baseline_neighbor_height':f['height_m']})
(R/'references/owner87aa_interface.json').write_text(json.dumps(r,indent=2));print(r)
