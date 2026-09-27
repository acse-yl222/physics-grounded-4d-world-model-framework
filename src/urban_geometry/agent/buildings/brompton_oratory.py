"""Mapped main Oratory only: moderate-detail stone church, roof cross and dome.
EA1m relative roof heights; licensed historic exterior grammar. Dimensions estimated.
"""
import math


def build(ctx,feature):
    stone=ctx.material('Oratory pale Portland stone',(.66,.64,.57),.84)
    roofmat=ctx.material('Oratory aged lead roofs',(.25,.29,.28),.71,.22)
    glass=ctx.material('Oratory recessed dark windows',(.07,.10,.095),.28)
    wood=ctx.material('Oratory dark timber doors',(.15,.08,.045),.74)
    body=ctx.mesh('Oratory | mapped low aisles and pierced upper church')
    trim=ctx.mesh('Oratory | principal orders and entrance portico')
    roof=ctx.mesh('Oratory | raised nave transept dome and lantern')
    base=float(feature.get('base_m',0));a=(1219.4789299500408,-372.189153784886);b=(1255.0505879902048,-354.05470474716276);W=math.dist(a,b);tx,ty=(b[0]-a[0])/W,(b[1]-a[1])/W;nx,ny=-ty,tx;ang=math.atan2(ty,tx)
    def P(u,v,z):return(a[0]+u*tx+v*nx,a[1]+u*ty+v*ny,base+z)
    def uv(q):return((q[0]-a[0])*tx+(q[1]-a[1])*ty,(q[0]-a[0])*nx+(q[1]-a[1])*ny)
    def box(u,v,z,w,d,h,mat=stone):
        x,y,zz=P(u,v,z);trim.box(x,y,zz,w,d,h,mat,ang)
    # Real wall apertures with inset glass/door surfaces. Coordinates in local UV.
    def wall(q0,q1,z0,z1,opens=(),mat=stone):
        L=math.dist(q0,q1);du,dv=(q1[0]-q0[0])/L,(q1[1]-q0[1])/L;ou,ov=dv,-du
        def Q(s,z,d=0):return P(q0[0]+s*du-ou*d,q0[1]+s*dv-ov*d,z)
        xs=sorted(set([0.,L]+[q for op in opens for q in op[:2]]));zs=sorted(set([z0,z1]+[q for op in opens for q in op[2:4]]))
        for aa,bb in zip(xs,xs[1:]):
            for za,zb in zip(zs,zs[1:]):
                if not any(l<(aa+bb)/2<r and bot<(za+zb)/2<top for l,r,bot,top,m in opens):body.face([Q(aa,za),Q(bb,za),Q(bb,zb),Q(aa,zb)],mat)
        for l,r,bot,top,m in opens:
            dep=.55 if m==wood else .30
            body.face([Q(l,bot,dep),Q(r,bot,dep),Q(r,top,dep),Q(l,top,dep)],m)
            for aa,bb in [((l,bot),(r,bot)),((r,bot),(r,top)),((r,top),(l,top)),((l,top),(l,bot))]:body.face([Q(*aa),Q(*bb),Q(*bb,dep),Q(*aa,dep)],stone)
            for s in (l,r):trim.beam(Q(s,bot,-.04),Q(s,top,-.04),.10,stone,8)
            for z in (bot,top):
                d=dep-.05 if m==wood and z==bot else -.04
                trim.beam(Q(l-.12,z,d),Q(r+.12,z,d),.04 if m==wood and z==bot else .10,stone,8)
            if m==glass:trim.beam(Q((l+r)/2,bot,dep-.04),Q((l+r)/2,top,dep-.04),.055,stone,8)
    r=feature['geometry'][0]['outer']
    for aa,bb in zip(r,r[1:]+r[:1]):
        u0,v0=uv(aa);u1,v1=uv(bb)
        if abs(v0)<.01 and abs(v1)<.01:
            wall((u0,v0),(8.,0),0,14);wall((36.,0),(u1,v1),0,14)
            # Beam owns v=0, z=12..13.2; retain the two separate wall bands.
            for z0,z1 in ((11.8,12.0),(13.2,14.0)):
                body.face([P(8,0,z0),P(36,0,z0),P(36,0,z1),P(8,0,z1)],stone)
        else:
            wall((u0,v0),(u1,v1),0,14)
            trim.beam(P(u0,v0,13.8),P(u1,v1,13.8),.17,stone,8)
    body.surface(feature['geometry'],base,stone);roof.surface(feature['geometry'],base+14,roofmat)
    # Roof over portico has an underside; open sides remain genuine voids.
    box(22,2.1,12.6,28,4.2,1.2)
    entries=[]
    doors=[(s-1.3,s+1.3,.6,5.8,wood) for s in (14.,23.,32.)]
    wall((8,4.2),(36,4.2),.6,11.9,[(l-8,r-8,bot,top,m) for l,r,bot,top,m in doors])
    for s in (10.,18.,28.,35.):
        x,y,z=P(s,.6,.6);trim.lathe(x,y,z,[(.68,0),(.68,.3),(.48,.6),(.44,10.5),(.72,10.7),(.72,11.2)],stone,24)
    box(22,2.1,.275,28,4.2,.65)
    for j in range(1,5):box(22,-(4-j+.5)*.35,(j*.15-.05)/2,28,.35,j*.15+.05)
    for s in (14.,23.,32.):entries.append({'id':'portico_door_'+str(int(s)),'threshold_xyz':list(P(s,4.2,.6)),'outward_normal':[-nx,-ny,0.],'clear_width_m':2.6,'door_leaf_depth_m':.55,'support_z':base+.6,'stair_treads':4,'riser_m':.15,'tread_m':.35,'stairs_extent_xyz':[list(P(8,-1.4,-.05)),list(P(36,-1.4,-.05)),list(P(36,0,-.05)),list(P(8,0,-.05))],'bottom_approach_xyz':list(P(22,-1.6,0.)),'basis':'photo-informed entrance portico and estimated4step approach; dimensions/individual door centres not surveyed'})
    # Raised nave and transept: low aisles are not extruded to the whole dome height.
    for q0,q1 in [((13,4.5),(33,4.5)),((33,4.5),(33,77)),((33,77),(13,77)),((13,77),(13,4.5))]:
        L=math.dist(q0,q1);ops=[]
        if L>25:
            for c in [7.5+10*j for j in range(6)]:
                if c+1.3<L:ops.append((c-1.3,c+1.3,17.,23.,glass))
        else:ops=[(L/2-2.,L/2+2.,16.,24.,glass)]
        wall(q0,q1,14,25.5,ops)
        trim.beam(P(*q0,25.6),P(*q1,25.6),.23,stone,8)
    for u0,u1 in [(13,23),(23,33)]:roof.face([P(u0,4.5,27.4 if u0==23 else 25.5),P(u1,4.5,27.4 if u1==23 else 25.5),P(u1,77,27.4 if u1==23 else 25.5),P(u0,77,27.4 if u0==23 else 25.5)],roofmat)
    for q0,q1 in [((3,43),(39.7,43)),((39.7,43),(39.7,58)),((39.7,58),(3,58)),((3,58),(3,43))]:
        L=math.dist(q0,q1);wall(q0,q1,14,25.5,[(L/2-1.3,L/2+1.3,17.,23.,glass)])
    roof.face([P(3,43,25.5),P(39.7,43,25.5),P(39.7,50.5,29),P(3,50.5,29)],roofmat);roof.face([P(3,50.5,29),P(39.7,50.5,29),P(39.7,58,25.5),P(3,58,25.5)],roofmat)
    for v in (4.5,77):body.face([P(13,v,25.5),P(33,v,25.5),P(23,v,27.4)],stone)
    for u in (3,39.7):body.face([P(u,43,25.5),P(u,58,25.5),P(u,50.5,29)],stone)
    # Front giant pilasters and triangular pediment, sculptures deliberately simplified away.
    for u in (13.2,16.2,29.8,32.8):box(u,4.25,20,.5,.5,11)
    roof.face([P(12.5,4.1,25.5),P(33.5,4.1,25.5),P(23,4.1,31.2)],stone)
    for q0,q1 in [((12.5,25.5),(23,31.2)),((23,31.2),(33.5,25.5))]:trim.beam(P(q0[0],4.0,q0[1]),P(q1[0],4.0,q1[1]),.25,stone,8)
    # Drum, lead dome with major ribs, open lantern and terminal cross.
    cx,cy,_=P(23,50.5,0);roof.lathe(cx,cy,base+25.5,[(10.,0),(10.,2.)],stone,64);roof.lathe(cx,cy,base+27.5,[(10.0,0),(10.,1.),(9.4,1.4),(9.4,6.4),(9.8,6.6)],stone,64)
    profile=[(9.7,0),(9.65,1.),(9.2,3.5),(8.3,6.),(6.6,8.5),(4.0,10.5),(1.8,11.5)]
    roof.lathe(cx,cy,base+34.1,profile,roofmat,64)
    for j in range(12):
        th=j*math.tau/12
        for (r0,z0),(r1,z1) in zip(profile,profile[1:]):trim.beam((cx+r0*math.cos(th),cy+r0*math.sin(th),base+34.1+z0),(cx+r1*math.cos(th),cy+r1*math.sin(th),base+34.1+z1),.07,stone,8)
    for j in range(8):
        th=j*math.tau/8;x,y=cx+1.55*math.cos(th),cy+1.55*math.sin(th);trim.lathe(x,y,base+46,[(.22,0),(.22,3.3)],roofmat,12)
    roof.lathe(cx,cy,base+45.6,[(2.,0),(2.,.4)],roofmat,32);roof.lathe(cx,cy,base+49.3,[(2.,0),(2.,.4),(1.2,1.4),(.3,2.)],roofmat,32)
    trim.beam((cx,cy,base+51.3),(cx,cy,base+54.),.10,stone,8);trim.beam((cx-tx*.8,cy-ty*.8,base+53.3),(cx+tx*.8,cy+ty*.8,base+53.3),.10,stone,8)
    objects=[m.done() for m in (body,trim,roof)]
    return {'created':[o.name for o in objects],'parameters':{'aisle_height_m':14,'nave_eaves_m':25.5,'nave_ridge_m':27.4,'dome_crown_m':45.6,'lantern_cross_top_m':54.,'dome_center_xy':[cx,cy],'height_basis':'EA2022 native1m DSM-DTM interpreted main regions; heights rounded'},'interfaces':{'entrances':entries},'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+['oratory-wjfox-pd-exterior','va-praefcke-aerial-a-2011','ea-lidar-composite-2022-tq27ne'])),'uncertainty':['Only main way851727368; adjacent851727367 remains separate.','Historical photo-supported primary grammar; sculptures, dome oculus carving, minor chapels and secondary window counts simplified.','Stair count, door positions and metric details estimated; full-scene approach check required.']}
