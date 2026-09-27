"""Run: blender --background --python src/urban_geometry/uav/generate_models.py"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent

def material(name, color, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = 0.32
    return m

def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj

def ellipsoid(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    o = bpy.context.object
    o.scale = scale
    return finish(o, name, mat)

def box(name, loc, scale, mat, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = o.modifiers.new('Rounded edges', 'BEVEL')
    mod.width = bevel
    mod.segments = 3
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o, name, mat)

def rod(name, a, b, radius, mat):
    d = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=d.length, location=(Vector(a)+Vector(b))/2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z','Y').to_euler()
    return finish(o, name, mat)

def rotor(name, loc, radius, angle=0, vertical=False):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = loc
    if vertical:
        root.rotation_euler.x = math.pi/2
    root.rotation_euler.z = angle
    hub = ellipsoid(name+'_hub', (0,0,0), (.027,.027,.022), metal)
    hub.parent = root
    for i in range(2):
        o = ellipsoid(name+'_blade_'+str(i), ((-1 if i else 1)*radius*.49, 0, 0), (radius*.51,radius*.105,.006), carbon)
        o.rotation_euler.x = .13
        o.parent = root

def camera(loc, size=1):
    x,y,z = loc
    rod('Gimbal_mount',(x,y,z+.08*size),loc,.018*size,metal)
    ellipsoid('Camera_gimbal',loc,(.06*size,.052*size,.046*size),carbon)
    rod('Camera_lens',(x,y-.04*size,z),(x,y-.065*size,z),.028*size,glass)

def multirotor(count, arm, prop):
    ellipsoid('Upper_shell',(0,0,.34),(.15 if count==4 else .23,.20 if count==4 else .26,.075),white if count==4 else orange)
    box('Lower_chassis',(0,0,.29),(.23,.29,.065),carbon)
    box('Battery',(0,.035,.407),(.115,.19,.045),carbon,.012)
    for i in range(count):
        t = 2*math.pi*i/count + math.pi/4 if count==4 else 2*math.pi*i/count
        x,y = arm*math.cos(t),arm*math.sin(t)
        rod('Arm_%02d'%i,(x*.22,y*.22,.32),(x,y,.34),.022 if count==4 else .03,carbon)
        rod('Motor_%02d'%i,(x,y,.325),(x,y,.389),.034,metal)
        rotor('Rotor_%02d'%i,(x,y,.408),prop,t+.25)
        ellipsoid('Navigation_light_%02d'%i,(x,y,.321),(.018,.018,.01),red if y<0 else green)
    for side in [-1,1]:
        for y in [-.10,.10]:
            rod('Landing_strut',(side*.10,y,.28),(side*.19,y,.055),.012,metal)
        rod('Landing_skid',(side*.19,-.24,.04),(side*.19,.24,.04),.015,carbon)
    if count==4:
        camera((0,-.13,.20))
    else:
        box('Cargo_case',(0,0,.16),(.27,.30,.17),white)
        for x in [-.09,.09]:
            box('Cargo_strap',(x,0,.16),(.023,.307,.178),carbon,.003)
        camera((0,-.27,.27),.8)
        rod('GPS_mast',(0,.12,.42),(0,.12,.52),.008,metal)
        ellipsoid('GPS_receiver',(0,.12,.53),(.04,.04,.012),white)

def wing(name, sections, mat):
    verts=[]
    for x,front,back,z,thick in sections:
        verts.extend([(x,front,z),(x,front+(back-front)*.3,z+thick),(x,back,z),(x,front+(back-front)*.3,z-thick*.4)])
    faces=[(3,2,1,0)]
    for i in range(len(sections)-1):
        for j in range(4):
            a=i*4+j; b=i*4+(j+1)%4
            faces.append((a,b,b+4,a+4))
    n=len(verts); faces.append(tuple(range(n-4,n)))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    return finish(obj,name,mat)

def fixedwing():
    ellipsoid('Fuselage',(0,0,.30),(.115,.73,.12),white)
    ellipsoid('Canopy',(0,-.29,.385),(.078,.23,.055),glass)
    for side in [-1,1]:
        wing('Main_wing',[(side*.065,-.25,.23,.32,.037),(side*.85,-.09,.23,.36,.023),(side*1.18,.03,.21,.40,.012)],white)
        wing('Wingtip_marking',[(side*1.08,-.006,.216,.387,.016),(side*1.18,.03,.21,.40,.012)],orange)
        wing('Tailplane',[(side*.035,.43,.69,.34,.018),(side*.40,.54,.70,.365,.009)],white)
    fin=wing('Vertical_stabilizer',[(0, .37,.70,0,.021),(.36,.59,.71,0,.008)],orange)
    fin.rotation_euler.y=-math.pi/2
    fin.location.z=.36
    rod('Nose_motor',(0,-.68,.30),(0,-.78,.30),.045,metal)
    rotor('Nose_propeller',(0,-.79,.30),.24,vertical=True)
    camera((0,-.25,.16),.7)
    for x,y in [(-.21,.12),(.21,.12),(0,-.48)]:
        rod('Wheel_strut',(x*.3,y,.25),(x,y,.065),.009,metal)
        rod('Wheel',(x-.018,y,.048),(x+.018,y,.048),.047,carbon)

report=[]
for name,builder in [('quadcopter',lambda:multirotor(4,.30,.145)),('hexacopter_cargo',lambda:multirotor(6,.48,.20)),('fixed_wing',fixedwing)]:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    white=material('Pearl shell',(.72,.79,.84),.2)
    carbon=material('Graphite',(.024,.033,.043),.3)
    metal=material('Motor aluminium',(.25,.29,.33),.8)
    orange=material('Safety orange',(.95,.19,.035),.15)
    glass=material('Lens blue',(.018,.10,.17),.7)
    red=material('Red navigation',(.85,.025,.018))
    green=material('Green navigation',(.025,.75,.16))
    builder()
    bpy.context.scene.unit_settings.system='METRIC'
    path=OUT/(name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert meshes and all(len(o.data.polygons)>0 for o in meshes)
    coords=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    dims=[round(max(v[i] for v in coords)-min(v[i] for v in coords),3) for i in range(3)]
    report.append(dict(file=path.name,bytes=path.stat().st_size,mesh_objects=len(meshes),triangles=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons),dimensions_blender_xyz_m=dims,reimport_verified=True))
    # Render the imported asset so the preview also verifies the actual deliverable.
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.samples=24
    scene.world.color=(.3,.3,.3)
    span=max(dims)
    bpy.ops.object.camera_add(location=(span*1.3,-span*1.65,span*1.1))
    cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,.25))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'; cam.data.ortho_scale=span*1.35; scene.camera=cam
    for loc,power,size in [((1,-2,4),450,4),((-3,-1,2),300,3),((0,3,3),500,2)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size
        light.rotation_euler=(Vector((0,0,.25))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=900; scene.render.resolution_y=700; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=True
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
