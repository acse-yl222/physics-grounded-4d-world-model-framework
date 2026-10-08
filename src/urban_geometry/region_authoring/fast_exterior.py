"""Budgeted, explicitly estimated surface facade baseline; run inside Blender.

blender -b -t 2 --python fast_exterior.py -- config.json
Config: source_blend, load_names (explicit targets + bounded obstacles), owners
[{id, owner_ids, object_names}], output_dir. Source meshes are never changed.
Owner records may group multiple mapped parts of one physical building. Sixty-second
SIGALRM covers facet discovery, generation and light checks per physical building;
timeout rolls back that building's additions. SIGALRM may deliver after a native C call; actual elapsed/overrun is reported, not an OS-process kill guarantee. Shared load/save is timed separately.
Not a detailed/as-built reconstruction: no booleans, entrances, roof changes or renders.
"""
from pathlib import Path
import datetime
import hashlib
import json
import math
import signal
import sys
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


class BudgetExpired(Exception):
    pass


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def geometry_record(ob):
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    fs = [list(f.vertices) for f in ob.data.polygons]
    return {'object': ob, 'vertices': vs,
            'tree': BVHTree.FromPolygons(vs, fs),
            'lo': Vector([min(v[k] for v in vs) for k in range(3)]),
            'hi': Vector([max(v[k] for v in vs) for k in range(3)])}


def blocked(point, records, own_name):
    # Nearest oriented surface detects an inside point as well as a coincident
    # neighboring wall; AABB rejection makes distant buildings inexpensive.
    for rec in records:
        if rec['object'].name == own_name:
            continue
        if any(point[k] < rec['lo'][k] - .17 or point[k] > rec['hi'][k] + .17 for k in range(3)):
            continue
        q, normal, _, distance = rec['tree'].find_nearest(point)
        if q is not None and (distance < .16 or (point - q).dot(normal) < -1e-5):
            return True
    return False


def add_box(buffers, material, origin, tangent, normal, l, r, z0, z1, d0, d1):
    assert r > l and z1 > z0 and d1 > d0
    vertices, faces = buffers.setdefault(material, ([], []))
    offset = len(vertices)
    for z in (z0, z1):
        for x, d in ((l, d0), (r, d0), (r, d1), (l, d1)):
            vertices.append(tuple(origin + tangent*x + normal*d + Vector((0, 0, z))))
    # tangent x outward = -Z; this ordering is outward and positive-volume.
    faces.extend([[offset+i for i in f] for f in
                  ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                   (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))])


def material(name, color, metal, rough):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = m.diffuse_color
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = rough
    return m


