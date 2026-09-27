"""Darwin Centre mapped modern envelope; bounded moderate-detail reconstruction.
Licensed2013 exterior/photo2011 aerial and EA1m relative roof heights.
Exterior door position and hidden elevations are estimates, not surveyed access.
"""
import math


def build(ctx,feature):
    glass=ctx.material('Darwin pale green screened curtain glazing',(.32,.49,.46),.36,.12)
    clear=ctx.material('Darwin recessed entrance glazing',(.07,.15,.15),.24,.08)
    metal=ctx.material('Darwin silver aluminium framing',(.56,.61,.60),.52,.4)
    roofmat=ctx.material('Darwin light grey curved roof',(.64,.68,.67),.74,.12)
    panel=ctx.material('Darwin estimated opaque rear panels',(.55,.60,.59),.78)
    shell=ctx.mesh('Darwin | independent modern curtain envelope')
    frames=ctx.mesh('Darwin | mullions transoms and inset doorway')
    roof=ctx.mesh('Darwin | broad curved south roof and lower north strip')
    base=float(feature.get('base_m',0));h=26.4;r=feature['geometry'][0]['outer'];nw,sw,se,ne=r
    W=math.dist(sw,se);D=math.dist(sw,nw)
    def P(u,v,z):
        f=u/W;g=v/D
        return(tuple((1-g)*((1-f)*sw[i]+f*se[i])+g*((1-f)*nw[i]+f*ne[i]) for i in (0,1))+(base+z,))
    entries=[]
    for ei,(a,b) in enumerate(zip(r,r[1:]+r[:1])):
        L=math.dist(a,b);ux,uy=(b[0]-a[0])/L,(b[1]-a[1])/L;nx,ny=uy,-ux;angle=math.atan2(uy,ux)
        def Q(s,z,out=0):return(a[0]+s*ux+out*nx,a[1]+s*uy+out*ny,base+z)
        south=ei==1;door=L*.5;lo,hi=door-1.2,door+1.2
        # Only one modelled external threshold; it is an explicit positional estimate.
        cuts=sorted(set([0.,L]+([lo,hi] if south else [])))
        for aa,bb in zip(cuts,cuts[1:]):
            bottom=.015+3.2 if south and lo<(aa+bb)/2<hi else 0.
            shell.face([Q(aa,bottom),Q(bb,bottom),Q(bb,h),Q(aa,h)],glass if ei!=3 else panel)
        if south:
            for s in (lo,hi):shell.face([Q(s,.015),Q(s,3.215),Q(s,3.215,-.45),Q(s,.015,-.45)],metal)
            for z in (.015,3.215):shell.face([Q(lo,z),Q(hi,z),Q(hi,z,-.45),Q(lo,z,-.45)],metal)
            shell.face([Q(lo,.015,-.45),Q(hi,.015,-.45),Q(hi,3.215,-.45),Q(lo,3.215,-.45)],clear)
            for s in (lo,door,hi):
                x,y,z=Q(s,1.615,-.40);frames.box(x,y,z,.07,.07,3.2,metal,angle)
            for z in (.055,3.175):
                x,y,_=Q(door,z,-.40);frames.box(x,y,base+z,2.4,.07,.07,metal,angle)
            entries.append({'id':'estimated_south_access','threshold_xyz':list(Q(door,.015)),'outward_normal':[nx,ny,0.],'clear_width_m':2.4,'door_leaf_depth_m':.45,'support_z':base+.015,'basis':'estimated access position; photographed approach obscured by Lodge/vegetation; coordinator ground/path check required'})
        # Photo-supported thin horizontal glazing bands; spacing remains estimated.
        count=max(1,round(L/3.5))
        for k in range(count+1):
            s=k*L/count;z0=3.215 if south and lo<s<hi else 0.
            x,y,z=Q(s,(z0+h)/2,.04);frames.box(x,y,z,.085,.13,h-z0,metal,angle)
        for j in range(1,20):
            z=j*h/20;spans=[(0.,L)]
            if south and z<3.215:spans=[(0.,lo),(hi,L)]
            for aa,bb in spans:
                x,y,_=Q((aa+bb)/2,z,.04);frames.box(x,y,base+z,bb-aa,.12,.055,metal,angle)
        # Upper and lower datum rails meet the actual facade, not floating decoration.
        for z in (.12,h):
            spans=[(0.,L)] if not south or z>3.215 else [(0.,lo),(hi,L)]
            for aa,bb in spans:
                x,y,_=Q((aa+bb)/2,z,.05);frames.box(x,y,base+z,bb-aa,.20,.16,metal,angle)
    def H(v):return 26.8+3.7*math.sin(math.pi*v/16.) if 0<=v<=16 else 26.8
    vc=sorted(set([0.,D,16.]+[D*j/56 for j in range(1,56)]))
    for va,vb in zip(vc,vc[1:]):
        roof.face([P(0,va,H(va)),P(W,va,H(va)),P(W,vb,H(vb)),P(0,vb,H(vb))],roofmat)
        for u in (0.,W):roof.face([P(u,va,h),P(u,vb,h),P(u,vb,H(vb)),P(u,va,H(va))],panel)
    for v in (0.,D):roof.face([P(0,v,h),P(W,v,h),P(W,v,H(v)),P(0,v,H(v))],metal)
    # Roof seams follow the fitted curve; no unidentifiable plant is fabricated.
    for u in [W*j/12 for j in range(1,12)]:
        for va,vb in zip(vc,vc[1:]):frames.beam(P(u,va,H(va)+.02),P(u,vb,H(vb)+.02),.018,metal,6)
    shell.surface(feature['geometry'],base,panel)
    objects=[m.done() for m in (shell,frames,roof)]
    return {'created':[o.name for o in objects],'parameters':{'mapped_width_m':W,'mapped_depth_m':D,'wall_height_m':h,'roof_low_m':26.8,'roof_crown_m':30.5,'height_basis':'EA2022 native1m DSM-DTM interpreted roof surfaces; rounded estimates'},'interfaces':{'entrances':entries},'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+['darwin-delgadosouza-exterior-2013','va-praefcke-aerial-a-2011','va-praefcke-aerial-b-2011','ea-lidar-composite-2022-tq27ne'])),'uncertainty':['Only way-4959883 rectangular modern footprint; neither adjacent historic Lodge nor full NHM complex.','Green curtain-wall grammar evidenced by2013 partial exterior; facade divisions, rear treatment and access position estimated.','2014 Cocoon interior inspected for identification only; interior not reconstructed.','Mapped west boundary differs by a few raster cells from roof returns; retain OSM outline.','No roof plant or unverified decorative details added.']}
