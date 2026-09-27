"""Bounded Jay Mews north-road connector; call after campus affine baking.
Only replaces new context-road triangles in a small campus-coordinate rectangle.
Inherited campus meshes/materials are read-only. No external geometry packages.
"""
import bpy
from mathutils import Vector

RECT=(-165.,257.,-157.3,260.)
WEST0,EAST0=-164.70033281407245,-157.65696419643825
WEST1,EAST1=-164.5109561242315,-158.4864260285151

def _clip(poly,axis,k,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-k)*(1 if positive else -1);db=(b[axis]-k)*(1 if positive else -1)
        if da>=-1e-10:out.append(a)
        if (da>1e-10 and db< -1e-10) or (da< -1e-10 and db>1e-10):
            t=da/(da-db);out.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    clean=[]
    for a in out:
        if not clean or (Vector(a)-Vector(clean[-1])).length>1e-8:clean.append(a)
    if len(clean)>1 and (Vector(clean[0])-Vector(clean[-1])).length<1e-8:clean.pop()
    return clean

def _height(triangles,x,y):
    for t in triangles:
        a,b,c=t;det=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(det)<1e-12:continue
        u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/det
        v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/det
        if min(u,v,1-u-v)>-2e-5:return u*a[2]+v*b[2]+(1-u-v)*c[2]
    raise ValueError('No original new-road height at connector end')

def build(root=None,road=None,inherited_road=None,scene=None):
    road=road or next(o for o in bpy.data.objects if o.get('research_object_id')=='extension::context::road-network')
    inherited_road=inherited_road or bpy.data.objects.get('Mapped roads | widths estimated')
    if road.get('jay_north_seam_patch_version')==1:return {'status':'already_applied','created':[]}
    if inherited_road is None:raise ValueError('Inherited road required as read-only material source')
    if any(abs(road.matrix_world[i][j]-(1 if i==j else 0))>1e-7 for i in range(4) for j in range(4)):raise ValueError('Requires campus coordinates already baked, identity matrix')
    asphalt=next((m for m in inherited_road.data.materials if m and 'asphalt' in m.name.lower()),None)
    if asphalt is None:raise ValueError('Inherited asphalt material not found')
    road.data.calc_loop_triangles();source=[([tuple(road.data.vertices[i].co) for i in t.vertices],t.material_index) for t in road.data.loop_triangles]
    local=[p for p,mi in source if max(q[1] for q in p)>=257 and min(q[1] for q in p)<=260.001 and max(q[0] for q in p)>=-165 and min(q[0] for q in p)<=-157.3]
    heights=[_height(local,x,260.) for x in (WEST1+1e-5,EAST1-1e-5)]
    vertices=[];faces=[];indices=[]
    def emit(poly,mi):
        if len(poly)<3:return
        for i in range(1,len(poly)-1):
            t=[poly[0],poly[i],poly[i+1]]
            if (Vector(t[1])-Vector(t[0])).cross(Vector(t[2])-Vector(t[0])).length*.5<=1e-10:continue
            start=len(vertices);vertices.extend(t);faces.append((start,start+1,start+2));indices.append(mi)
    removed_area=0.
    for poly,mi in source:
        if max(p[0] for p in poly)<=RECT[0] or min(p[0] for p in poly)>=RECT[2] or max(p[1] for p in poly)<=RECT[1] or min(p[1] for p in poly)>=RECT[3]:emit(poly,mi);continue
        rest=poly
        for axis,k,pos in [(0,RECT[0],True),(0,RECT[2],False),(1,RECT[1],True),(1,RECT[3],False)]:
            emit(_clip(rest,axis,k,not pos),mi);rest=_clip(rest,axis,k,pos)
            if not rest:break
        if len(rest)>2:
            removed_area+=sum(abs((rest[i][0]-rest[0][0])*(rest[i+1][1]-rest[0][1])-(rest[i][1]-rest[0][1])*(rest[i+1][0]-rest[0][0]))*.5 for i in range(1,len(rest)-1))
    mats=list(road.data.materials)
    if asphalt not in mats:mats.append(asphalt)
    mi=mats.index(asphalt);ys=[257.,257.25,257.75,258.5,259.25,260.];fractions={0.,1.}
    for tri in local:
        for a,b in zip(tri,tri[1:]+tri[:1]):
            if (a[1]-260)*(b[1]-260)<0:
                x=a[0]+(b[0]-a[0])*(260-a[1])/(b[1]-a[1]);t=(x-WEST1)/(EAST1-WEST1)
                if 1e-5<t<1-1e-5:fractions.add(t)
    fractions=sorted(fractions)
    def point(f,y):
        t=(y-257)/3;west=WEST0+(WEST1-WEST0)*t;east=EAST0+(EAST1-EAST0)*t
        endx=WEST1+(EAST1-WEST1)*f;endz=_height(local,min(EAST1-1e-5,max(WEST1+1e-5,endx)),260)
        h=max(0,(y-257.25)/2.75);return (west+(east-west)*f,y,.045*(1-h)+endz*h)
    for ya,yb in zip(ys,ys[1:]):
        for fa,fb in zip(fractions,fractions[1:]):emit([point(fa,ya),point(fb,ya),point(fb,yb),point(fa,yb)],mi)
    mesh=bpy.data.meshes.new('Jay north seam repaired context roads');mesh.from_pydata(vertices,[],faces);mesh.update()
    for m in mats:mesh.materials.append(m)
    for p,m in zip(mesh.polygons,indices):p.material_index=m
    # Inherited asphalt uses implicit UV and active vertex color. The frozen
    # campus road has metre-scaled UV=(campusX/3,campusY/3), active Color=white.
    uv=mesh.uv_layers.new(name='UVMap')
    color=mesh.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
    for i,loop in enumerate(mesh.loops):
        co=mesh.vertices[loop.vertex_index].co;uv.data[i].uv=(co.x/3.,co.y/3.)
        color.data[i].color=(1.,1.,1.,1.)
    mesh.color_attributes.active_color_index=0;mesh.color_attributes.render_color_index=0
    previous=road.data;road.data=mesh
    if previous.users==0:bpy.data.meshes.remove(previous)
    road['jay_north_seam_patch_version']=1
    return {'created':[],'status':'applied','coordinate_frame':'campus metres; M already baked','modified_object':road.name,'read_only_material_source':inherited_road.name,'scope_rectangle_xy':RECT,'removed_original_area_m2':removed_area,'connector_area_m2':((EAST0-WEST0)+(EAST1-WEST1))*1.5,'boundary_y257_z':.045,'boundary_y260_z_endpoints':heights,'material':asphalt.name,'old_campus_mesh_modified':False,'limits':['Localized estimated road-width transition, not survey evidence.','Original road material reused over connector; its next boundary at y260 still requires visual review.','No road/ground geometry outside rectangle intentionally changed; new side widths transition between measured authored endpoints.']}
