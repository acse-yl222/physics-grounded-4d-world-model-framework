"""Read-only native mesh audit. Never saves or mutates the pinned regional blend."""
from pathlib import Path
import bpy,json,hashlib,collections
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';src=R/'exports/appearance-colonnade-upper-bank-001/region.blend'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
before=sha(src);bpy.ops.wm.open_mainfile(filepath=str(src));owners={};unowned=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 bid=ob.get('building_id');alias=ob.get('aggregate_alias_id','')
 if not bid:unowned.append(ob.name);continue
 # Exact transformed vertex extrema, not camera bounds or geometry.json height.
 zz=[(ob.matrix_world@v.co).z for v in ob.data.vertices]
 if not zz:continue
 rec=owners.setdefault(str(bid),{'id':str(bid),'min_z_m':float('inf'),'max_z_m':float('-inf'),'mesh_count':0,'vertex_count':0,'aliases':[],'object_names':[]})
 rec['min_z_m']=min(rec['min_z_m'],min(zz));rec['max_z_m']=max(rec['max_z_m'],max(zz));rec['mesh_count']+=1;rec['vertex_count']+=len(zz);rec['object_names'].append(ob.name)
 if alias and alias not in rec['aliases']:rec['aliases'].append(str(alias))
after=sha(src);assert before==after,'Source changed during read; discard audit and rerun'
g=json.loads((R/'geometry.json').read_text());hist=json.loads((R/'references/region_building_height_audit.json').read_text());progress=json.loads((R/'progress.json').read_text());auds={r['id']:r for r in hist['buildings']};touched=set()
for rec in progress.get('appearance_studies',{}).get('records',[]):touched.update(rec.get('owner_ids',[]))
for rec in progress['buildings']:
 if rec.get('appearance_history'):touched.add(rec['id'])
aliases={a:bid for bid,r in owners.items() for a in r['aliases']};rows=[]
for f in g['buildings']:
 bid=f['id'];native=owners.get(bid) or owners.get(aliases.get(bid));a=auds.get(bid,{})
 if not a:continue
 med=a.get('surface_minus_terrain_median_m');height=native['max_z_m'] if native else None;delta=med-height if med is not None and height is not None else None
 basis=f.get('height_basis','');details=f.get('detail_parameters',{});prior=('lidar' in basis.lower() or bool(details.get('height_review')) or any(r['id']==bid and 'lidar' in r.get('evidence_reviewed','') for r in progress['buildings']))
 coverage=a.get('inset_sample_area_fraction',0);area=a.get('area_m2',0);spread=a.get('spread_m');cat='low_discrepancy_or_small'
 if bid in touched or (native and native['id'] in touched):cat='excluded_retained_appearance_history'
 elif prior:cat='prior_lidar_corrected_do_not_reduce_from_median'
 elif not native:cat='absent_or_unresolved_owner_alias'
 elif med is None:cat='no_historical_dsm_samples'
 elif coverage<.7:cat='partial_coverage_requires_spatial_audit'
 elif delta<-8 and med<height*.35:cat='epoch_or_dropout_only_no_height_reduction'
 elif f.get('source_properties',{}).get('has_parts') and area>=100 and abs(delta)>=8:cat='parent_parts_interface_audit_before_height'
 elif spread is not None and spread>50:cat='mixed_return_sampling_or_epoch_audit'
 elif area>=100 and abs(delta)>=8:cat='uncorrected_height_candidate'
 row={'id':bid,'name':f.get('name'),'parent_id':f.get('parent_id'),'area_m2':area,'classification':cat,'native_owner_id':native['id'] if native else None,'native_min_z_m':native['min_z_m'] if native else None,'native_max_z_m':height,'mesh_count':native['mesh_count'] if native else 0,'aliases':native['aliases'] if native else [],'geometry_json_height_m':f.get('height_m'),'geometry_height_basis':basis,'raw_source_height_m':f.get('source_properties',{}).get('height'),'raw_source_floors':f.get('source_properties',{}).get('num_floors'),'raw_source_records':f.get('source_properties',{}).get('sources',[]),'prior_lidar_corrected':prior,'historical_dsm_minus_dtm_median_m':med,'historical_spread_m':spread,'historical_inset_coverage':coverage,'historical_median_minus_native_max_m':delta,'priority':area*abs(delta or 0),'note':'DSM-minus-local-DTM versus native scene max is only prioritization; differing ground datum, roof slopes, facade projections and epochs prevent treating this difference as an error.'};rows.append(row)
rows.sort(key=lambda q:q['priority'],reverse=True)
report={'scope':'Pinned actual native region per-owner mesh extents, compared with historical 2m-inset DSM audit. Read-only; no new geometry or render.','source_blend':str(src),'source_blend_sha256_before':before,'source_blend_sha256_after':after,'source_unchanged':True,'input_sha256':{n:sha(R/n) for n in ['geometry.json','progress.json','references/region_building_height_audit.json']},'classification_counts':dict(collections.Counter(r['classification'] for r in rows)),'touched_ids_excluded':sorted(touched),'native_owner_count':len(owners),'native_alias_map':aliases,'unowned_mesh_names':unowned,'native_owners':list(owners.values()),'top10_useful_uncorrected_candidates':[r for r in rows if r['classification']=='uncorrected_height_candidate'][:10],'epoch_or_dropout_cases':[r for r in rows if r['classification']=='epoch_or_dropout_only_no_height_reduction'],'prior_lidar_corrected_cases':[r for r in rows if r['classification']=='prior_lidar_corrected_do_not_reduce_from_median'],'rows':rows,'limitations':['Native max includes authored parapets and detail; not roof median.','Epoch/dropout classification is a triage hypothesis, not verified construction chronology.','Historical raster has mixed 2017–2020 acquisition; mapped source circa2026.','Partial coverage <70% excluded from useful top10; inspect bounds before any reconstruction.','No geometry is altered and all whole-building completeness claims remain unresolved.']};out=R/'references/current_region_height_review_queue.json';out.write_text(json.dumps(report,indent=2));print(report['classification_counts']);print('TOP10');
for r in report['top10_useful_uncorrected_candidates']:print(r['id'],r['name'],r['native_max_z_m'],r['historical_dsm_minus_dtm_median_m'],r['area_m2'])
