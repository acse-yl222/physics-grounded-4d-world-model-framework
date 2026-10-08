"""Record retained appearance history separately from evidence reconstruction status."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';p=R/'progress.json';progress=json.loads(p.read_text());history={};records=[]
for manifest in sorted((S/'runs').glob('canary_wharf_appearance_*/manifest.json')):
 m=json.loads(manifest.read_text());v=json.loads((manifest.parent/'verification.json').read_text());review=json.loads((manifest.parent/'visual_review.json').read_text())
 assert v['native_reopened'] and v['independent_glb_verified'] and review['inspected']
 record={'run_id':m['run_id'],'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'owner_ids':m['provenance']['parameters']['source_owner_ids'],'representation':m['provenance']['parameters']['representation'],'numerical_checks':'export/reimport only; not geographical accuracy','visual_review':'partial recorded views; not complete facade verification'};records.append(record)
 for bid in record['owner_ids']:history.setdefault(bid,[]).append(m['run_id'])
for row in progress['buildings']:
 if row['id'] in history:row['appearance_history']={'retained_runs':history[row['id']],'quality':'estimated appearance or component study; not full verified building'}
progress['appearance_studies']={'scope':'Historical retained optional views; counts are touched inventory IDs, not fully rebuilt buildings. Combined ownership and unchanged baseline subparts remain in this count.','touched_inventory_ids':len(history),'latest_retained_run':max(records,key=lambda q:json.loads((S/'runs'/q['run_id']/'manifest.json').read_text())['created_at'])['run_id'],'records':records,'fully_image_verified_buildings':0}
p.write_text(json.dumps(progress,indent=2)+'\n');print('Recorded appearance history for',len(history),'inventory IDs across',len(records),'retained runs')
