"""Retain the first Canary Wharf massing baseline as a protocol run."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

repo=Path(__file__).resolve().parents[2]
scene=repo/'project/tower_hamlets';root=scene/'input/canary_wharf_20261007'
export=root/'exports/massing-001';run=scene/'runs/canary_wharf_massing_20261007'
run.mkdir(parents=True,exist_ok=False)
def write(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
g=json.loads((root/'geometry.json').read_text());audit=json.loads((root/'inventory_audit.json').read_text())
verification=json.loads((export/'verification.json').read_text())
xy=[p for f in g['buildings'] for part in f['geometry'] for p in part['outer']]
spatial={'frame':'ENU','units':'m','origin':{'longitude':-.0188,'latitude':51.5053,'height_m':0,
         'vertical_datum':'Unsurveyed local flat ground z=0; not Ordnance Datum'},
         'bounds_m':{'min':[min(p[0] for p in xy),min(p[1] for p in xy),-.1],
                     'max':[max(p[0] for p in xy),max(p[1] for p in xy),max(f.get('height_m',0) for f in g['buildings'])]}}
image_review={'google':{'geometry_derivation':'not_authorized','user_decision':'Use Google only for permitted discovery; use licensed imagery for reconstruction',
              'maps_url':'https://www.google.com/maps/@51.5053,-0.0188,16z','status':'viewing tool could not access map'},
 'aerial':{'url':'https://commons.wikimedia.org/wiki/File:Canary_Wharf_from_the_air_-_geograph.org.uk_-_4641680.jpg',
 'author':'Thomas Nugent','capture_date':'2015-08-28','license_url':'https://creativecommons.org/licenses/by-sa/2.0/',
 'status':'download_failed_http_403','actually_inspected':False,'used_for_geometry':False},
 'street':{'url':'https://commons.wikimedia.org/wiki/File:One_Canada_Square.jpg','author':'Kurkoe','capture_date':'2006',
 'license_url':'https://creativecommons.org/licenses/by-sa/4.0/','status':'text_only','actually_inspected':False,'used_for_geometry':False},
 'overpass':{'status':'request_failed_http_406','retry':False},
 'limitations':'No satellite, aerial or street image has been visually inspected or used in this baseline.'}
write(root/'references/imagery-review.json',image_review)
progress={'stage':'baseline_numerical_checks_passed','inventory_complete_relative_to_download':True,
 'real_world_inventory_complete':False,'buildings_in_source_inventory':371,'building_and_part_objects':439,
 'detailed_image_verified_buildings':0,'numerical_verified':True,'visual_reviewed':False,'delivered':False,
 'baseline_render_reviewed':True,'pending':'Accessible licensed aerial/street imagery and per-building detailed reconstruction',
 'buildings':[{'id':f['id'],'stage':'baseline_numerical_checks_passed','evidence_reviewed':'vector_only'} for f in g['buildings'] if f['kind']!='site']}
write(root/'progress.json',progress)
(root/'docs/STATUS.md').write_text('# Canary Wharf baseline — 2026-10-07\n\nSelected WGS84 rectangle: [-0.0260, 51.5008, -0.0116, 51.5098]. Origin: [-0.0188, 51.5053], local AEQD east/north metres.\n\n371 source building records, 79 part records; 439 rendered building/part objects after envelope subtraction, plus two cartographic support meshes. This is a massing baseline, not a completed image-backed reconstruction. 155 objects use source-reported height, 143 use floor count × assumed 3 m, and 141 use assumed 9 m. Native Blender and uncompressed GLB exported; independent GLB reimport verifies IDs, triangles, bounds, and material presence.\n\nOverview, opposite overview, top view and One Canada Square roof close-up were inspected. The mapped 210–235 m pyramid is present. No entrance or facade is verified. Long boundary-crossing buildings are deliberately retained; support is clipped to the rectangle.\n\nGoogle derivation is not authorized. User chose permitted Google discovery plus licensed alternative imagery. Wikimedia metadata identifies licensed aerial/street leads, but aerial download returned HTTP 403 and no actual source image was inspected. Detailed reconstruction remains pending accessible imagery.\n')
(root/'docs/UNCERTAINTY.md').write_text('# Uncertainty\n\nNo current aerial/street/satellite image verification. Source vintage varies; source update date is not capture date. Terrain/water levels estimated. Missing heights use 3 m per mapped floor or 9 m fallback. Parent remainder height can overestimate podiums. Boundary-crossing multipart buildings may need a wider evidence query. Roof shapes are flat except the individually authored One Canada Square pyramid. Doors, recessed glazing, facade materials, streets, furniture and vegetation have not been reconstructed. Export numerical tolerance does not imply geographical accuracy.\n')
(root/'references/ATTRIBUTION.md').write_text('# Sources\n\nBuildings and water: © OpenStreetMap contributors, Overture Maps Foundation, release 2026-09-23.1, ODbL. Per-feature contributors and source versions are retained in GeoJSON. https://docs.overturemaps.org/attribution/ and https://www.openstreetmap.org/copyright\n\nBoroughs: Greater London Authority / Ordnance Survey, OGL v3. Contains OS data © Crown copyright and database rights. https://data.london.gov.uk/dataset/london-boroughs-e55pw ; retrieved from https://gis.london.gov.uk/arcgis/rest/services/apps/BIDs_service_02/MapServer/6/query on 2026-10-07. Used only for the area map, not building dimensions.\n\nImagery leads and failed access are recorded in imagery-review.json. No third-party imagery or texture is embedded. Materials are procedural.\n')
for name in ['region.blend','region.glb','verification.json','overview.png','north-overview.png','roof-overview.png','one-canada-square-roof.png']:
    shutil.copy2(export/name,run/name)
shutil.copy2(root/'renders/area-selection.png',run/'area-selection.png')
shutil.copy2(root/'inventory_audit.json',run/'inventory_audit.json')
shutil.copy2(root/'references/ATTRIBUTION.md',run/'ATTRIBUTION.md')
write(run/'visual_review.json',{'master_sha256':sha(run/'region.blend'),
 'inspected_renders':['overview.png','north-overview.png','roof-overview.png','one-canada-square-roof.png'],
 'baseline_appearance_reviewed':True,'image_comparison_verified':False,'entrances_verified':False,
 'detailed_reconstruction_delivered':False,'observations':['Mapped pyramid visible; no occluding duplicate tower part.',
 'Untextured massing with estimated-height objects distinguished by material.',
 'Boundary-crossing structures retained outside flat support.']})
with zipfile.ZipFile(run/'source_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in root.rglob('*'):
        if path.is_file() and not any(s in path.relative_to(root).parts for s in ['exports','renders','__pycache__']):z.write(path,'authoring/'+str(path.relative_to(root)))
    for path in (repo/'src/urban_geometry/region_authoring').glob('*.py'):z.write(path,'repository-src/'+path.name)
    z.write(Path(__file__),'finalize_canary_baseline.py')
artifacts=[]
for path in sorted(run.iterdir()):
    if path.name=='region.glb':continue
    types={'.png':'image/png','.json':'application/json','.zip':'application/zip','.blend':'application/x-blender','.md':'text/markdown'}
    artifacts.append({'id':'source_snapshot' if path.suffix=='.zip' else path.stem.replace('-','_'),
                      'asset':path.name,'sha256':sha(path),'media_type':types[path.suffix]})
manifest={'schema_version':'1.1.0','scene_id':'tower_hamlets','simulation':'geometry','run_id':run.name,
 'status':'complete','created_at':'2026-10-07T09:00:00Z',
 'provenance':{'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'dirty':True,
 'parameters':{'representation':'massing_baseline','detailed_reconstruction_complete':False,'aoi_wgs84':[-.0260,51.5008,-.0116,51.5098],
               'projection':g['crs'],'default_height_m':9,'assumed_floor_height_m':3,'imagery_used':False},
 'inputs':[{'id':name,'sha256':sha(root/'references'/f'{name}.geojson')} for name in ['buildings','building_parts','water']]},
 'spatial':spatial,'time':{'unit':'s','samples':[]},
 'layers':[{'id':'geometry','kind':'mesh','format':'glb','asset':'region.glb','sampling':'static',
            'encoding':{'coordinate_frame':'glTF-y-up'},'display':{'widget':'mesh','capabilities':['pick','opacity']}}],
 'artifacts':artifacts}
write(run/'manifest.json',manifest)
write(scene/'project.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets','title':'Tower Hamlets · Canary Wharf massing baseline',
 'spatial':spatial,'inputs':[{'id':'overture_buildings','path':'input/canary_wharf_20261007/references/buildings.geojson',
 'source':'Overture Maps Foundation 2026-09-23.1 / OpenStreetMap','sha256':sha(root/'references/buildings.geojson'),'license':'ODbL-1.0'}],
 'default_view':'canary_wharf_baseline'})
(scene/'views').mkdir(exist_ok=True)
write(scene/'views/canary_wharf_baseline.json',{'schema_version':'1.1.0','scene_id':'tower_hamlets',
 'title':'Canary Wharf · unverified massing baseline','time_alignment':'relative','runs':[run.name],
 'layers':[{'run_id':run.name,'layer_id':'geometry','visible':True}]})
print(run/'manifest.json')
