"""Finite campus-frame threshold supports, unioned without invented bridging.
Pure-math plan(); build(ctx, reports) uses supplied BuildingContext.
Returns created object names, legacy-compatible approaches, interfaces.supports,
and explicit skipped/conflicts. Call with campus-frame reports; do NOT apply M.
No IO/global mutation.
Cross-direction/cross-building coplanar overlaps use exact convex polygon subtraction.
"""
import math
EPS=1e-7

def _overlap(a,b):
 # Strict positive-area SAT overlap of two oriented rectangles.
 for axis in (a['t'],a['n'],b['t'],b['n']):
  pa=[x*axis[0]+y*axis[1] for x,y in a['corners']];pb=[x*axis[0]+y*axis[1] for x,y in b['corners']]
  if min(max(pa),max(pb))-max(min(pa),min(pb))<=EPS:return False
 return True

def _area(poly):
 return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>2 else 0.

def _clip(poly,a,b,inside=True):
 def side(p):return ((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))*(1 if inside else -1)
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  u,v=side(p),side(q)
  if u>=-1e-10:out.append(p)
  if u*v<0:
   f=u/(u-v);out.append([p[0]+f*(q[0]-p[0]),p[1]+f*(q[1]-p[1])])
 clean=[]
 for p in out:
  if not clean or math.dist(p,clean[-1])>1e-9:clean.append(p)
 if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-9:clean.pop()
 return clean if _area(clean)>1e-10 else []

def _subtract(poly,clip):
 # Convex clip CCW: disjoint outside pieces plus successively restricted inside.
 remaining=poly;pieces=[]
 for a,b in zip(clip,clip[1:]+clip[:1]):
  if not remaining:break
  outside=_clip(remaining,a,b,False)
  if outside:pieces.append(outside)
  remaining=_clip(remaining,a,b,True)
 return pieces

def _intersection(poly,clip):
 for a,b in zip(clip,clip[1:]+clip[:1]):
  if not poly:break
  poly=_clip(poly,a,b)
 return poly


