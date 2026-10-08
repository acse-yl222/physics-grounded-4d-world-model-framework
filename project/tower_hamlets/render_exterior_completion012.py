from pathlib import Path
import bpy,json,hashlib,time
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/appearance-exterior-completion-012';st=time.time();h=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();before=h(O/'region.blend');bpy.ops.wm.open_mainfile(filepath=str(O/'region.blend'));s=bpy.context.scene;c=s.camera;c.data.type='ORTHO';c.data.clip_start=.05;c.data.clip_end=3000;s.cycles.samples=16;s.render.resolution_x=1400;s.render.resolution_y=1000
views=[{'name':'marketbuilding-whole-context','target':[474,-250,22.5],'offset':[-40,0,8],'scale':115},{'name':'locke-whole-context','target':[442,-121,28.5],'offset':[-25,-8,10],'scale':115},{'name':'brannan-boundary-context','target':[500,-218,4],'offset':[20,-15,9],'scale':35}]
def render(v,name=None):
 target=Vector(v['target']);c.location=target+Vector(v['offset']);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=v['scale'];s.render.filepath=str(O/((name or v['name'])+'.png'));bpy.ops.render.render(write_still=True)
for v in views:render(v)
(O/'camera-correction.json').write_text(json.dumps({'views':views,'reason':'Closer west-gap Locke and Market cameras plus supplemental Brannan source-ground eastern boundary; no ground extension or hidden neighbors.','native_unchanged_sha256':before},indent=2))
assert h(O/'region.blend')==before
# Optional reproducible supplements already delivered; run with -- --supplements.
import sys
if '--supplements' in sys.argv:
 s.view_settings.exposure+=2;extra=[]
 for v in json.loads((O/'assembly-config.json').read_text())['views']:
  if 'entry'not in v['name']:continue
  name=v['name']+'-exposure-plus2';render(v,name);extra.append(name+'.png')
 assert h(O/'region.blend')==before
 (O/'inspection-exposure.json').write_text(json.dumps({'images':extra,'adjustment':'Render-only exposure+2 stops; originals retained; no native/material/light changes.','native_unchanged_sha256':before,'seconds':time.time()-st},indent=2))
