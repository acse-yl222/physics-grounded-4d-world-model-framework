"""Editable conceptual CAD assembly. Surveyed constraints and assumptions are separate."""
from pathlib import Path
import json,hashlib
import cadquery as cq
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/carpark-cad-002';O.mkdir(exist_ok=True)
g=json.loads((R/'geometry.json').read_text());b=next(x for x in g['buildings'] if x['id']=='overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c');p=unary_union([Polygon(q['outer'],q.get('holes',[])) for q in b['geometry']]);origin=[-280.,305.];datum=4.28000021;top=24.7868393486-datum
params={'local_origin_enu_m':origin,'vertical_reference_odn_m':datum,'source_floor_count':8,'assumed_deck_count':8,'assumed_deck_thickness_m':.28,'assumed_column_width_m':.5,'assumed_grid_spacing_m':12,'assumed_level_spacing_m':top/7,'scope':'Conceptual structural CAD, not surveyed as-built. Mapped footprint and holes retained; regular structure and floor elevations are assumptions. No invented windows or ramp geometry.'};(O/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
parts=[];meshes=[]
def add(name,shape,kind):
 shape=shape.fix()
 assert shape.isValid() and shape.Volume()>0,name
 parts.append(shape);vs,fs=shape.tessellate(.05, .15);meshes.append({'name':name,'kind':kind,'vertices':[[v.x/1000+origin[0],v.y/1000+origin[1],v.z/1000] for v in vs],'faces':fs,'volume_m3':shape.Volume()/1e9})
def wire(ring,z):return cq.Wire.makePolygon([cq.Vector((x-origin[0])*1000,(y-origin[1])*1000,z*1000) for x,y in list(ring.coords)[:-1]],close=True)

level_report=json.loads((R/'references/carpark_level_planes.json').read_text());main_report=json.loads((R/'references/carpark_main_plane.json').read_text())
main_half=Polygon([(-500,100),(-100,100),(-100,320.5-.32*240),(-500,320.5+.32*160)])
main_zone=p.intersection(main_half).intersection(box(-500,100,-262,500));remaining=p.difference(main_zone);upper_zone=remaining.intersection(box(-338,100,-290,500));lower_zone=remaining.difference(upper_zone)
zones=[('main_slope',main_zone,main_report),('upper_level',upper_zone,level_report['planes'][2]),('lower_level',lower_zone,level_report['planes'][0])]
assert abs(sum(poly.area for _,poly,_ in zones)-p.area)<1e-6
assert sum(a.intersection(b).area for i,(_,a,_) in enumerate(zones) for _,b,_ in zones[i+1:])<1e-6
def z_at(report,x,y):
 cx,cy=report['center_xy_m'];a,b,c=report['coefficients_odn_m'];return a+b*(x-cx)+c*(y-cy)-datum
def roof_z(x,y):
 return next(z_at(r,x,y) for _,poly,r in zones if poly.buffer(1e-7).covers(Point(x,y)))
def surface_wire(ring,report):
 return cq.Wire.makePolygon([cq.Vector((x-origin[0])*1000,(y-origin[1])*1000,z_at(report,x,y)*1000) for x,y in list(ring.coords)[:-1]],close=True)
for name,poly,report in zones:
 for j,part in enumerate([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
  part=part.simplify(1e-7,preserve_topology=True)
  solid=cq.Solid.extrudeLinear(surface_wire(part.exterior,report),[surface_wire(h,report) for h in part.interiors],cq.Vector(0,0,-280));add('Top_'+name+'_'+str(j),solid,'deck')
(O/'top_regions.json').write_text(json.dumps({'datum_odn_m':datum,'boundaries':'Estimated full-footprint completion: main y<320.5-.32*(x+340),x<-262; high remainder -338<x<-290; low remainder elsewhere. Not measured breaklines.','regions':[{'name':name,'area_m2':poly.area,'geometry':poly.__geo_interface__,'plane':report['coefficients_odn_m'],'center_xy_m':report['center_xy_m']} for name,poly,report in zones]},indent=2)+'\n')

# Lower storeys remain estimated.
for i in range(7):
 level=i*top/7;outer=wire(p.exterior,level);holes=[wire(h,level) for h in p.interiors];solid=cq.Solid.extrudeLinear(outer,holes,cq.Vector(0,0,-280));add(f'Deck_{i+1:02d}_estimated',solid,'deck')
# Columns use an explicitly estimated regular grid, clipped by exact footprint.
minx,miny,maxx,maxy=p.bounds;n=0
for x in range(int(minx)+6,int(maxx),12):
 for y in range(int(miny)+6,int(maxy),12):
  if not p.buffer(-.5).covers(Point(x,y)):continue
  n+=1;shape=cq.Workplane('XY').box(500,500,(roof_z(x,y)-.28)*1000,centered=(True,True,False)).translate(((x-origin[0])*1000,(y-origin[1])*1000,0)).val();add(f'Column_{n:03d}_estimated',shape,'column')
# Perimeter safety rails are illustrative, not observed construction details.
for i in range(1,7):
 level=i*top/7
 for j,(a,c) in enumerate(zip(list(p.exterior.coords)[:-1],list(p.exterior.coords)[1:])):
  va=cq.Vector((a[0]-origin[0])*1000,(a[1]-origin[1])*1000,(level+.9)*1000);vb=cq.Vector((c[0]-origin[0])*1000,(c[1]-origin[1])*1000,(level+.9)*1000);d=vb-va
  add(f'Rail_{i}_{j}_estimated',cq.Solid.makeCylinder(45,d.Length,va,d.normalized()),'rail')
compound=cq.Compound.makeCompound(parts);cq.exporters.export(compound,str(O/'carpark.step'));reloaded=cq.importers.importStep(str(O/'carpark.step')).val();assert reloaded.isValid();assert abs(reloaded.Volume()-compound.Volume())/compound.Volume()<1e-6
(O/'mesh.json').write_text(json.dumps(meshes));(O/'cad_verification.json').write_text(json.dumps({'step_reimport_valid':True,'solid_count':len(parts),'volume_m3':compound.Volume()/1e9,'step_sha256':hashlib.sha256((O/'carpark.step').read_bytes()).hexdigest(),'footprint_area_m2':p.area,'footprint_holes':len(p.interiors),'limitations':['Top uses observed plane equations with estimated full-footprint partitions/extrapolation. Lower deck levels still uniform assumptions.','Floor count is source-reported; deck interpretation, grid, rails and dimensions estimated.','Columns and slabs overlap at joints; assembly is separate valid solids, not fused manufacturing part.','No ramps, entrances, facade cladding or operational accessibility validation.']},indent=2)+'\n');print('CAD_STEP_VERIFIED',len(parts))