def plan(reports,threshold_max=.15,bottom_z=-.05):
 rectangles=[];skipped=[];groups=[]
 for oid,report in sorted(reports.items()):
  for index,e in enumerate(report.get('interfaces',{}).get('entrances',[])):
   key=f'{oid}::leaf-{index}';p=e.get('campus_threshold_xyz');normal=e.get('campus_outward_normal')
   reason=None
   if p is None or normal is None:reason='missing integrated campus interface'
   elif float(p[2])>threshold_max:reason='raised threshold; module-authored access retained'
   elif oid=='way-205276847' and float(e.get('ramp_run_m',0))>0:reason='Stevens verified continuous ramp; flat support excluded'
   if reason:skipped.append({'entry_id':key,'reason':reason});continue
   length=math.hypot(normal[0],normal[1]);width=float(e.get('clear_width_m',1.2))
   if length<EPS or width<=0 or not all(math.isfinite(float(v)) for v in [*p,*normal,width]):raise ValueError('Invalid entrance '+key)
   n=(normal[0]/length,normal[1]/length);t=(-n[1],n[0]);z=float(p[2])-.006;d=p[0]*n[0]+p[1]*n[1];u=p[0]*t[0]+p[1]*t[1];half=width/2+.12
   rect={'entry_id':key,'building_id':oid,'threshold':list(p),'clear_width_m':width,'t':t,'n':n,'z':z,'plane':d,'u0':u-half,'u1':u+half,'v0':d-.12,'v1':d+.9}
   rect['corners']=[(t[0]*a+n[0]*b,t[1]*a+n[1]*b) for a,b in [(rect['u0'],rect['v0']),(rect['u1'],rect['v0']),(rect['u1'],rect['v1']),(rect['u0'],rect['v1'])]]
   # No angular rounding, height snapping or threshold-plane snapping.
   group=next((g for g in groups if g['building_id']==oid and abs(g['z']-z)<EPS and math.dist(g['n'],n)<EPS),None)
   if group is None:group={'building_id':oid,'z':z,'plane':d,'n':n,'t':t,'rectangles':[],'index':len(groups)};groups.append(group)
   rect['group']=group['index'];group['rectangles'].append(rect);rectangles.append(rect)
 # Avoid duplicate coplanar faces across incompatible groups too. Do not convex-hull corners.
 conflicts=[];deferred=set()
 for i,a in enumerate(rectangles):
  for b in rectangles[i+1:]:
   if a['group']!=b['group'] and abs(a['z']-b['z'])<EPS and _overlap(a,b):
    conflicts.append({'entry_ids':[a['entry_id'],b['entry_id']],'reason':'coplanar overlapping groups differ in building or direction; requires cross-group exact union'});deferred.update([a['group'],b['group']])
 surfaces=[]
 for g in groups:
  if g['index'] in deferred:continue
  rs=g['rectangles'];us=sorted(set([r[k] for r in rs for k in ['u0','u1']]));vs=sorted(set([r[k] for r in rs for k in ['v0','v1']]))
  cells=set()
  for i,(a,b) in enumerate(zip(us,us[1:])):
   for j,(c,d) in enumerate(zip(vs,vs[1:])):
    if b-a>EPS and d-c>EPS and any(r['u0']-EPS<(a+b)/2<r['u1']+EPS and r['v0']-EPS<(c+d)/2<r['v1']+EPS for r in rs):cells.add((i,j))
  # Connected occupied cells form independent finite patches; distant doors never bridge.
  remain=set(cells);components=[]
  while remain:
   stack=[min(remain)];component=set();remain.remove(stack[0])
   while stack:
    i,j=stack.pop();component.add((i,j))
    for q in [(i-1,j),(i+1,j),(i,j-1),(i,j+1)]:
     if q in remain:remain.remove(q);stack.append(q)
   components.append(component)
  t,n=g['t'],g['n']
  def xy(a,b):return [t[0]*a+n[0]*b,t[1]*a+n[1]*b]
  for ci,component in enumerate(components):
   top=[];edges=[];area=0
   for i,j in sorted(component):
    a,b=us[i],us[i+1];c,d=vs[j],vs[j+1];q=[xy(a,c),xy(b,c),xy(b,d),xy(a,d)];top.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]]);area+=(b-a)*(d-c)
    for neighbour,k in [((i,j-1),0),((i+1,j),1),((i,j+1),2),((i-1,j),3)]:
     if neighbour not in cells:edges.append([q[k],q[(k+1)%4]])
   member_ids=[r['entry_id'] for r in rs if any(min(us[i+1],r['u1'])-max(us[i],r['u0'])>EPS and min(vs[j+1],r['v1'])-max(vs[j],r['v0'])>EPS for i,j in component)]
   surfaces.append({'id':f"entry-support::{g['building_id']}::{g['index']}::{ci}",'building_id':g['building_id'],'entry_ids':member_ids,'top_z':g['z'],'bottom_z':min(bottom_z,g['z']-.03),'top_triangles_xy':top,'outer_boundary_edges_xy':edges,'area_m2':area,'ground_estimated':True})
 # Resolve incompatible coplanar groups by exact convex half-plane subtraction.
 # Connected conflict components are processed separately, preserving distant entries.
 pending=set(deferred);components=[]
 while pending:
  component={min(pending)};pending-=component
  changed=True
  while changed:
   changed=False
   for a in rectangles:
    if a['group'] not in component:continue
    for b in rectangles:
     if b['group'] in pending and abs(a['z']-b['z'])<EPS and _overlap(a,b):component.add(b['group']);pending.remove(b['group']);changed=True
  components.append(component)
 for ci,component in enumerate(components):
  rs=[r for r in rectangles if r['group'] in component];polys=[list(reversed(r['corners'])) for r in rs];pieces=[]
  for i,poly in enumerate(polys):
   chunks=[poly]
   for earlier in polys[:i]:chunks=[q for chunk in chunks for q in _subtract(chunk,earlier)]
   pieces.extend(chunks)
  tris=[]
  for poly in pieces:
   for i in range(1,len(poly)-1):
    tri=[poly[0],poly[i],poly[i+1]]
    if _area(tri)>1e-10:tris.append(list(reversed(tri))) # stored CW like regular surfaces
  edges=[]
  for poly in polys:
   for a,b in zip(poly,poly[1:]+poly[:1]):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);cuts=[0.,1.]
    for other in polys:
     for c,d in zip(other,other[1:]+other[:1]):
      ex,ey=d[0]-c[0],d[1]-c[1];den=dx*ey-dy*ex
      if abs(den)>1e-12:
       u=((c[0]-a[0])*ey-(c[1]-a[1])*ex)/den;v=((c[0]-a[0])*dy-(c[1]-a[1])*dx)/den
       if -EPS<=u<=1+EPS and -EPS<=v<=1+EPS:cuts.append(max(0,min(1,u)))
      elif abs((c[0]-a[0])*dy-(c[1]-a[1])*dx)<1e-8:
       for p in (c,d):
        u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
        if 0<u<1:cuts.append(u)
    cuts=sorted(set(cuts))
    for u,v in zip(cuts,cuts[1:]):
     if (v-u)*length<EPS:continue
     mid=[a[0]+dx*(u+v)/2+dy/length*1e-6,a[1]+dy*(u+v)/2-dx/length*1e-6]
     def contains(p,other):return all((d[0]-c[0])*(p[1]-c[1])-(d[1]-c[1])*(p[0]-c[0])>=-1e-10 for c,d in zip(other,other[1:]+other[:1]))
     if not any(contains(mid,other) for other in polys):edges.append([[a[0]+dx*v,a[1]+dy*v],[a[0]+dx*u,a[1]+dy*u]])
  coverage=[]
  for r,poly in zip(rs,polys):
   expected=_area(poly);covered=sum(_area(_intersection(chunk,poly)) for chunk in pieces)
   coverage.append({'entry_id':r['entry_id'],'building_id':r['building_id'],'input_area_m2':expected,'covered_area_m2':covered,'coverage_error_m2':abs(expected-covered)})
  ids=sorted({r['building_id'] for r in rs});z=rs[0]['z']
  surfaces.append({'id':f'entry-support::shared-coplanar::{ci}','building_id':ids[0] if len(ids)==1 else None,'building_ids':ids,'entry_ids':[r['entry_id'] for r in rs],'top_z':z,'bottom_z':min(bottom_z,z-.03),'top_triangles_xy':tris,'outer_boundary_edges_xy':edges,'area_m2':sum(_area(t) for t in tris),'leaf_coverage':coverage,'ownership':'shared union geometry; per-leaf original footprint coverage retained','ground_estimated':True})
 for conflict in conflicts:conflict['resolution']='exact polygon subtraction union; no leaf deferred'
 # Union collinear vertical skirt rectangles too, including stacked heights.
 skirt_groups=[]
 for surface in surfaces:
  for aa,bb in surface['outer_boundary_edges_xy']:
   length=math.dist(aa,bb);axis=((bb[0]-aa[0])/length,(bb[1]-aa[1])/length)
   if axis[0]<-EPS or abs(axis[0])<EPS and axis[1]<0:axis=(-axis[0],-axis[1])
   normal=(-axis[1],axis[0]);offset=aa[0]*normal[0]+aa[1]*normal[1]
   group=next((q for q in skirt_groups if math.dist(q['axis'],axis)<EPS and abs(q['offset']-offset)<EPS),None)
   if group is None:group={'axis':axis,'normal':normal,'offset':offset,'rects':[]};skirt_groups.append(group)
   av=aa[0]*axis[0]+aa[1]*axis[1];bv=bb[0]*axis[0]+bb[1]*axis[1]
   group['rects'].append((min(av,bv),max(av,bv),surface['bottom_z'],surface['top_z']))
 skirts=[]
 for g in skirt_groups:
  xx=sorted({v for r in g['rects'] for v in r[:2]});zz=sorted({v for r in g['rects'] for v in r[2:]})
  def point(u,z):return [g['axis'][0]*u+g['normal'][0]*g['offset'],g['axis'][1]*u+g['normal'][1]*g['offset'],z]
  for a,b in zip(xx,xx[1:]):
   for c,d in zip(zz,zz[1:]):
    if b-a>EPS and d-c>EPS and any(r[0]-EPS<(a+b)/2<r[1]+EPS and r[2]-EPS<(c+d)/2<r[3]+EPS for r in g['rects']):skirts.append([point(a,c),point(b,c),point(b,d),point(a,d)])
 return {'coordinate_frame':'campus affine already applied; do not apply M again','surfaces':surfaces,'skirt_quads_xyz':skirts,'input_rectangles':rectangles,'skipped':skipped,'deferred_group_indices':[],'resolved_cross_group_indices':sorted(deferred),'conflicts':conflicts,'accepted_input_area_sum_m2':sum((r['u1']-r['u0'])*(r['v1']-r['v0']) for r in rectangles),'output_union_area_m2':sum(s['area_m2'] for s in surfaces),'note':'Finite estimated support tops and exterior skirts only; terrain/door clearance remains coordinator check. Different heights intentionally retained separately.'}

