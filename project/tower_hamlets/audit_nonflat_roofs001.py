"""Read actual existing native geometry before scheduling mapped nonflat roofs."""
from pathlib import Path
import bpy,json,hashlib,collections
S=Path(__file__).resolve().parent;R=S/'input/canary_wharf_20261007';src=S/'runs/canary_wharf_appearance_owner836_001/region.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(src)
g=json.loads((R/'geometry.json').read_text())['buildings'];targets={b['id']:b for b in g if b.get('source_properties',{}).get('roof_shape') not in [None,'flat']}
bpy.ops.wm.open_mainfile(filepath=str(src));rows=[]
for bid,b in targets.items():
 obs=[o for o in bpy.data.objects if o.type=='MESH' and (o.get('building_id')==bid or bid in list(o.get('source_owner_ids',[])))];details=[]
 for o in obs:
  zs=[(o.matrix_world@v.co).z for v in o.data.vertices];normals=o.matrix_world.to_3x3().inverted().transposed();slopes=[]
  for f in o.data.polygons:
   n=(normals@f.normal).normalized()
   if .05<n.z<.999:slopes.append(round(n.z,5))
  details.append({'name':o.name,'primary_owner':o.get('building_id'),'vertices':len(zs),'z_min':min(zs) if zs else None,'z_max':max(zs) if zs else None,'unique_z_rounded_cm':len({round(z,2) for z in zs}),'upward_sloped_face_count':len(slopes),'slope_normal_z_values':sorted(set(slopes)),'height_basis':o.get('height_basis'),'coverage':o.get('coverage')})
 rows.append({'id':bid,'name':b.get('name'),'mapped_roof_shape':b['source_properties']['roof_shape'],'input_height_basis':b.get('height_basis'),'native_meshes':details,'next':'Review actual evidence and existing study history; counts do not establish roof correctness or lack of refinement.'})
assert sha(src)==before
out={'source':str(src),'sha256':before,'source_unchanged':True,'mapped_nonflat_owner_count':len(rows),'rows':rows,'limitation':'Sloped-face counts include gables/details and depend on normals; not a shape classifier or accuracy/completion claim.'}
(R/'references/nonflat_roof_native_audit001.json').write_text(json.dumps(out,indent=2)+'\n');print('Audited',len(rows),'mapped nonflat owners; native unchanged.')
