"""Blender native, closed-component centre-sampled volumetric union (not columns).
Run blender -b -t 2 --python native_blend.py -- --source FILE --out DIRECTORY.
Components without a sample centre in their AABB are subgrid, explicitly counted.
Open components are reported and excluded; no invented closure or ground extrusion.
"""
import argparse, collections, hashlib, json, math, shutil, sys, time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_volume_surface as surface


def intervals(tree, x, y, lo, hi):
    """Even/odd crossings of ONE closed component; distinct solids are unioned later."""
    zs=[]; z=lo-1.; upper=hi+1.
    for _ in range(512):
        p,n,idx,d=tree.ray_cast(Vector((x,y,z)),Vector((0,0,1)),upper-z)
        if p is None:break
        if abs(n.z)>1e-7:zs.append(float(p.z))
        z=float(p.z)+max(1e-4,abs(float(p.z))*2e-7)
        if z>=upper:break
    if len(zs)%2:return [],zs
    return list(zip(zs[::2],zs[1::2])),None


def six_axis_enclosure(tree, point):
    proof=[]
    for dr in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
        direction=Vector(dr);hit,normal,idx,dist=tree.ray_cast(Vector(point),direction,2000.)
        if hit is None or normal.dot(direction)<=1e-5:return None
        proof.append(float(dist))
    return proof


def box(lo,hi):
    vs=[(x,y,z)for z in [lo[2],hi[2]]for y in [lo[1],hi[1]]for x in [lo[0],hi[0]]]
    fs=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    return vs,fs