def build(ctx,reports,threshold_max=.15,bottom_z=-.05):
 result=plan(reports,threshold_max,bottom_z);mat=ctx.material('Extension entrance paving union',(.50,.48,.43),.88);created=[]
 for surface in result['surfaces']:
  m=ctx.mesh(surface['id']);z=surface['top_z'];bottom=surface['bottom_z']
  for tri in surface['top_triangles_xy']:
   # Local (t,n) frame has determinant -1; reverse for upward normal.
   m.face([(x,y,z) for x,y in reversed(tri)],mat)
  ob=m.done();ob['research_object_id']=surface['id'];ob['semantic_type']='entry_support';ob['building_id']=surface['building_id'] or 'shared-entry-support';ob['support_building_ids']=';'.join(surface.get('building_ids',[surface['building_id']]));ob['support_entry_ids']=';'.join(surface['entry_ids']);ob['ground_status']='finite estimated surface; not surveyed';created.append(ob.name)
 if result['skirt_quads_xyz']:
  m=ctx.mesh('entry-support::union-exterior-skirts')
  for quad in result['skirt_quads_xyz']:m.face(quad,mat)
  ob=m.done();ob['research_object_id']='extension::entry-support-union-skirts';ob['semantic_type']='entry_support';created.append(ob.name)
 result['approaches']=[{'building_id':r['building_id'],'threshold':r['threshold'],'width':r['clear_width_m'],'estimated':True,'support_ids':[s['id'] for s in result['surfaces'] if r['entry_id'] in s['entry_ids']]} for r in result['input_rectangles'] if r['group'] not in result['deferred_group_indices']]
 result['created']=created;result['interfaces']={'supports':[{'research_object_id':s['id'],'building_id':s['building_id'],'building_ids':s.get('building_ids',[s['building_id']]),'entry_ids':s['entry_ids'],'leaf_coverage':s.get('leaf_coverage',[]),'top_z':s['top_z'],'bottom_z':s['bottom_z'],'area_m2':s['area_m2']} for s in result['surfaces']]}
 return result
