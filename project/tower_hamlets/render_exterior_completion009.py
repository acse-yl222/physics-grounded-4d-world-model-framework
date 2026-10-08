from pathlib import Path
import bpy,json,hashlib,time
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/appearance-exterior-completion-009';st=time.time();h=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();before=h(O/'region.blend');bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));s=bpy.context.scene;target=Vector((388,-299,21));offset=Vector((0,28,10));c=s.camera;c.location=target+offset;c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=115;c.data.clip_start=.05;c.data.clip_end=3000;s.cycles.samples=16;s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.filepath=str(O/'water20-whole-context.png');bpy.ops.render.render(write_still=True);assert h(O/'region.blend')==before;(O/'camera-correction.json').write_text(json.dumps({'view':'water20-whole-context','target':list(target),'offset':list(offset),'scale':115,'reason':'Closer north camera in gap avoids foreground15Water occlusion; all scene meshes remain visible and unchanged.','native_unchanged_sha256':before,'seconds':time.time()-st},indent=2))
# Supplemental inspection images only: retain original regional-context images.
s.view_settings.exposure+=2
cfg=json.loads((O/'assembly-config.json').read_text());extra=[]
for v in cfg['views']:
 if v['name']not in ['water20-entry-context','water15-entry-context']:continue
 target=Vector(v['target']);c.location=target+Vector(v['offset']);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=v['scale'];name=v['name']+'-exposure-plus2.png';s.render.filepath=str(O/name);bpy.ops.render.render(write_still=True);extra.append(name)
assert h(O/'region.blend')==before
(O/'inspection-exposure.json').write_text(json.dumps({'images':extra,'adjustment':'Render-only exposure +2 stops; original context images preserved. No model/material/light changes, no native save.','native_unchanged_sha256':before,'total_camera_and_supplement_seconds':time.time()-st},indent=2))
