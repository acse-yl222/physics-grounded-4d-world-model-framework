"""Retain coarse4km contextual geometry separately from untouched detailedcore."""
from pathlib import Path
import json,hashlib,shutil,datetime,subprocess,zipfile
root=Path(__file__).resolve().parents[2];scene=root/'project/tower_hamlets';inp=scene/'input/expanded4km_20261008';run=scene/'runs/canary_wharf_outer4km_geometry_021';run.mkdir(exist_ok=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for directory in ['outer','references','water','outer_grid16m','solver_grid8m']:shutil.copytree(inp/directory,run/directory,ignore=shutil.ignore_patterns('*.state'))
for name in ['ATTRIBUTION.md','region.json']:shutil.copy2(inp/name,run/name)
shutil.copy2(scene/'input/outer4km_20261008/osm/map.osm.provenance.json',run/'references/osm-water-provenance.json')
with zipfile.ZipFile(run/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED)as z:
 for f in [root/'src/urban_geometry/region_authoring/prepare_peripheral_overture.py',root/'src/urban_geometry/voxelization/peripheral_grid.py',root/'src/urban_geometry/region_authoring/osm_water_context.py',scene/'build_outer4km_context.py',Path(__file__),root/'cache/tower_hamlets/expanded4km/verify_glb.py']:
  z.write(f,str(f.relative_to(root)))
 z.write(scene/'input/outer4km_20261008/osm/map.osm.xml','inputs/osm-water-source.xml')
 for name in ['solid.npy','metadata.json']:z.write(root/'cache/tower_hamlets/wind020_geometry'/name,'inputs/core8m/'+name)
check=json.load(open(run/'outer/glb-validation.json'));bounds=check['bounds_enu'];report=json.load(open(run/'outer/report.json'));wm=json.load(open(run/'water/metadata.json'));layers=[]
for ident,file in [('outer-buildings','outer.glb'),('outer-ground','outer-ground.glb'),('outer-water','outer-water.glb')]:layers.append({'id':ident.replace('-','_'),'kind':'mesh','format':'glb','asset':'outer/'+file,'sampling':'static','encoding':{'coordinate_frame':'glTF-y-up'},'display':{'widget':'mesh','capabilities':['pick','opacity']}})
art=[]
for p in sorted(run.rglob('*')):
 if p.is_file():art.append({'id':'source_snapshot' if p.name=='source_snapshot.zip' else str(p.relative_to(run)).replace('/','_').replace('.','_').replace('-','_'),'asset':str(p.relative_to(run)),'sha256':digest(p),'media_type':'application/octet-stream'})
manifest={'schema_version':'1.1.0','scene_id':'tower_hamlets','simulation':'geometry','run_id':run.name,'status':'complete','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provenance':{'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'dirty':True,'parameters':{'representation':'Coarse mapped footprint and source/assumed height exterior context; detailedcore remains separate untouched019layer','aoi_bounds_enu':[-2000,-2000,2000,2000],'source_release':'2026-09-23.1','building_part_records':report['retained_building_and_part_records'],'flat_visual_support_not_DTM':True,'outer_geographic_coverage':'Wholeintersectingfootprints retained; extends slightly outside4km','core_protection':'439 existingbuilding/part IDs + corefootprintunion and nominal1km protectedzone','water_surface':'SourceOSM polygons, fixedestimated z.01m outsideexistingcoreground'} ,'inputs':[{'id':str(inp/'references/buildings.geojson'),'sha256':report['source_hashes']['buildings.geojson']},{'id':str(inp/'references/building_parts.geojson'),'sha256':report['source_hashes']['building_parts.geojson']},{'id':wm['source'],'sha256':wm['source_sha256']}]},'spatial':{'frame':'ENU','units':'m','origin':json.load(open(scene/'project.json'))['spatial']['origin'],'bounds_m':{'min':[bounds[0][0],bounds[0][1],-.12],'max':bounds[1]}},'time':{'unit':'s','samples':[]},'layers':layers,'artifacts':art};(run/'manifest.json').write_text(json.dumps(manifest,indent=2));print(run)
