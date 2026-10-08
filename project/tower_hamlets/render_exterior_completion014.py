"""Exposure-only entry inspection supplements. Never saves or modifies frozen region geometry."""
from pathlib import Path
import bpy,json,hashlib,time,math
from datetime import datetime,timezone
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/appearance-exterior-completion-014';path=O/'region.blend';before=hashlib.sha256(path.read_bytes()).hexdigest();start=time.time();bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;c=s.camera;cfg=json.loads((O/'assembly-config.json').read_text());s.cycles.samples=16;s.render.resolution_x=1400;s.render.resolution_y=1000;s.view_settings.exposure=2;rows=[]
for v in cfg['views']:
 if v['name'] not in ['park10low-whole-context','park10low-entry-context','discoverywest-entry-context']:continue
 target=Vector(v['target']);c.location=target+Vector(v['offset']);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type=v.get('camera_type','ORTHO');c.data.ortho_scale=v['scale'];
 if 'fov_degrees'in v:c.data.angle=math.radians(v['fov_degrees'])
 c.data.clip_start=.05;c.data.clip_end=3000;s.render.filepath=str(O/(v['name']+'-exposure-plus2.png'));st=time.time();bpy.ops.render.render(write_still=True);rows.append({'file':Path(s.render.filepath).name,'exposure_stops':2,'seconds':time.time()-st,'geometry_material_camera_changed':False})
assert hashlib.sha256(path.read_bytes()).hexdigest()==before;(O/'render-supplements.json').write_text(json.dumps({'native_sha256_unchanged':before,'started_utc':datetime.fromtimestamp(start,timezone.utc).isoformat(),'finished_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.time()-start,'views':rows},indent=2))
