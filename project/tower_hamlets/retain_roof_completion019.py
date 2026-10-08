"""Retain reviewed additive roof019 as an optional run; never changes defaults."""
from pathlib import Path
import json,hashlib,shutil,zipfile
from datetime import datetime,timezone
S=Path(__file__).resolve().parent;ROOT=S.parent.parent;R=S/'input/canary_wharf_20261007';O=R/'exports/appearance-roof-completion-019';D=S/'runs/canary_wharf_appearance_roof_completion_019'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')
v=read(O/'verification.json');c=read(O/'assembly-config.json');review=read(O/'visual-review.json')
assert all(v[k]for k in ['native_reopened','independent_glb_verified','source_unchanged']);assert review['inspected'];assert not v['replaced'];assert v['unrelated_exact_geometry_properties_materials_uv']==4338
assert sha(O/'region.blend')==v['native_sha256'];assert sha(O/'region.glb')==v['glb_sha256'];assert sha(ROOT/c['source'])==c['source_sha256']
for comp in c['components']:assert sha(ROOT/comp['native'])==comp['sha256']
D.mkdir(exist_ok=False)
for f in O.iterdir():
 if f.is_file():shutil.copy2(f,D/f.name)
shutil.copy2(R/'references/ATTRIBUTION.md',D/'ATTRIBUTION.md')
with zipfile.ZipFile(D/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
 files=[S/'prepare_roof019_assembly.py',S/'assemble_accelerated_repairs002.py',Path(__file__),ROOT/'src/urban_geometry/region_authoring/fast_exterior.py',ROOT/'src/urban_geometry/region_authoring/fast_roof_details.py',R/'geometry.json',R/'references/sources.json',R/'references/roof019_scope.json',R/'references/roof019_shard_timing.json',O/'assembly-config.json']
 files += list((R/'references').glob('roof019_shard[0-2].json'))
 files += [S/'check_roof019_cross_owner.py',R/'references/roof019_cross_owner_overlap.json',ROOT/'cache/tower_hamlets/roof019/native-scan.json']
 files += [f for f in [R/'references/roof019_assembly_plan.json',R/'references/roof019_partial_family_followup.json',R/'references/roof019_remaining_audit.json',R/'references/roof019_final_coverage_audit.json',R/'references/roof019_generated_owners.json']if f.exists()]
 files += list((R/'exports/roof019_pilot').glob('*.json'))
 files += list((R/'exports/roof019_pilot').glob('*.png'))
 files += list((R/'exports/roof019_shard0').glob('*review*.png'))
 files += [f for f in [ROOT/'cache/tower_hamlets/roof019/prepare.py',ROOT/'cache/tower_hamlets/roof019/native-inspection.json']if f.exists()]
 for comp in c['components']:
  files += [ROOT/comp['native']]+[ROOT/f for f in comp['source_files']]
 for f in sorted(set(files)):z.write(f,str(f.relative_to(ROOT)))
 # Baseline retained native remains referenced by its immutable path and SHA instead of duplicate archive payload.
 z.writestr('baseline-reference.json',json.dumps({'path':c['source'],'sha256':c['source_sha256']}))
m=read((ROOT/c['source']).parent/'manifest.json');m.update(run_id=D.name,created_at=datetime.now(timezone.utc).isoformat());m['provenance']['parameters']={'representation':'Estimated restrained roof details; additive only, all existing bodies and roofs retained','not_as_built':True,'source_owner_ids':read(O/'batch-report.json')['actual_added_owner_ids'],'requested_owner_ids':sorted({o for comp in c['components']for o in comp['owners']}),'limitations':review['limitations'],'timing_note':'Per-family generation/light checks capped60seconds; shared loading/BVH/save/integration/browser time reported separately.'};m['provenance']['inputs']=[{'id':c['source'],'sha256':c['source_sha256']}]+[{'id':x['native'],'sha256':x['sha256']}for x in c['components']];m['spatial']['bounds_m']={'min':v['bounds_enu_m'][0],'max':v['bounds_enu_m'][1]}
types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown','.py':'text/x-python'}
m['artifacts']=[{'id':'source_snapshot'if p.name=='source_snapshot.zip'else p.name.replace('-','_').replace('.','_'),'asset':p.name,'sha256':sha(p),'media_type':types[p.suffix]}for p in sorted(D.iterdir())if p.suffix in types];write(D/'manifest.json',m)
print(D)
