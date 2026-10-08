from pathlib import Path
import bpy,json,math,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'input/canary_wharf_20261007/exports/facade-pediment-pilot002';bpy.ops.wm.open_mainfile(filepath=str(O/'pediment.blend'));s=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();rows=[]
for kind,y,angles,expected in [('coffer_back',1.8,[(i+.5)*math.pi/8 for i in range(8)],5.5),('longitudinal_rib',1.8,[i*math.pi/8 for i in range(1,8)],5.33),('cross_rib',2.40,[(i+.5)*math.pi/8 for i in range(8)],5.33)]:
 for a in angles:
  hit,loc,n,idx,obj,mat=s.ray_cast(deps,Vector((0,y,8)),Vector((math.cos(a),0,math.sin(a))),distance=8);assert hit;rad=math.hypot(loc.x,loc.z-8);assert abs(rad-expected)<.005,(kind,a,obj.name,rad);rows.append({'kind':kind,'angle':a,'y':y,'first_object':obj.name,'radius_m':rad,'expected_radius':expected})
(O/'coffer_depth_checks.json').write_text(json.dumps({'native_sha256':hashlib.sha256((O/'pediment.blend').read_bytes()).hexdigest(),'radial_rays':rows,'passed':True,'recess_depth_m':.17,'scope':'Actualfrozenmesh radialdepth; noexactphotodimensionclaim'},indent=2))
