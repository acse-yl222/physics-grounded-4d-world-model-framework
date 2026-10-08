import bpy,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';old=R/'exports/appearance-owner-aliases-001/region.blend';new=R/'exports/appearance-discovery-west-001/region.blend';ID='overture-building-9846b4f7-d4b8-4038-bf9c-d513e4428466'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(v):
 if hasattr(v,'to_list'):return v.to_list()
 if hasattr(v,'to_dict'):return v.to_dict()
 return v
def snap(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  data={'vertices':[list(v.co) for v in o.data.vertices],'faces':[list(p.vertices) for p in o.data.polygons],'matrix':[list(r) for r in o.matrix_world],'materials':[m.name if m else None for m in o.data.materials],'material_indices':[p.material_index for p in o.data.polygons]}
  out[o.name]={'geometry_material_hash':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'building_id':o.get('building_id'),'source_owner_ids':plain(o.get('source_owner_ids',[])),'aggregate_alias_id':plain(o.get('aggregate_alias_id'))}
 return out
hashes={str(p):sha(p) for p in [old,new]};a=snap(old);b=snap(new);removed=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys());changed=[n for n in a.keys()&b.keys() if a[n]!=b[n]];assert len(removed)==1 and a[removed[0]]['building_id']==ID;assert len(added)==3 and all(b[n]['building_id']==ID and b[n]['source_owner_ids']==[ID] for n in added);assert not changed;assert hashes=={str(p):sha(p) for p in [old,new]}
r={'review':'Independent actual native comparison and actual image inspection','inputs_sha256':hashes,'removed':{n:a[n] for n in removed},'added':{n:b[n] for n in added},'unchanged_mesh_count':len(a.keys()&b.keys()),'changed_existing_meshes':changed,'existing_source_owner_ids_preserved':True,'comparison_fields':['all vertex positions','polygon topology','world matrix','material slots and indices','building_id','source_owner_ids','aggregate_alias_id'],'images_actually_viewed':['overview.png','discovery-west-context.png'],'visual_findings':['Overview contains complete region but target roof too small to inspect detail.','Context shows continuous main roof and both upper estimates clearly. Hilton foreground occludes lower south facade; Jemstock2 occludes part of eastern roof junction. No claim of all-sided facade validation.','No visible floating or macroscopic roof penetration in shown portions; prior isolated neighbor diagnostic provides additional coverage.'],'verification_json_consistent':True,'geometry_modified':False,'retention_script_executed':False,'limitations':['Material node values not independently diffed; slots and indices checked.','No independent render/photo realism claim. Existing standalone envelope uncertainties remain.']};out=R/'references/discovery_west_region_independent_review001.json';out.write_text(json.dumps(r,indent=2));print(out,len(a),len(b),len(changed))
