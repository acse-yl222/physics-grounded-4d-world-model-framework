"""Render from recorded Google request parameters; height remains an assumption."""
import hashlib
import json
import math
from pathlib import Path


def recorded_pose(bdir, anchor, rot, center, poly_mode):
    bdir = Path(bdir)
    path = bdir / 'image_camera.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    photo = bdir / 'streetview.png'
    if data.get('image_sha256') != hashlib.sha256(photo.read_bytes()).hexdigest():
        raise ValueError('Camera metadata does not match reference image')
    lat,lng,heading,pitch,fov=(float(data[k]) for k in ('lat','lng','heading','pitch','fov'))
    if not (0<fov<180 and -90<pitch<90):
        raise ValueError('Invalid recorded camera angles')
    px=(lng-anchor['lon0'])*111320*math.cos(math.radians(anchor['lat0']))
    py=(lat-anchor['lat0'])*110540
    gx,gy=math.sin(math.radians(heading)),math.cos(math.radians(heading))
    if not poly_mode:
        px,py=px-center[0],py-center[1]
        ca,sa=math.cos(-rot),math.sin(-rot)
        px,py=ca*px-sa*py,sa*px+ca*py
        gx,gy=ca*gx-sa*gy,sa*gx+ca*gy
    # Static Street View metadata does not provide camera height/elevation.
    height=float(data.get('assumed_camera_height',2.5))
    return {'location':[px,py,height],
            'target':[px+10*gx,py+10*gy,height+10*math.tan(math.radians(pitch))],
            'lens_mm':18/math.tan(math.radians(fov/2)),
            'height_assumed':True,'source':'Google panorama/request parameters'}


def blender_override(pose):
    if pose is None:
        return ''
    return (f"\ncam.location = {tuple(pose['location'])!r}\n"
            f"tgt.location = {tuple(pose['target'])!r}\n"
            "cam.data.sensor_fit = 'HORIZONTAL'\ncam.data.sensor_width = 36\n"
            f"cam.data.lens = {pose['lens_mm']!r}\n")


def recorded_top(bdir, anchor, rot, center, poly_mode):
    """Match a north-up Static Maps request's center and ground extent."""
    bdir=Path(bdir);path=bdir/'satellite_camera.json'
    if not path.exists():
        return None
    data=json.loads(path.read_text())
    if data['image_sha256'] != hashlib.sha256((bdir/'satellite.png').read_bytes()).hexdigest():
        raise ValueError('Satellite camera metadata does not match image')
    lat,lng=data['center'];zoom=int(data['zoom']);size=data['logical_size']
    if size[0]!=size[1]:
        raise ValueError('Current acceptance renderer requires a square satellite tile')
    span=156543.03392*math.cos(math.radians(lat))/(2**zoom)*size[0]
    px=(lng-anchor['lon0'])*111320*math.cos(math.radians(anchor['lat0']))
    py=(lat-anchor['lat0'])*110540
    if not poly_mode:
        px,py=px-center[0],py-center[1]
        ca,sa=math.cos(-rot),math.sin(-rot)
        px,py=ca*px-sa*py,sa*px+ca*py
    return {'center':[px,py],'span':span,'rotation_z':0 if poly_mode else -rot}


def top_override(pose):
    if pose is None:
        return ''
    return (f"\ncamT.location = ({pose['center'][0]!r}, {pose['center'][1]!r}, 300)\n"
            f"camT.data.ortho_scale = {pose['span']!r}\n"
            f"camT.rotation_euler = (0, 0, {pose['rotation_z']!r})\n")
