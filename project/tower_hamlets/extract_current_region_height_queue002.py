"""Read-only revision 002: explicit primary ownership, composite aliases and pending studies."""
from pathlib import Path
import bpy,json,hashlib,collections
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007'
src=P/'runs/canary_wharf_appearance_cabot_place_facade_001/region.blend'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
inputs=['geometry.json','progress.json','references/region_building_height_audit.json']
hashes={n:sha(R/n) for n in inputs}
g=json.loads((R/inputs[0]).read_text());progress=json.loads((R/inputs[1]).read_text());hist=json.loads((R/inputs[2]).read_text())
ids={f['id'] for f in g['buildings']};suffix={i.split('building-',1)[-1].split('part-',1)[-1]:i for i in ids}
def canon(x):
 x=str(x);return x if x in ids else suffix.get(x,x)
parent={}
def find(x):
 parent.setdefault(x,x)
 if parent[x]!=x:parent[x]=find(parent[x])
 return parent[x]
def union(a,b):
 a,b=find(a),find(b)
 if a!=b:parent[max(a,b)]=min(a,b)
before=sha(src);bpy.ops.wm.open_mainfile(filepath=str(src));meshes={};primary=collections.defaultdict(set);refs=collections.defaultdict(set);aliasmap=collections.defaultdict(set);unowned=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 bid=ob.get('building_id')
 if not bid:unowned.append(ob.name);continue
 bid=canon(bid);z=[(ob.matrix_world@v.co).z for v in ob.data.vertices]
 if not z:continue
 meshes[ob.name]={'min_z_m':min(z),'max_z_m':max(z),'vertices':len(z),'primary':bid};primary[bid].add(ob.name);find(bid)
 owners=ob.get('source_owner_ids',[])
 if isinstance(owners,str):
  try:owners=json.loads(owners)
  except Exception:owners=[owners]
 if not isinstance(owners,(list,tuple)):
  try:owners=list(owners)
  except Exception:owners=[]
 alias=ob.get('aggregate_alias_id')
 for raw in list(owners)+([alias] if alias else []):
  rid=canon(raw);refs[rid].add(ob.name);union(bid,rid)
  if alias and raw==alias:aliasmap[rid].add(bid)
assert sum(map(len,primary.values()))==len(meshes)
def extent(names):
 return {'min_z_m':min(meshes[n]['min_z_m'] for n in names),'max_z_m':max(meshes[n]['max_z_m'] for n in names),'mesh_count':len(names),'object_names':sorted(names)} if names else None
touched=set()
for rec in progress.get('appearance_studies',{}).get('records',[]):touched.update(map(canon,rec.get('owner_ids',[])))
for rec in progress.get('buildings',[]):
 if rec.get('appearance_history'):touched.add(canon(rec['id']))
touchedgroups={find(x) for x in touched}
pending={
 'e11ce207-cf69-46f8-8c2a-9aaea740ff3c':('Water15','water15-roof-study-001','Current roof applicability unresolved; composite local survey vintage unresolved.'),
 'f8ead506-e28b-4be6-a6f6-4c9b41183e76':('Water20','water20-massing-001','Standalone historical massing; current roof applicability unresolved.'),
 'fff0d9e0-18c9-4aff-a3f8-f805c34662fe':('12 Bank Street','fff0-roof-study-001','Design-stage 24 m occupied roof supports scale, not as-built roof morphology.'),
 '89962572-8843-4725-b0ee-29311954b535':('899 transport-adjacent','owner899-roof-study-001','Reviewed standalone pending integration/transport interface decision.')}