def author_family(family, records, materials, config):
    start = time.monotonic()
    started = utc()
    objects = []
    max_seconds = min(60., max(.000001, float(config.get('seconds_per_building', 60))))
    deadline = start + max_seconds
    def check():
        if time.monotonic() >= deadline:
            raise BudgetExpired()
    def alarm(*_):
        raise BudgetExpired()
    previous = signal.signal(signal.SIGALRM, alarm)
    counts = {'panes': 0, 'rejected': 0, 'planes': 0}
    error = None
    buffers_by_owner = {}
    pane_limit = min(int(config.get('max_panes_per_building', 600)), 1200)
    try:
        signal.setitimer(signal.ITIMER_REAL, max_seconds)
        all_groups = []
        for name in family['object_names']:
            check()
            rec = next(r for r in records if r['object'].name == name)
            ob = rec['object']
            owner = str(ob.get('building_id', ''))
            if owner not in family['owner_ids']:
                raise ValueError('Object ownership is outside explicit family: '+name)
            # Group coplanar native faces, including triangulated walls. The
            # actual source BVH, not their rectangular envelope, clips each pane.
            groups = {}
            normal_matrix = ob.matrix_world.to_3x3().inverted().transposed()
            for face in ob.data.polygons:
                n = (normal_matrix @ face.normal).normalized()
                if abs(n.z) > .015:
                    continue
                n.z = 0
                n.normalize()
                vs = [rec['vertices'][i] for i in face.vertices]
                d = n.dot(vs[0])
                key = (round(n.x, 4), round(n.y, 4), round(d, 3))
                group = groups.setdefault(key, {'normal': n, 'd': d, 'vertices': []})
                group['vertices'].extend(vs)
            for group in groups.values():
                n=group['normal'];t=Vector((-n.y,n.x,0));vs=group['vertices']
                width=max(t.dot(v)for v in vs)-min(t.dot(v)for v in vs)
                height=max(v.z for v in vs)-max(min(v.z for v in vs),0)
                if width>=1.2 and height>=1.2:
                    group.update(record=rec,owner=owner,name=name,area=width*height)
                    all_groups.append(group)
        # Allocate across the entire physical family before generating a wall;
        # coarsen continuous grids instead of leaving checkerboard gaps.
        all_groups=sorted(all_groups,key=lambda g:-g['area'])[:pane_limit]
        area=sum(g['area']for g in all_groups)
        remaining=max(0,pane_limit-len(all_groups))
        for group in all_groups:
            group['quota']=1+int(remaining*group['area']/area)
            check();rec=group['record'];owner=group['owner'];name=group['name']
            buffers=buffers_by_owner.setdefault(owner,{})
            n = group['normal']; t = Vector((-n.y, n.x, 0)); origin = n*group['d']
            vs = group['vertices']; xs = [t.dot(v) for v in vs]
            xmin, xmax = min(xs), max(xs)
            zmin = max(min(v.z for v in vs)+.5, .5)
            zmax = max(v.z for v in vs)-.65
            if xmax-xmin < 1.2 or zmax-zmin < 1.2:
                continue
            counts['planes'] += 1
            columns = max(1, math.floor((xmax-xmin)/3.5))
            rows = max(1, math.floor((zmax-zmin)/3.3))
            quota = group['quota']
            factor = max(1., math.sqrt(columns*rows/quota))
            columns = max(1, min(quota, math.floor(columns/factor)))
            rows = max(1, min(math.floor(rows/factor), quota//columns))
            dx = (xmax-xmin)/columns; dz = (zmax-zmin)/rows
            for row in range(rows):
                for col in range(columns):
                    check()
                    if counts['panes'] >= pane_limit:
                        break
                    l=xmin+col*dx+.28; r=xmin+(col+1)*dx-.28
                    z0=zmin+row*dz+.20; z1=zmin+(row+1)*dz-.35
                    if r-l < .5 or z1-z0 < .5:
                        continue
                    probes=[(l,z0),(r,z0),(r,z1),(l,z1),((l+r)/2,(z0+z1)/2)]
                    okay=True
                    for x,z in probes:
                        point=origin+t*x+Vector((0,0,z))
                        hit, no, _, distance=rec['tree'].ray_cast(point+n*.2,-n,.4)
                        if hit is None or abs(distance-.2)>.001 or no.dot(n)<.98 or blocked(point+n*.075,records,name):
                            okay=False;break
                    if not okay:
                        counts['rejected']+=1;continue
                    add_box(buffers,'glass',origin,t,n,l+.055,r-.055,z0+.055,z1-.055,.018,.038)
                    for a,b in ((l,l+.065),(r-.065,r)):
                        add_box(buffers,'frame',origin,t,n,a,b,z0,z1,.012,.085)
                    for a,b in ((z0,z0+.065),(z1-.065,z1)):
                        add_box(buffers,'frame',origin,t,n,l+.065,r-.065,a,b,.012,.085)
                    counts['panes']+=1
        for owner, buffers in buffers_by_owner.items():
            for kind,(vs,fs) in buffers.items():
                check()
                name='FastEstimated_'+hashlib.sha256(owner.encode()).hexdigest()[:12]+'_'+kind
                mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update()
                ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);objects.append(ob)
                mesh.materials.append(materials[kind]);ob['building_id']=owner
                ob['research_object_id']='fast-estimated-v1::'+owner+'::'+kind
                ob['basis']='Estimated surface-mounted facade baseline; no observed window count; source body/roof unchanged'
                ob['coverage']='Fast baseline only; no recess cuts, entrance or as-built verification'
                # Closed cube components, finite coordinates and positive box
                # dimensions checked by construction; verify normals/light counts.
                assert len(mesh.polygons)*4==len(mesh.vertices)*3
                assert all(math.isfinite(c)for v in mesh.vertices for c in v.co)
                check()
        status='built' if objects else 'skipped_no_exposed_panels'
    except BudgetExpired:
        for ob in objects:
            bpy.data.objects.remove(ob,do_unlink=True)
        objects=[];status='skipped_timeout';counts['panes']=0
    except Exception as exc:
        for ob in objects:
            bpy.data.objects.remove(ob,do_unlink=True)
        objects=[];status='skipped_error';counts['panes']=0
        error=type(exc).__name__+': '+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)
    return objects,dict(id=family['id'],owner_ids=family['owner_ids'],status=status,
                        started_utc=started,ended_utc=utc(),elapsed_seconds=time.monotonic()-start,
                        budget_seconds=max_seconds,budget_overrun_seconds=max(0.,time.monotonic()-deadline),error=error,add_names=[o.name for o in objects],**counts)


def run(config):
    began=time.monotonic();output=Path(config['output_dir']);output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    names=config['load_names']
    assert len(names)==len(set(names)), 'Duplicate selective names'
    with bpy.data.libraries.load(config['source_blend'],link=False)as(a,b):
        missing=set(names)-set(a.objects)
        if missing:raise ValueError('Missing native objects: '+str(missing))
        b.objects=list(names)
    for ob in b.objects:
        bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.update()
    originals=list(b.objects)
    records=[geometry_record(ob)for ob in originals if ob.type=='MESH']
    preparation=time.monotonic()-began
    mats={'glass':material('Fast estimated muted glazing',(.14,.23,.26),.3,.28),
          'frame':material('Fast estimated dark frame',(.13,.15,.16),.4,.4)}
    additions=[];reports=[];seen=set()
    for family in config['owners']:
        if seen.intersection(family['owner_ids']):raise ValueError('Owner in multiple physical families')
        seen.update(family['owner_ids'])
        obs,report=author_family(family,records,mats,config);additions.extend(obs);reports.append(report)
        (output/'summary.json').write_text(json.dumps({'owners':reports,'in_progress':True},indent=2))
    # Additive-only candidate: source objects never edited or silently replaced.
    for ob in originals:bpy.data.objects.remove(ob,do_unlink=True)
    saved=time.monotonic();bpy.ops.wm.save_as_mainfile(filepath=str(output/'candidate.blend'),compress=False)
    summary={'schema':'fast-exterior-estimated-v1','source_blend':config['source_blend'],
             'source_sha256':config.get('source_sha256'),'source_hash_status':'coordinator supplied, not reread by worker',
             'owners':reports,'add_names':[o.name for o in additions],'replace_names':[],
             'source_geometry_unchanged':True,'selective_loaded_objects':len(originals),
             'shared_prepare_seconds':preparation,'shared_save_seconds':time.monotonic()-saved,
             'total_seconds':time.monotonic()-began,'ended_utc':utc(),
             'limitations':'Surface-mounted estimated baseline only. Per-building generation/check budget excludes shared selective I/O/BVH setup and final save, reported separately. No per-building render, no real openings, no fabricated doors. Coordinator performs batch export/validation.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    run(json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text()))
