"""Coordinator integration for the visually deduplicated Thurloe crossing only."""
import json
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
from public_realm_crossings import build

def integrate(root,M):
 records=json.loads((root/'references/public_realm/crossing_module/inputs.json').read_text())['records']
 r=next(dict(r) for r in records if r['id']=='node-5146303890');scene=bpy.context.scene;bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();checks=[]
 u=r['crossing_unit_xy'];v=r['road_unit_xy'];x,y=r['position_authoring_xy_m'];w=r['stripe_width_m'];gap=r['stripe_gap_m'];depth=r['band_depth_m'];count=int((r['road_span_m']+gap)/(w+gap));total=count*w+(count-1)*gap
 for i in range(count):
  a=-total/2+i*(w+gap)
  for da,db in [(a,-depth/2),(a+w,-depth/2),(a+w,depth/2),(a,depth/2),(a+w/2,0)]:
   p=M@Vector((x+u[0]*da+v[0]*db,y+u[1]*da+v[1]*db,2));hit,loc,n,idx,ob,_=scene.ray_cast(deps,p,Vector((0,0,-1)),distance=3);rid=ob.get('research_object_id','') if hit else ''
   allowed=hit and n.z>.9 and (rid=='MESH-Mapped roads | widths estimated' or rid.startswith('extension::context::') and ob.get('semantic_type')=='road')
   if not allowed:raise ValueError('Crossing top surface is not verified road: '+rid)
   checks.append({'stripe':i,'point':list(loc),'road_id':rid})
 heights=[c['point'][2] for c in checks]
 if max(heights)-min(heights)>.0005:raise ValueError('Crossing needs nonplanar draping')
 r['ground_z']=sum(heights)/len(heights);r['ground_gradient_xy']=[0,0];r['ground_status']='45 stripe-corner/centre rays on top road surface; planar within 0.5mm';r['dedup_status']='Review007 old-scene crossing top view actually inspected; no existing white marking'
 col=bpy.data.collections.new('Extension | mapped Thurloe crossing');scene.collection.children.link(col);objects=build(col,[r])
 for ob in objects:ob.data.transform(M@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
 return objects,{'included_ids':[r['id']],'ground_checks':checks,'held_ids':[q['id'] for q in records if q['id']!=r['id']],'held_reason':'Queen Gate inherited path intersects road marking footprint','geometry_dimensions_estimated':True}
