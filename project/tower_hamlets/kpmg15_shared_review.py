from pathlib import Path
exec(Path('project/tower_hamlets/kpmg15_review.py').read_text().split('rows=[]')[0])
neighbor=next(f for f in g['buildings'] if f['id'].startswith('overture-building-6e7e0de2'));q=poly(neighbor);shared=p.boundary.intersection(q.boundary);out={'shared_edge':shared.__geo_interface__,'strips':[]}
for side,domain in [('KPMG',p),('Fitch',q)]:
 for lo,hi in [(0,1),(1,2),(2,3)]:
  k=mask(domain.intersection(shared.buffer(hi)).difference(shared.buffer(lo)));out['strips'].append({'side':side,'distance':[lo,hi],'DSM_ODN':stats(z[k]),'DTM_ODN':stats(t[k]),'note':'Initialrasterwindow coversonlyup to3m outsideKPMG; no extrapolation.'})
out['limitation']='Shared-neighbor sourceflat68.5m is not datum-adjusted; candidate introduces heightstep relativeunchangedbaseline. Adjacent actualroof may differ; interface unresolved, not evidenceof exposedfacade.';(R/'references/kpmg15_shared_review.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
