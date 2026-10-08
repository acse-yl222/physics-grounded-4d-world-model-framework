"""Prepare additive batch integration after shard completion; does not run Blender."""
from pathlib import Path
import json,hashlib,sys
S=Path(__file__).resolve().parent;ROOT=S.parent.parent;R=S/'input/canary_wharf_20261007'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=S/'runs/canary_wharf_appearance_exterior_completion_014/region.blend';expected='c635a1e621e92c9a1cc715f0073a61072cb239f9b547691d5e35544d5a0029a1';assert sha(source)==expected
components=[];seen=set();timing=[]
for arg in sys.argv[1:]:
 p=Path(arg).resolve();d=json.loads((p/'summary.json').read_text());assert not d.get('in_progress');assert d['replace_names']==[];assert d['source_sha256']==expected
 owners={o for f in d['owners']for o in f['owner_ids']};assert not seen&owners;seen|=owners
 for f in d['owners']:
  assert f['budget_seconds']<=60
  assert f['status']!='built' or f['elapsed_seconds']<=60.1
 components.append({'label':p.name,'native':str((p/'candidate.blend').relative_to(ROOT)),'sha256':sha(p/'candidate.blend'),'replace_names':[],'add_names':d['add_names'],'owners':sorted(owners),'source_files':[str(x.relative_to(ROOT))for x in p.iterdir()if x.suffix in ['.json','.py','.md']]})
 timing.append({'shard':p.name,'owners':d['owners'],'shared_prepare_seconds':d['shared_prepare_seconds'],'shared_save_seconds':d['shared_save_seconds'],'total_seconds':d['total_seconds']})
assert len(components)==3
cfg={'source':str(source.relative_to(ROOT)),'source_sha256':expected,'output':str((R/'exports/appearance-fast-completion-015').relative_to(ROOT)),'components':components,'views':[{'name':'north-regional','target':[0,180,25],'offset':[-350,350,330],'scale':780},{'name':'south-regional','target':[0,-300,40],'offset':[350,-350,330],'scale':820}]}
(R/'references/fast015_assembly.json').write_text(json.dumps(cfg,indent=2));(R/'references/fast015_shard_timing.json').write_text(json.dumps(timing,indent=2));print('PREPARED',len(seen),'owners',sum(len(c['add_names'])for c in components),'additions')