pending={canon(k):{'label':v[0],'study_path':str(R/'exports'/v[1]),'hold_reason':v[2],'study_exists':(R/'exports'/v[1]).exists()} for k,v in pending.items()}
auds={r['id']:r for r in hist['buildings']};pr={r['id']:r for r in progress.get('buildings',[])};rows=[]
for f in g['buildings']:
 bid=f['id'];a=auds.get(bid)
 if not a:continue
 direct=primary.get(bid,set());names=direct or refs.get(bid,set());n=extent(names);scope='direct_primary' if direct else ('composite_fallback_not_independent' if names else 'absent');group=find(bid)
 med=a.get('surface_minus_terrain_median_m');height=n['max_z_m'] if n else None;delta=med-height if med is not None and height is not None else None
 basis=f.get('height_basis','');details=f.get('detail_parameters',{});prior='lidar' in basis.lower() or bool(details.get('height_review')) or 'lidar' in pr.get(bid,{}).get('evidence_reviewed','')
 area=a.get('area_m2',0);coverage=a.get('inset_sample_area_fraction',0);spread=a.get('spread_m');cat='low_discrepancy_or_small'
 if bid in pending:cat='reviewed_standalone_pending_integration'
 elif bid in touched:cat='excluded_retained_appearance_history'
 elif group in touchedgroups:cat='excluded_retained_composite_group_history'
 elif scope=='composite_fallback_not_independent':cat='composite_alias_not_independent_candidate'
 elif prior:cat='prior_lidar_corrected_do_not_reduce_from_median'
 elif not n:cat='absent_or_unresolved_owner_alias'
 elif med is None:cat='no_historical_dsm_samples'
 elif coverage<.7:cat='partial_coverage_requires_spatial_audit'
 elif delta<-8 and med<height*.35:cat='epoch_or_dropout_only_no_height_reduction'
 elif f.get('source_properties',{}).get('has_parts') and area>=100 and abs(delta)>=8:cat='parent_parts_interface_audit_before_height'
 elif spread is not None and spread>50:cat='mixed_return_sampling_or_epoch_audit'
 elif area>=100 and abs(delta)>=8:cat='uncorrected_height_candidate'
 rows.append({'id':bid,'name':f.get('name'),'review_group_id':group,'classification':cat,'native_extent_scope':scope,'native_primary_owner_ids':sorted({meshes[x]['primary'] for x in names}),'native_min_z_m':n['min_z_m'] if n else None,'native_max_z_m':height,'mesh_count':len(names),'area_m2':area,'geometry_json_height_m':f.get('height_m'),'geometry_height_basis':basis,'raw_source_records':f.get('source_properties',{}).get('sources',[]),'historical_dsm_minus_dtm_median_m':med,'historical_spread_m':spread,'historical_inset_coverage':coverage,'historical_median_minus_native_max_m':delta,'priority':area*abs(delta or 0),'pending_study':pending.get(bid)})
rows.sort(key=lambda r:r['priority'],reverse=True);actionable=[];seen=set()
for r in rows:
 if r['classification']=='uncorrected_height_candidate' and r['review_group_id'] not in seen:actionable.append(r);seen.add(r['review_group_id'])
after=sha(src);assert before==after
assert hashes=={n:sha(R/n) for n in inputs},'Inputs changed during audit'
report={'revision':2,'source_blend':str(src),'source_blend_sha256_before':before,'source_blend_sha256_after':after,'source_unchanged':True,'input_sha256':hashes,'script_sha256':sha(Path(__file__)),'datum':'Native world z; regional datum ODN minus 4.28000021 m. Historical comparison is DSM minus local DTM and is only triage, not measured roof error.','vintage':'EA composite DSM/DTM; actual local survey vintage unresolved. Cached overlapping catalogue surveys are 2017/18 and 2020; this does not establish per-pixel dates.','ownership_method':'Each mesh counted once under building_id. Direct primary extents take precedence; source_owner_ids and aggregate_alias_id create many-to-many deduplicated fallback references and review groups, never replace direct part extents. Composite fallback rows are not independent candidates.','unique_owned_mesh_count':len(meshes),'primary_group_mesh_sum':sum(map(len,primary.values())),'unowned_mesh_names':unowned,'native_primary_owner_count':len(primary),'native_primary_owners':{k:extent(v) for k,v in primary.items()},'source_and_alias_reference_meshes':{k:sorted(v) for k,v in refs.items()},'review_groups':{k:sorted(x for x in parent if find(x)==k) for k in sorted({find(x) for x in parent})},'aggregate_alias_to_primary_ids':{k:sorted(v) for k,v in aliasmap.items()},'classification_counts':dict(collections.Counter(r['classification'] for r in rows)),'actionable_remaining_roof_candidates':actionable,'reviewed_standalone_pending':[r for r in rows if r['id'] in pending],'rows':rows,'limitations':['Native maxima include parapets, frames and details; historical raster median is not a roof plane.','Categorization is a review prioritization, not permission to extrude or reduce heights.','Retained history excludes repeat work but does not establish full facade or roof verification.','No geometry, native blend or historical report changed.']}
out=R/'references/current_region_height_review_queue002.json';out.write_text(json.dumps(report,indent=2))
lines=['# Actual native height review queue 002','',report['vintage'],'',report['datum'],'',f'Retained region: `{src}`. {len(meshes)} uniquely owned meshes; {len(rows)} historical inventory rows.','', '## New roof review candidates','']
for r in actionable:lines.append(f"- {r['id']} ({r['name'] or 'unnamed'}): native max {r['native_max_z_m']:.3f} m; historical DSM−DTM median {r['historical_dsm_minus_dtm_median_m']:.3f} m; area {r['area_m2']:.1f} m²; spread {r['historical_spread_m']:.2f} m. Spatial/identity audit required.")
if not actionable:lines.append('No new candidates satisfy the conservative unreviewed, direct-owner, area ≥100 m², discrepancy ≥8 m, coverage ≥70% filter.')
lines+=['','## Already reviewed standalone holds','']
for r in report['reviewed_standalone_pending']:lines.append(f"- {r['pending_study']['label']}: {r['pending_study']['hold_reason']}")
lines+=['','## Ownership and limitations','',report['ownership_method'],'']+report['limitations']
out.with_suffix('.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'counts':report['classification_counts'],'actionable':actionable,'report':str(out)},indent=2))
