from pathlib import Path
import bpy,json,math
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan-west-high001';r=json.loads((O/'evaluation.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'morgan.blend'));s=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();rows=[]
for x,y,z in r['samples_xyz_odn']:
 hit,loc,n,i,obj,matrix=s.ray_cast(deps,Vector((x,y,150)),Vector((0,0,-1)),distance=160)
 assert hit
 rows.append({'x':x,'y':y,'dsm_odn':z,'mesh_odn':loc.z+r['datum'],'object':obj.name,'error_m':z-loc.z-r['datum']})
err=[v['error_m'] for v in rows];native={'cells':len(rows),'missing':0,'rmse_m':math.sqrt(sum(e*e for e in err)/len(err)),'mae_m':sum(abs(e) for e in err)/len(err),'rows':rows};(O/'frozen_mesh_evaluation.json').write_text(json.dumps(native,indent=2))
# Context is a review scene only; original standalone file is not overwritten.
source=P/'runs/canary_wharf_appearance_morgan_visibility_correction_001/region.blend';old=json.loads((R/'references/morgan_massing_study_002.json').read_text());names=[q['name'] for q in old['objects'] if q['building_id']!=r['zone']['owner']]
with bpy.data.libraries.load(str(source),link=False) as(a,b):b.objects=[n for n in names if n in a.objects]
for o in b.objects:bpy.context.collection.objects.link(o)
target=Vector((-352,-59,77));s.camera.location=target+Vector((75,90,48));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=65;s.render.filepath=str(O/'neighbor-context.png');bpy.ops.render.render(write_still=True)
(O/'context_check.json').write_text(json.dumps({'render_only_neighbor_names':[o.name for o in b.objects],'standalone_not_overwritten':True,'source_native':str(source),'interface_tests':r['cap']['interfaces']},indent=2))
