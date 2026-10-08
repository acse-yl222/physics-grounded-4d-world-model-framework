"""Render all changed feature IDs with real context and no asset relocation."""
import argparse
import sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--features',nargs='+',required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.run.resolve()
bpy.ops.wm.open_mainfile(filepath=str(root/'region.blend'))
scene=bpy.context.scene;cam=scene.camera
scene.render.resolution_x=1200;scene.render.resolution_y=900
for identity in args.features:
    objects=[o for o in scene.objects if o.get('building_id')==identity]
    if not objects:raise ValueError(identity)
    points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box]
    low=Vector([min(p[i] for p in points) for i in range(3)])
    high=Vector([max(p[i] for p in points) for i in range(3)])
    centre=(low+high)/2;span=max(high-low)
    for name,direction in [('roof',(0,-.6,1.4)),('front',(1,-1,.7)),('rear',(-1,1,.7))]:
        if identity in ['overture-part-a6f929ab-fd4c-385b-91cc-7e46d5a66a12','overture-part-e0db9847-57b0-3010-855f-42d610d4b350'] and name!='roof':
            # Elevated opposing oblique views avoid surrounding tower occlusion.
            # These inspect the canopy, not an unmodelled entrance.
            direction=(1,-.4,3.4) if name=='front' else (-1,.4,3.4)
        cam.location=centre+Vector(direction)*max(span,10)*2
        cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=max(span,10)*1.6
        scene.render.filepath=str(root/(identity+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