def selftest():
    a,f=box((10,20,4),(18,28,12));tree=BVHTree.FromPolygons(a,f)
    assert intervals(tree,14,24,4,12)[0]==[(4.,12.)]
    assert intervals(tree,9,24,4,12)[0]==[]
    # Bridge roof elevated four metres: air underneath MUST survive.
    assert not any(l<=2<h for l,h in intervals(tree,14,24,4,12)[0])
    b,g=box((10,20,8),(18,28,16));t2=BVHTree.FromPolygons(b,g)
    zs=np.arange(0,20)+.5;mask=np.zeros(20,bool)
    for tr in [tree,t2]:
        for l,h in intervals(tr,14,24,0,20)[0]:mask|=(zs>=l)&(zs<h)
    assert np.array_equal(mask,(zs>=4)&(zs<16))
    # Four closed wall solids surrounding a courtyard; central shaft stays empty.
    for l,h in [((0,0,0),(2,10,10)),((8,0,0),(10,10,10)),((2,0,0),(8,2,10)),((2,8,0),(8,10,10))]:
        v,f=box(l,h);assert intervals(BVHTree.FromPolygons(v,f),5,5,0,10)[0]==[]
    assert six_axis_enclosure(tree,(14,24,8)) is not None
    assert six_axis_enclosure(tree,(14,24,2)) is None
    bv,bf=box((10,20,4),(18,28,12))
    assert six_axis_enclosure(BVHTree.FromPolygons(bv,bf),(14,24,8)) is not None
    assert six_axis_enclosure(BVHTree.FromPolygons(bv,bf[1:]),(14,24,8)) is None
    rv=[];rf=[]
    for l,h in [((0,0,0),(2,10,10)),((8,0,0),(10,10,10)),((2,0,0),(8,2,10)),((2,8,0),(8,10,10))]:
        q,g=box(l,h);off=len(rv);rv.extend(q);rf.extend(tuple(i+off for i in face)for face in g)
    assert six_axis_enclosure(BVHTree.FromPolygons(rv,rf),(5,5,5)) is None
    return {'six_axis_material_split_closed_box':True,'six_axis_open_box_rejected':True,'six_axis_courtyard_air':True,'six_axis_bridge_air':True,'translated_box':True,'overlap_union':True,'bridge_undercroft':True,'courtyard_hole':True}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--spacing',type=float,default=8);ap.add_argument('--origin',nargs=3,type=float,default=[-1120,-1008,0]);ap.add_argument('--shape',nargs=3,type=int,default=[64,256,256]);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);start=time.time();args.out.mkdir(parents=True,exist_ok=True)
    tests=selftest();tests.update(surface.selftest(box));sourcehash=hashlib.file_digest(args.source.open('rb'),'sha256').hexdigest();bpy.ops.wm.open_mainfile(filepath=str(args.source));origin=np.array(args.origin);nz,ny,nx=args.shape;cell=args.spacing;solid=np.zeros((nz,ny,nx),bool);centres=[origin[i]+(np.arange([nx,ny,nz][i])+.5)*cell for i in range(3)];counts=collections.Counter();bad=[];records=[];sampleproof=[]
    for oi,ob in enumerate(bpy.data.objects):
        if ob.type!='MESH':continue
        owner=ob.get('building_id');name=ob.name
        if not owner or owner=='site-support' or ob.get('semantic_type')not in (None,'building'):
            counts['excluded_site_or_unlabelled_objects']+=1;continue
        vs=np.array([tuple(ob.matrix_world@v.co)for v in ob.data.vertices],dtype=np.float64)
        if len(vs)==0:continue
        # Preserve native disconnected solids: welding touching boxes would merge
        # valid components and introduce false non-manifold edges/internal faces.
        unique=vs;inv=np.arange(len(vs));parent=np.arange(len(unique));faces=[]
        def find(x):
            while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
            return int(x)
        for p in ob.data.polygons:
            ids=[int(inv[i])for i in p.vertices];faces.append(ids)
            for j in ids[1:]:a,b=find(ids[0]),find(j);parent[b]=a
        groups=collections.defaultdict(list)
        for f in faces:groups[find(f[0])].append(f)
        # Retain native closed solids separately; weld only unresolved surface
        # components of this object, never already closed touching solids.
        native_closed=[];unresolved=[]
        for fs in groups.values():
            ed=collections.Counter(tuple(sorted((a,b)))for f in fs for a,b in zip(f,f[1:]+f[:1])if a!=b)
            if ed and all(n==2 for n in ed.values()):native_closed.append(fs)
            else:unresolved.extend(fs)
        if unresolved:
            coordmap={};rem={}
            for i in {j for f in unresolved for j in f}:
                key=tuple(np.round(unique[i],6));rem[i]=coordmap.setdefault(key,i)
            unresolved=[[rem[i]for i in f]for f in unresolved];wp={i:i for f in unresolved for i in f}
            def wf(i):
                while wp[i]!=i:wp[i]=wp[wp[i]];i=wp[i]
                return i
            for f in unresolved:
                for i in f[1:]:wp[wf(i)]=wf(f[0])
            wg=collections.defaultdict(list)
            for f in unresolved:wg[wf(f[0])].append(f)
            native_closed.extend(wg.values())
        groups=dict(enumerate(native_closed))
        obcount=collections.Counter();obbefore=int(solid.sum()) if oi%100==0 else None
        for fs in groups.values():
            ids=sorted({i for f in fs for i in f});v=unique[ids];lo=v.min(0);hi=v.max(0);axis=[np.where((c>=lo[i]-1e-7)&(c<=hi[i]+1e-7))[0]for i,c in enumerate(centres)]
            if any(len(x)==0 for x in axis):obcount['subgrid_or_outside_components']+=1;continue
            edges=collections.Counter(tuple(sorted((a,b)))for f in fs for a,b in zip(f,f[1:]+f[:1]) if a!=b)
            if not edges or any(n!=2 for n in edges.values()):
                obcount['open_or_nonmanifold_components']+=1;bad.append({'object':name,'owner':owner,'bounds':[lo.tolist(),hi.tolist()],'faces':len(fs),'bad_edges':sum(n!=2 for n in edges.values())});continue
            remap={i:j for j,i in enumerate(ids)};ff=[[remap[i]for i in f]for f in fs];tree=BVHTree.FromPolygons(v.tolist(),ff);obcount['closed_sampled_components']+=1
            for iy in axis[1]:
                for ix in axis[0]:
                    ints,odd=intervals(tree,float(centres[0][ix]),float(centres[1][iy]),float(lo[2]),float(hi[2]))
                    if odd is not None:
                        obcount['odd_crossing_rays']+=1
                        if len(bad)<2000:bad.append({'object':name,'odd_xy':[float(centres[0][ix]),float(centres[1][iy])],'crossings':odd})
                        continue
                    for l,h in ints:
                        iz=np.where((centres[2]>=l-1e-6)&(centres[2]<h-1e-6))[0];solid[iz,iy,ix]=True
                    if ints and len(sampleproof)<24:sampleproof.append({'object':name,'xy':[float(centres[0][ix]),float(centres[1][iy])],'inside_intervals':ints,'below_lowest_interval_air_for_this_component':True})
        counts.update(obcount);records.append({'name':name,'owner_id':owner,**obcount})
        if oi%250==0:print('progress',oi,dict(counts),flush=True)
    # Native presentation meshes may divide an enclosure among material objects.
    # Recover ONLY centres geometrically enclosed by actual owner surfaces in all
    # six axis directions, with outward-facing nearest hits. Never cap an opening.
    strict=solid.copy();np.save(args.out/'solid_strict_closed.npy',strict,allow_pickle=False)
    recover_owners=collections.defaultdict(list)
    for issue in bad:
        if 'bounds' not in issue:continue
        lo,hi=np.array(issue['bounds']);span=hi-lo
        if span.prod()>1000 and span[2]>8 and min(span[:2])>4:
            recover_owners[issue['owner']].append((lo,hi))
    recovery=[];normal_corrections=[]
    for owner,boxes in recover_owners.items():
        vv=[];ff=[]
        for ob in bpy.data.objects:
            if ob.type!='MESH' or ob.get('building_id')!=owner:continue
            off=len(vv);ov=[tuple(ob.matrix_world@v.co)for v in ob.data.vertices];vv.extend(ov)
            omin=min(v[2]for v in ov);omax=max(v[2]for v in ov)
            for p in ob.data.polygons:
                ids=list(p.vertices);zvalues=[ov[i][2]for i in ids];normal=ob.matrix_world.to_3x3().inverted().transposed()@p.normal
                desired=1 if all(abs(z-omax)<1e-5 for z in zvalues)else -1 if all(abs(z-omin)<1e-5 for z in zvalues)else 0
                if desired and normal.z*desired<0:
                    normal_corrections.append({'object':ob.name,'face_index':p.index,'z':zvalues[0],'before_normal_z_sign':1 if normal.z>0 else -1,'after_normal_z_sign':desired,'basis':'Exact native object extremal horizontal surface; orientation only, vertices unchanged'})
                    ids.reverse()
                ff.append([off+i for i in ids])
        tree=BVHTree.FromPolygons(vv,ff);lo=np.min([a for a,b in boxes],axis=0);hi=np.max([b for a,b in boxes],axis=0)
        axis=[np.where((c>=lo[i])&(c<=hi[i]))[0]for i,c in enumerate(centres)];added_count=0;tested=0;examples=[]
        for iz in axis[2]:
            for iy in axis[1]:
                for ix in axis[0]:
                    if solid[iz,iy,ix]:continue
                    pt=Vector((float(centres[0][ix]),float(centres[1][iy]),float(centres[2][iz])));valid=True;proof=[];tested+=1
                    proof=six_axis_enclosure(tree,pt);valid=proof is not None
                    if valid:
                        solid[iz,iy,ix]=True;added_count+=1
                        if len(examples)<4:examples.append({'point_enu':list(pt),'six_actual_boundary_distances':proof})
        recovery.append({'owner_id':owner,'tested_centres':tested,'recovered_centres':added_count,'examples':examples})
    before_surface=solid.copy();surface_reports=[]
    surface_owners={i['owner']for i in bad if 'roof floor hidden-wall shell' in i.get('object','').lower()}
    for owner in surface_owners:
        triangles=[]
        for ob in bpy.data.objects:
            if ob.type!='MESH' or ob.get('building_id')!=owner:continue
            vs=np.array([tuple(ob.matrix_world@v.co)for v in ob.data.vertices]);ob.data.calc_loop_triangles()
            triangles.extend(vs[list(t.vertices)]for t in ob.data.loop_triangles)
        lo,surf,inside=surface.owner_surface_fill(triangles,origin,cell);mask=surf|inside;new=0
        for z,y,x in np.argwhere(mask):
            ix,iy,iz=lo+np.array([x,y,z])
            if 0<=ix<nx and 0<=iy<ny and 0<=iz<nz:
                new+=not bool(solid[iz,iy,ix]);solid[iz,iy,ix]=True
        surface_reports.append({'owner_id':owner,'triangle_count':len(triangles),'surface_cells':int(surf.sum()),'enclosed_interior_cells':int(inside.sum()),'new_global_cells':new,'method':f'Actual triangle-AABB SAT conservative surface; owner-local exterior flood fill; {cell:g}m subgrid openings may close explicitly'})
    np.save(args.out/'solid_owner_surface_added.npy',solid & ~before_surface,allow_pickle=False)
    (args.out/'owner_surface_fill.json').write_text(json.dumps(surface_reports,indent=2))
    np.save(args.out/'solid_enclosure_added.npy',before_surface & ~strict,allow_pickle=False)
    counts['owner_surface_added_voxels']=int((solid & ~before_surface).sum())
    counts['six_axis_enclosure_recovered_voxels']=sum(x['recovered_centres']for x in recovery)
    (args.out/'query_normal_corrections.json').write_text(json.dumps(normal_corrections,indent=2))
    (args.out/'material_split_enclosure_recovery.json').write_text(json.dumps(recovery,indent=2))
    np.save(args.out/'solid.npy',solid,allow_pickle=False);np.save(args.out/'height_m.npy',np.max(np.where(solid,(np.arange(nz)[:,None,None]+1)*cell,0),axis=0).astype(np.float32));assert solid.any();assert not solid[-1].any()
    meta={'source':str(args.source.resolve()),'source_sha256':sourcehash,'shape_zyx':list(solid.shape),'axis_order':'zyx','spacing_xyz_m':[cell]*3,'source_region_origin_xyz_m':args.origin,'origin_xyz_m':args.origin,'frame':'ENU','geographic_origin':{'longitude':-.0188,'latitude':51.5053,'height_m':0,'vertical_datum':'Unsurveyed flat local z=0, not ODN'},'cell_centres':'ENU_xyz=origin_xyz+(index_xyz+0.5)*spacing_xyz','ground_boundary':'flat z=0; source ground/water excluded from building occupancy','method':'Closed-component even-odd ray interval union; diagnosed large open/material-split owners additionally require actual outward-facing boundaries along all six axes per centre; world transforms applied','counts':dict(counts),'occupied_voxels':int(solid.sum()),'top_layer_empty':bool(not solid[-1].any()),'self_tests':tests,'seconds':time.time()-start,'limits':[f'{cell:g}m centre sampling misses subgrid equipment/walls; no claim conservative surface voxelization.','Open/nonmanifold components enumerated; large owner enclosures recovered only by six actual outward boundary hits, never column-filled.',f'Diagnosed material-split tier shells use owner-local conservative triangle-cell surfaces and enclosed-air fill; sub-{cell:g}m openings may close.', 'Mask represents estimated source exterior, not surveyed buildings.','Padding has no supplied geometry and is not evidence of empty real surroundings.']};(args.out/'metadata.json').write_text(json.dumps(meta,indent=2));(args.out/'diagnostics.json').write_text(json.dumps({'objects':records,'issues':bad,'native_interval_probes':sampleproof},indent=2));shutil.copy2(__file__,args.out/'native_blend_source.py');shutil.copy2(surface.__file__,args.out/'native_volume_surface.py');print(json.dumps(meta),flush=True)
if __name__=='__main__':main()
