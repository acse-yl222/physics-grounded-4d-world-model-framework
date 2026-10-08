"""Prepare additive batch integration after shard completion; does not run Blender."""
from pathlib import Path
import json,hashlib,sys
S=Path(__file__).resolve().parent;ROOT=S.parent.parent;R=S/'input/canary_wharf_20261007'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=S/'runs/canary_wharf_appearance_roof_completion_018/region.blend';expected='1f2f1a6212bedd0a44db44f41715d3cf206982a2a6eabdc697b161385b5d3520';assert sha(source)==expected
components=[];seen=set();timing=[]
for arg in sys.argv[1:]:
 p=Path(arg).resolve();d=json.loads((p/'summary.json').read_text());assert not d.get('in_progress');assert d['replace_names']==[];assert d['source_sha256']==expected
 owners={f['owner_id']for f in d['targets']};assert not seen&owners;seen|=owners
 for f in d['targets']:
  assert f['budget_seconds']<=60
  assert not f.get('error'), f
  assert f['elapsed_seconds']<=60.1, f
  assert f['status']!='built' or f['elapsed_seconds']<=60.1
 assert sha(p/'candidate.blend')==d['candidate_sha256']
 components.append({'label':p.name,'native':str((p/'candidate.blend').relative_to(ROOT)),'sha256':sha(p/'candidate.blend'),'replace_names':[],'add_names':d['add_names'],'owners':sorted(owners),'source_files':[str(x.relative_to(ROOT))for x in p.iterdir()if x.suffix in ['.json','.py','.md']]})
 timing.append({'shard':p.name,'targets':d['targets'],'total_with_IO_preview_seconds':d['total_with_IO_preview_seconds'],'shared_IO_preview_save_seconds':d['total_with_IO_preview_seconds']-sum(f['elapsed_seconds']for f in d['targets'])})
assert len(components)==3
built=[f for d in timing for f in d['targets']if f['status']=='built']
views=[]
for variant,name in [('standard_two_units','standard-roof-detail'),('compact_one_unit','compact-roof-detail')]:
 proof=next(f['support']for f in built if f['support']['variant']==variant)
 center=proof['center'][:2]+[proof['roof_z']+.5];offset=[proof['t'][i]*6-proof['n'][i]*8 for i in range(3)];offset[2]=12
 views.append({'name':name,'target':center,'offset':offset,'scale':18 if variant=='standard_two_units'else 12})
views.insert(0,{'name':'south-roof-context','target':[-110,-390,18],'offset':[0,-60,220],'scale':300})
cfg={'source':str(source.relative_to(ROOT)),'source_sha256':expected,'output':str((R/'exports/appearance-roof-completion-019').relative_to(ROOT)),'components':components,'views':views}
(R/'references/roof019_assembly.json').write_text(json.dumps(cfg,indent=2));(R/'references/roof019_shard_timing.json').write_text(json.dumps(timing,indent=2));print('PREPARED',len(seen),'owners',sum(len(c['add_names'])for c in components),'additions')
