"""Conservative triangle/cell surface intersection and OWNER-LOCAL enclosed-air fill.
No scene-global closure, no roof-column extrusion. Existing triangles only.
"""
from collections import deque
import numpy as np

def triangle_cell(triangle, center, half):
    v=triangle-center;e=[v[1]-v[0],v[2]-v[1],v[0]-v[2]]
    axes=[np.cross(e[0],e[1])]+[np.cross(edge,axis)for edge in e for axis in np.eye(3)]
    if np.any(v.min(0)>half+1e-8)or np.any(v.max(0)<-half-1e-8):return False
    for a in axes:
        if np.dot(a,a)<1e-18:continue
        p=v@a;r=half*np.abs(a).sum()
        if p.min()>r+1e-8 or p.max()<-r-1e-8:return False
    return True

def owner_surface_fill(triangles, origin, spacing):
    tr=np.asarray(triangles,float);lo=np.floor((tr.min((0,1))-origin)/spacing).astype(int)-1;hi=np.floor((tr.max((0,1))-origin)/spacing).astype(int)+2;size=hi-lo;surf=np.zeros(tuple(size[::-1]),bool)
    for t in tr:
        a=np.maximum(lo,np.floor((t.min(0)-origin)/spacing).astype(int)-1);b=np.minimum(hi-1,np.floor((t.max(0)-origin)/spacing).astype(int))
        for iz in range(a[2],b[2]+1):
            for iy in range(a[1],b[1]+1):
                for ix in range(a[0],b[0]+1):
                    q=(iz-lo[2],iy-lo[1],ix-lo[0])
                    if not surf[q] and triangle_cell(t,origin+(np.array([ix,iy,iz])+.5)*spacing,spacing/2):surf[q]=True
    exterior=np.zeros_like(surf);q=deque()
    for z in range(surf.shape[0]):
        for y in range(surf.shape[1]):
            for x in range(surf.shape[2]):
                if (z in [0,surf.shape[0]-1]or y in [0,surf.shape[1]-1]or x in [0,surf.shape[2]-1])and not surf[z,y,x]:exterior[z,y,x]=True;q.append((z,y,x))
    while q:
        z,y,x=q.popleft()
        for zz,yy,xx in [(z-1,y,x),(z+1,y,x),(z,y-1,x),(z,y+1,x),(z,y,x-1),(z,y,x+1)]:
            if 0<=zz<surf.shape[0]and 0<=yy<surf.shape[1]and 0<=xx<surf.shape[2]and not surf[zz,yy,xx]and not exterior[zz,yy,xx]:exterior[zz,yy,xx]=True;q.append((zz,yy,xx))
    return lo,surf,~exterior & ~surf

def selftest(box):
    def triangles(lo,hi,omit=None):
        v,f=box(lo,hi);v=np.array(v);return [v[[p[0],p[i],p[i+1]]]for j,p in enumerate(f)if j!=omit for i in range(1,len(p)-1)]
    origin=np.array([-8.,-8.,-8.]);cell=2.
    def at(lo,surf,inside,p):
        ix=np.floor((np.array(p)-origin)/cell).astype(int)-lo;return bool(inside[ix[2],ix[1],ix[0]])
    lo,su,ins=owner_surface_fill(triangles((0,0,0),(24,24,24)),origin,cell);assert at(lo,su,ins,(11,11,11))
    lo,su,ins=owner_surface_fill(triangles((0,0,0),(24,24,24),omit=1),origin,cell);assert not at(lo,su,ins,(11,11,11))
    lo,su,ins=owner_surface_fill(triangles((0,0,16),(24,24,24)),origin,cell);assert not at(lo,su,ins,(11,11,15)) # lower surface, no filled undercroft
    tr=[]
    for a,b in [((0,0,0),(8,40,24)),((32,0,0),(40,40,24)),((8,0,0),(32,8,24)),((8,32,0),(32,40,24))]:tr.extend(triangles(a,b))
    lo,su,ins=owner_surface_fill(tr,origin,cell);assert not at(lo,su,ins,(19,19,11))
    return {'surface_closed_box_filled':True,'surface_open_box_not_filled':True,'surface_resolved_bridge_void':True,'surface_resolved_courtyard_void':True}
