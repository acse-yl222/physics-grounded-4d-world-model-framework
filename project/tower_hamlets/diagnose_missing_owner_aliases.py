from pathlib import Path
import bpy,json,hashlib
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/inventory-alias-diagnostic-001';O.mkdir(exist_ok=True);sources={'current':R.parent.parent/'runs/canary_wharf_appearance_cabot_place_facade_001/region.blend','carpark_original':R/'exports/carpark-exterior-005/carpark.blend','museum_original':R/'exports/warehouses-connected-002/museum.blend','museum_prior':R/'exports/museum-exterior-004/museum.blend'};result={};projections={}
for label,p in sources.items():
 before=hashlib.sha256(p.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(p));items=[];projections[label]=[]
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  if label=='current' and o.get('building_id') not in ['overture-building-6d05a9ee-8c19-448d-b29f-5c1bacd8651c','overture-building-dbe8f73e-e036-48c5-9059-bb6350356575']:continue
  if label=='museum_original' and o.name not in ['Museum_east_exterior_hypothesis','Museum_west_exterior_hypothesis']:continue
  points=[list(o.matrix_world@v.co) for v in o.data.vertices];faces=[list(f.vertices) for f in o.data.polygons];props={k:(v.to_list() if hasattr(v,'to_list') else v.to_dict() if hasattr(v,'to_dict') else v) for k,v in o.items()};key=hashlib.sha256(json.dumps(dict(points=points,faces=faces),sort_keys=True).encode()).hexdigest();mats=[dict(name=m.name,diffuse=list(m.diffuse_color)) if m else None for m in o.data.materials];items.append(dict(name=o.name,properties=props,geometry_sha256=key,vertices=len(points),polygons=len(faces),materials=mats,bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]));o.data.calc_loop_triangles()
  projections[label].append(dict(name=o.name,group='carpark' if label.startswith('carpark') or str(o.get('research_object_id','')).startswith('carpark-appearance::') else 'museum',triangles_xy=[[points[i][:2] for i in t.vertices] for t in o.data.loop_triangles]))
 assert hashlib.sha256(p.read_bytes()).hexdigest()==before;result[label]=dict(path=str(p),sha256=before,unchanged=True,objects=items)
(O/'native_diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');(O/'projected_triangles.json').write_text(json.dumps(projections)+'\n')
print({k:len(v['objects']) for k,v in result.items()})
