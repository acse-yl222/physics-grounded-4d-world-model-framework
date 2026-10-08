"""Prepare additive batch integration after shard completion; does not run Blender."""
from pathlib import Path
import json,hashlib,sys
S=Path(__file__).resolve().parent;ROOT=S.parent.parent;R=S/'input/canary_wharf_20261007'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=S/'runs/canary_wharf_appearance_fast_completion_017/region.blend';expected='963a00fda071fd8dfffbe83a625feb30cef8632510fe213d3c7daaa80cafebe0';assert sha(source)==expected
components=[];seen=set();timing=[]
for arg in sys.argv[1:]:
 p=Path(arg).resolve();d=json.loads((p/'summary.json').read_text());assert not d.get('in_progress');assert d['replace_names']==[];assert d['source_sha256']==expected
 owners={f['owner_id']for f in d['targets']};assert not seen&owners;seen|=owners
 for f in d['targets']:
  assert f['budget_seconds']<=60
  assert f['status']!='built' or f['elapsed_seconds']<=60.1
 components.append({'label':p.name,'native':str((p/'candidate.blend').relative_to(ROOT)),'sha256':sha(p/'candidate.blend'),'replace_names':[],'add_names':d['add_names'],'owners':sorted(owners),'source_files':[str(x.relative_to(ROOT))for x in p.iterdir()if x.suffix in ['.json','.py','.md']]})
 timing.append({'shard':p.name,'targets':d['targets'],'total_with_IO_preview_seconds':d['total_with_IO_preview_seconds'],'shared_IO_preview_save_seconds':d['total_with_IO_preview_seconds']-sum(f['elapsed_seconds']for f in d['targets'])})
assert len(components)==3
proof=json.loads((Path(sys.argv[3])/'summary.json').read_text())['targets'][0]['support']
center=proof['center'][:2]+[proof['roof_z']+.5];offset=[proof['t'][i]*6-proof['n'][i]*8 for i in range(3)];offset[2]=10
cfg={'source':str(source.relative_to(ROOT)),'source_sha256':expected,'output':str((R/'exports/appearance-roof-completion-018').relative_to(ROOT)),'components':components,'views':[{'name':'large-roof-close','target':[-193,-264,27],'offset':[0,-8,180],'scale':110},{'name':'houses-roof-close','target':[-154,-405,12],'offset':[-20,-25,90],'scale':75},{'name':'roof-detail-close','target':center,'offset':offset,'scale':16}]}
(R/'references/roof018_assembly.json').write_text(json.dumps(cfg,indent=2));(R/'references/roof018_shard_timing.json').write_text(json.dumps(timing,indent=2));print('PREPARED',len(seen),'owners',sum(len(c['add_names'])for c in components),'additions')
