"""Editable conceptual CAD assembly. Surveyed constraints and assumptions are separate."""
from pathlib import Path
import json,hashlib
import cadquery as cq
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/carpark-cad-001';O.mkdir(exist_ok=True)
g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if x['id']=='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);origin=[-280.,305.];datum=4.28000021;top=24.7868393486-datum
params={'local_origin_enu_m':origin,'vertical_reference_odn_m':datum,'source_floor_count':8,'assumed_deck_count':8,'assumed_deck_thickness_m':.28,'assumed_column_width_m':.5,'assumed_grid_spacing_m':12,'assumed_level_spacing_m':top/7,'scope':'Conceptual structural CAD, not surveyed as-built. Mapped footprint and holes retained; regular structure and floor elevations are assumptions. No invented windows or ramp geometry.'};(O/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
parts=[];meshes=[]
def add(name,shape,kind):
 assert shape.isValid() and shape.Volume()>0,name
 parts.append(shape);vs,fs=shape.tessellate(.05, .15);meshes.append({'name':name,'kind':kind,'vertices':[[v.x/1000+origin[0],v.y/1000+origin[1],v.z/1000] for v in vs],'faces':fs,'volume_m3':shape.Volume()/1e9})
def wire(ring,z):return cq.Wire.makePolygon([cq.Vector((x-origin[0])*1000,(y-origin[1])*1000,z*1000) for x,y in list(ring.coords)[:-1]],close=True)
# Exact mapped planar slab outlines including both holes. Lower storey arrangement estimated.
for i in range(8):
 level=i*top/7;outer=wire(p.exterior,level);holes=[wire(h,level) for h in p.interiors];solid=cq.Solid.extrudeLinear(outer,holes,cq.Vector(0,0,-280));add(f'Deck_{i+1:02d}_estimated',solid,'deck')
# Columns use an explicitly estimated regular grid, clipped by exact footprint.
minx,miny,maxx,maxy=p.bounds;n=0
for x in range(int(minx)+6,int(maxx),12):
 for y in range(int(miny)+6,int(maxy),12):
  if not p.buffer(-.5).covers(Point(x,y)):continue
  n+=1;shape=cq.Workplane('XY').box(500,500,(top-.28)*1000,centered=(True,True,False)).translate(((x-origin[0])*1000,(y-origin[1])*1000,0)).val();add(f'Column_{n:03d}_estimated',shape,'column')
# Perimeter safety rails are illustrative, not observed construction details.
for i in range(1,8):
 level=i*top/7
 for j,(a,c) in enumerate(zip(list(p.exterior.coords)[:-1],list(p.exterior.coords)[1:])):
  va=cq.Vector((a[0]-origin[0])*1000,(a[1]-origin[1])*1000,(level+.9)*1000);vb=cq.Vector((c[0]-origin[0])*1000,(c[1]-origin[1])*1000,(level+.9)*1000);d=vb-va
  add(f'Rail_{i}_{j}_estimated',cq.Solid.makeCylinder(45,d.Length,va,d.normalized()),'rail')
compound=cq.Compound.makeCompound(parts);cq.exporters.export(compound,str(O/'carpark.step'));reloaded=cq.importers.importStep(str(O/'carpark.step')).val();assert reloaded.isValid();assert abs(reloaded.Volume()-compound.Volume())/compound.Volume()<1e-6
(O/'mesh.json').write_text(json.dumps(meshes));(O/'cad_verification.json').write_text(json.dumps({'step_reimport_valid':True,'solid_count':len(parts),'volume_m3':compound.Volume()/1e9,'step_sha256':hashlib.sha256((O/'carpark.step').read_bytes()).hexdigest(),'footprint_area_m2':p.area,'footprint_holes':len(p.interiors),'limitations':['Uniform deck elevations do not yet reproduce observed sloped and raised upper surfaces.','Floor count is source-reported; deck interpretation, grid, rails and dimensions estimated.','Columns and slabs overlap at joints; assembly is separate valid solids, not fused manufacturing part.','No ramps, entrances, facade cladding or operational accessibility validation.']},indent=2)+'\n');print('CAD_STEP_VERIFIED',len(parts))
