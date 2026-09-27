"""Dana / Wellcome Wolfson Building: licensed courtyard facade + LiDAR roof.

Facade and detail estimates are explicit; the 2007 reference is not treated as
proof of post-2015 screen pattern or a surveyed street-side entrance.
"""
import math

SOURCES=['dana-azeraz-courtyard-2007','dana-brookbanks-engineering-text','dana-millimetre-screen-text','va-praefcke-aerial-a-2011','ea-lidar-composite-2022-tq27ne']

def build(ctx,feature):
    base=float(feature.get('base_m',0));parts=feature['geometry']
    concrete=ctx.material('Dana pale structural concrete',(.68,.69,.65),.82)
    glass=ctx.material('Dana cool reflective glazing',(.10,.17,.20),.24,.18,.18)
    clear=ctx.material('Dana courtyard transparent glazing',(.20,.26,.27),.22,.08,.48)
    frame=ctx.material('Dana dark anodised metal',(.075,.085,.085),.48,.45)
    white=ctx.material('Dana white powder coated aluminium',(.87,.88,.84),.5,.25)
    roofmat=ctx.material('Dana roof membrane',(.31,.32,.32),.84)
    inside=ctx.material('Dana shaded interior backing',(.13,.14,.13),.9)
    wall=ctx.mesh('mapped glazed envelope and slab edges')
    frames=ctx.mesh('curtain wall mullions and outer louvres')
    lower=ctx.mesh('courtyard concrete portico and projecting bay')
    stairs=ctx.mesh('visible glazed end stair flights')
    roof=ctx.mesh('closed LiDAR-informed roof and west atrium glazing')
    screen=ctx.mesh('interpreted post-2015 interior perforated screen')
    # Derive orthonormal source-coordinate axes from mapped south edge.
    ring=parts[0]['outer'];o=ring[0];end=ring[1];W=math.dist(o,end);ux,uy=(end[0]-o[0])/W,(end[1]-o[1])/W;vx,vy=-uy,ux
    def xy(p):return ((p[0]-o[0])*ux+(p[1]-o[1])*uy,(p[0]-o[0])*vx+(p[1]-o[1])*vy)
    def p(x,y,z):return(o[0]+ux*x+vx*y,o[1]+uy*x+vy*y,base+z)
    angle=math.atan2(vy,vx)
    def box(m,x,y,z,w,d,h,mat):m.box(*p(x,y,z),w,d,h,mat,angle)
    # box local width runs along building length (v), depth along -u.
    def face(m,vs,mat):
        clean=[]
        for v in vs:
            if not clean or math.dist(v,clean[-1])>1e-7:clean.append(v)
        if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
        if len(clean)<3:return
        a=clean[0]
        for b,c in zip(clean[1:],clean[2:]):
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            if sum((u[(i+1)%3]*v[(i+2)%3]-u[(i+2)%3]*v[(i+1)%3])**2 for i in range(3))>1e-14:m.face([a,b,c],mat)
    west_strip=2.6
    def height(x):return 21.1+2.2*min(1.,max(0.,x/west_strip))
    bounds=[xy(q) for q in ring];V=max(y for x,y in bounds)
    # Exact footprint side walls are glazing surfaces, not opaque solids with
    # dark rectangles pasted onto them. Thick slab edges/mullions are separate.
    for part in parts:
        for boundary in [part['outer']]+part.get('holes',[]):
            for a,b in zip(boundary,boundary[1:]+boundary[:1]):
                x0,y0=xy(a);x1,y1=xy(b);L=math.dist(a,b)
                if L<1e-5:continue
                east=min(x0,x1)>W-.15
                west=max(abs(x0),abs(x1))<.15
                cuts=[0.,1.]
                if (x0-west_strip)*(x1-west_strip)<0:cuts.append((west_strip-x0)/(x1-x0))
                cuts.sort()
                for ta,tb in zip(cuts,cuts[1:]):
                    xa,ya=x0+ta*(x1-x0),y0+ta*(y1-y0);xb,yb=x0+tb*(x1-x0),y0+tb*(y1-y0)
                    if west:
                        lo,hi=sorted([ya,yb]);door=V/2
                        for yl,yh in [(lo,door-1.1),(door+1.1,hi)]:
                            if yh>yl:face(wall,[p(0,yl,.05),p(0,yh,.05),p(0,yh,21.1),p(0,yl,21.1)],glass)
                        face(wall,[p(0,door-1.1,2.7),p(0,door+1.1,2.7),p(0,door+1.1,21.1),p(0,door-1.1,21.1)],glass)
                    else:face(wall,[p(xa,ya,.15),p(xb,yb,.15),p(xb,yb,height(xb)),p(xa,ya,height(xa))],clear if east else glass)
                tx,ty=(b[0]-a[0])/L,(b[1]-a[1])/L;ang=math.atan2(ty,tx)
                for z in [.15,8.2,11.7,15.2,18.7,21.0]:
                    if z+.15<min(height(x0),height(x1)):
                        if west and z<1.:
                            for yl,yh in [(min(y0,y1),V/2-1.1),(V/2+1.1,max(y0,y1))]:
                                if yh>yl:box(wall,0,(yl+yh)/2,z,yh-yl,.28,.24,concrete)
                        else:wall.box((a[0]+b[0])/2,(a[1]+b[1])/2,base+z,L,.28,.24,concrete,ang)
                n=max(1,round(L/1.15))
                for j in range(n+1):
                    t=j/n;x,y=x0+t*(x1-x0),y0+t*(y1-y0)
                    bot=2.75 if west and abs(y-V/2)<1.16 else .15
                    frames.box(*p(x,y,(height(x)+bot)/2),.065,.12,height(x)-bot,frame,ang)
                for z in [2.7,5.4,9.4,10.7,12.9,14.2,16.4,17.7,19.9]:
                    if z<min(height(x0),height(x1)):frames.box((a[0]+b[0])/2,(a[1]+b[1])/2,base+z,L,.10,.055,frame,ang)
        wall.surface([part],base+.02,concrete)
    # Courtyard frontage follows the actual east long segment, with glazed
    # stairs on its two returns. Portico proportions interpreted from CC image.
    long_east=max([(xy(a),xy(b)) for a,b in zip(ring,ring[1:]+ring[:1]) if min(xy(a)[0],xy(b)[0])>W-.15],key=lambda ab:math.dist(*ab))
    ylo,yhi=sorted([long_east[0][1],long_east[1][1]]);C=(ylo+yhi)/2;span=yhi-ylo
    # Upper sun-screen blades have a real gap to the curtain glazing.
    for j in range(44):
        z=8.6+j*.305
        if z>22.0:break
        box(frames,W+.28,C,z,span,.30,.10,frame)
    for j in range(9):
        y=ylo+j*span/8
        box(frames,W+.29,y,15.25,.09,.16,13.7,frame)
        for z in [8.6,12.,15.5,19.,22.]:box(frames,W+.17,y,z,.15,.38,.075,frame)
    # Six pale lower structural columns and continuous deep head beam.
    for f in [0.,.15,.38,.62,.85,1.]:
        y=ylo+span*f
        lower.beam(p(W+.16,y,.1),p(W+.16,y,8.05),.17,concrete,16)
        box(lower,W+.16,y,.15,.48,.48,.22,concrete)
    box(lower,W+.16,C,8.15,span+.6,.52,.45,concrete)
    # Projecting first-floor bay: deep returns, glazed sidelights and a white
    # central panel; its silhouette is present in the licensed 2007 image.
    bw=min(12.7,span*.57);bz0,bz1=4.45,7.8
    for z in [bz0,bz1]:box(lower,W+.55,C,z,bw,.75,.22,concrete)
    for y in [C-bw/2,C+bw/2]:box(lower,W+.55,y,(bz0+bz1)/2,.22,.75,bz1-bz0,concrete)
    box(lower,W+.42,C,(bz0+bz1)/2,bw*.51,.07,bz1-bz0-.24,white)
    for z in [5.55,6.7]:box(lower,W+.465,C,z,bw*.51,.012,.012,frame)
    box(lower,W+.465,C,(bz0+bz1)/2,.012,.012,bz1-bz0-.24,frame)
    for side in [-1,1]:
        cy=C+side*bw*.375
        face(lower,[p(W+.43,cy-bw*.115,bz0+.12),p(W+.43,cy+bw*.115,bz0+.12),p(W+.43,cy+bw*.115,bz1-.12),p(W+.43,cy-bw*.115,bz1-.12)],glass)
        for z in [5.55,6.7]:box(lower,W+.47,cy,z,bw*.23,.07,.04,frame)
    # Actual stair treads/landings are visible through end glazing in source.
    # Their unmeasured internal arrangement is an explicitly estimated fit.
    for cy in [ylo-2.0,yhi+2.0]:
        if not 2.<cy<V-2.:continue
        for level in range(6):
            z=level*3.5
            if z+3.5>21.1:continue
            for flight in [0,1]:
                x=W-1.05-flight*1.45
                for j in range(10):
                    y=cy-1.35+(j+.5)*.25 if flight==0 else cy+1.15-(j+.5)*.25
                    zz=z+flight*1.75+(j+1)*.175
                    box(stairs,x,y,zz-.045,.26,1.2,.09,concrete)
                y=cy+1.3 if flight==0 else cy-1.35
                box(stairs,W-1.77,y,z+(flight+1)*1.75-.055,.6,2.8,.11,concrete)
                a=p(x-.55,cy-1.3,z+flight*1.75+.85);b=p(x-.55,cy+1.2,z+(flight+1)*1.75+.85)
                if flight:a,b=p(x-.55,cy+1.2,z+flight*1.75+.85),p(x-.55,cy-1.3,z+(flight+1)*1.75+.85)
                stairs.beam(a,b,.028,frame,8)
                for side in [-1,1]:
                    za=z+flight*1.75;zb=za+1.75
                    ya,yb=(cy-1.35,cy+1.25) if flight==0 else (cy+1.25,cy-1.35)
                    stairs.beam(p(x+side*.5,ya,za-.08),p(x+side*.5,yb,zb-.08),.06,frame,8)
    # Post-2015 screen is independently supported by manufacturer text. The
    # exact pattern is NOT copied from unlicensed contemporary photographs.
    # Simplified open cells represent the screen rhythm; 4mm micro
    # perforations cannot be truthfully resolved by the available image.
    for panel in range(32):
        y0=ylo+.25+panel*(span-.5)/32;pw=(span-.5)/32
        z0,z1=3.1,7.65;x=W-.45
        # 2mm-thick folded panel with simplified larger open cells.
        rows=6;cols=2;dh=(z1-z0)/rows;dw=pw/cols
        for j in range(rows):
            for k in range(cols):
                yy=y0+(k+.5)*dw;zz=z0+(j+.5)*dh
                hole=min(dw*.55,dh*.55)
                # Open cells are a deliberate lower-detail approximation, not exact holes.
                box(screen,x,yy,zz-(dh+hole)/4,dw,.002,(dh-hole)/2,white)
                box(screen,x,yy,zz+(dh+hole)/4,dw,.002,(dh-hole)/2,white)
                for side in [-1,1]:box(screen,x,yy+side*(dw+hole)/4,zz,(dw-hole)/2,.002,hole,white)
        for y in [y0,y0+pw]:box(screen,x-.025,y,(z0+z1)/2,.012,.052,z1-z0,white)
    # Closed roof height field, using the 1m raster only for broad massing:
    # lower west atrium strip, main flat roof at 23.3m, small perimeter coping.
    def clip(poly,sign):
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            fa,fb=sign*(a[0]-west_strip),sign*(b[0]-west_strip)
            if fa>=-1e-8:out.append(a)
            if fa*fb< -1e-12:
                t=fa/(fa-fb);out.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
        return out
    for part in parts:
        for tri in part['triangles']:
            for sign in [-1,1]:face(roof,[p(x,y,height(x)) for x,y in clip([xy(q) for q in tri],sign)],glass if sign<0 else roofmat)
        for a,b in zip(part['outer'],part['outer'][1:]+part['outer'][:1]):
            x0,y0=xy(a);x1,y1=xy(b)
            cuts=[0.,1.]
            if (x0-west_strip)*(x1-west_strip)<0:cuts.append((west_strip-x0)/(x1-x0))
            cuts.sort()
            for ta,tb in zip(cuts,cuts[1:]):
                xa,ya=x0+ta*(x1-x0),y0+ta*(y1-y0);xb,yb=x0+tb*(x1-x0),y0+tb*(y1-y0)
                roof.beam(p(xa,ya,height(xa)),p(xb,yb,height(xb)),.065,frame,8)
    for j in range(max(1,int(V/1.15))):
        y=(j+.5)*V/max(1,int(V/1.15))
        roof.beam(p(0,y,21.13),p(west_strip,y,23.33),.045,frame,8)
    # Inner dark backdrop gives glazed elevation depth without claiming interiors.
    box(wall,W-3.8,C,11.5,span,.16,22.,inside)
    # Public Queen's Gate access is known, but precise current jamb location
    # is unobserved: this central west doorway is an explicit low-confidence
    # placement estimate under the requested lower-detail tolerance.
    dc=V/2
    face(lower,[p(.30,dc-1.1,.05),p(.30,dc+1.1,.05),p(.30,dc+1.1,2.7),p(.30,dc-1.1,2.7)],glass)
    for yy in [dc-1.1,dc,dc+1.1]:box(lower,.25,yy,1.375,.06,.10,2.65,frame)
    box(lower,.25,dc,2.7,2.26,.10,.06,frame)
    box(lower,-.1,dc,.025,2.5,1.,.05,concrete)
    for side in [-1,1]:lower.beam(p(.18,dc+side*.15,1.0),p(.18,dc+side*.15,1.5),.025,frame,8)
    entrances=[{'name':'Estimated west public entry '+str(side),'threshold_xyz':list(p(0,dc+side*.55,.05)),'outward_normal':[-ux,-uy,0.],'clear_width_m':1.03,'door_leaf_depth_m':.3,'status':'central west placement estimated; current entrance not resolved by licensed photo'} for side in [-1,1]]
    created=[m.done().name for m in [wall,frames,lower,stairs,roof,screen] if m.v]
    return {'created':created,'parameters':{'wall_height_m':23.3,'roof_top_m':23.37,'levels_interpreted':6,'height_status':'EA 1m DSM-DTM supports roof about23m; individual facade bands estimated','facade_status':'licensed east courtyard facade with explicit estimated post-2015 screen','window_openings':'curtain-wall glazed envelope with solid separated mullions, reveals and projecting lower bay'},'interfaces':{'entrances':entrances,'entrance_status':'Public Queens Gate access known; central-west position and dimensions are explicitly estimated'},'uncertainty':['2007 facade photograph predates 2015 library conversion; exact contemporary perforation pattern and micro-holes unresolved. The 32-panel white screen follows factual manufacturer description with simplified larger open cells; exact macro/micro perforations are omitted.','West street facade, roof gutter dimensions and stair-flight arrangement are incompletely observed. Their simple envelope/frame geometry is explicitly lower confidence, not equivalent to a fully surveyed facade.','Flat inherited ground is retained; lidar relative heights are not a registered surveyed threshold datum. Current entrance position is explicitly estimated, not source-verified.'],'evidence_source_ids':list(dict.fromkeys(feature.get('evidence_source_ids',[])+SOURCES))}
