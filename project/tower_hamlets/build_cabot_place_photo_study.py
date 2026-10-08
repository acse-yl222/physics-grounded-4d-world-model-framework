from pathlib import Path
import bpy,bmesh,json,math,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';O=R/'exports/cabot-place-photo-study-001';O.mkdir(exist_ok=True);src=R/'exports/dfbe-roof-study-003/dfbe.blend';D=json.loads((R/'references/dfbe_authoring003.json').read_text());bid=D['building_id'];bpy.ops.wm.open_mainfile(filepath=str(src));bodies=[o for o in bpy.data.objects if o.type=='MESH'];ring=D['source_geometry']['geometry'][0]['outer'];area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]));bins={k:([],[]) for k in ['cut','glass','frame','stone','bronze','red']};windows=[]
def box(k,origin,t,n,s0,s1,d0,d1,z0,z1):
 v,f=bins[k];off=len(v)
 for z in [z0,z1]:
  for s,d in [(s0,d0),(s1,d0),(s1,d1),(s0,d1)]:v.append(list(origin+t*s+n*d+Vector((0,0,z))))
 f.extend([[off+i for i in q] for q in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]])
for i in [0,*range(14,len(ring))]:
 A=Vector((*ring[i],0));B=Vector((*ring[(i+1)%len(ring)],0));t=(B-A).normalized();L=(B-A).length;n=Vector((t.y,-t.x,0))*(1 if area>0 else -1)
 if L<.5:continue
 count=max(1,round(L/2.4));step=L/count
 for j in range(count):
  center=(j+.5)*step;w=max(.4,min(step-.25,2.15))
  for z0,z1,label in [(3.0,10.0,'glazed_lower')]:
   s0,s1=center-w/2,center+w/2;box('cut',A,t,n,s0,s1,-.30,.06,z0,z1);box('glass',A,t,n,s0+.04,s1-.04,-.255,-.235,z0+.04,z1-.04)
   for aa,bb in [(s0,s0+.055),(s1-.055,s1)]:box('frame',A,t,n,aa,bb,-.20,-.13,z0,z1)
   for lo,hi in [(z0,z0+.06),(z1-.06,z1)]:box('frame',A,t,n,s0,s1,-.20,-.13,lo,hi)
   if label=='glazed_lower':
    for z in [5.8,8.0]:box('frame',A,t,n,s0,s1,-.19,-.12,z,z+.07)
    box('frame',A,t,n,center-.026,center+.026,-.20,-.12,z0,z1)
   windows.append({'edge':i,'along_m':[s0,s1],'z_m':[z0,z1],'type':label})
 # Fine horizontal stringcourse ledges, observed layering, artistically estimated sections.
 for z in [10.5,11.3,11.9]:box('stone',A,t,n,.05,L-.05,-.01,.12,z,z+.12)
def obj(k,mat=None):
 v,f=bins[k];me=bpy.data.meshes.new('CabotPlace_'+k);me.from_pydata(v,[],f);me.update();ob=bpy.data.objects.new('CabotPlace_'+k,me);bpy.context.collection.objects.link(ob);ob['building_id']=bid;ob['kind']=k
 if mat:me.materials.append(mat)
 return ob
def mat(n,col,metal,rough):
 m=bpy.data.materials.new(n);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
stone=mat('Estimated pale limestone',(.61,.59,.53),0,.7);glass=mat('Estimated bluegrey recessed glazing',(.13,.23,.27),.12,.23);frame=mat('Estimated slender metal frames',(.38,.43,.44),.6,.32)
cut=obj('cut')
for ob in [*bodies,cut]:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free()
for ob in bodies:
 bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Actual southwest facade recesses','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut,do_unlink=True)
bronze=mat('Estimated bronze inset panels',(.32,.22,.10),.5,.4);red=mat('Estimated muted terracotta courses',(.31,.12,.095),0,.7)
for k,m in [('glass',glass),('frame',frame),('stone',stone)]:obj(k,m)
for ob in bpy.data.objects:
 if ob.type=='MESH':
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free()
scene=bpy.context.scene;scene.cycles.samples=48;scene.render.resolution_x=1200;scene.render.resolution_y=1000
T=Vector((-211,-12,14));scene.camera.location=T+Vector((-150,25,45));scene.camera.rotation_euler=(T-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=110
bpy.ops.wm.save_as_mainfile(filepath=str(O/'cabot_place.blend'),compress=False);bpy.ops.object.select_all(action='DESELECT');obs=[o for o in bpy.data.objects if o.type=='MESH']
for ob in obs:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'cabot_place.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=False)
objects=[]
for ob in obs:
 ob.data.calc_loop_triangles();objects.append({'name':ob.name,'building_id':bid,'vertices':[list(ob.matrix_world@v.co) for v in ob.data.vertices],'triangles':len(ob.data.loop_triangles)})
report={'objects':objects,'building_id':bid,'source_blend':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'Anna photo-informed westfront only: realrecessedglazing onouter12.452mstrip,z3..10; upper decorativepanelcomposition withheld because wallplane correspondence unproven. Preserveall003roofzones andeasternDLRinterface. Dimensions/cadenceestimated, steppedmassingnotphotocalibrated; noentry/logo modeled.','source_id':'pexels_anna_19572396','windows':windows,'limitations':['Photo roofalignment uncertain: existing3stepheightroofretained, facadecomposition appliedbyexposedzone notcalibratedphotoheights.','Lower0..3mentrance unresolved; no businesslogo/signage.','Onlywestfront modeled; mainupperroofwallsandotherfacadesplain.','Estimatedspacingandmaterials; notcompletebuilding.']};report['photo_observations']={'source_id': 'pexels_anna_19572396', 'observed': ['Central projecting curved lowerglazedfront with dark slenderverticalframes and horizontaltransoms.', 'Pale piers separate sideglazedbays; pale horizontalledge/coping aboveglass.', 'Large opaque upperparapet with coloreddecoration visible but mappedwallplane correspondence unresolved; withheld.'], 'artist_estimates': ['Glazingz3..10m; .30mrecess; approximate2.4mbaycadence, compressedbaysalongmappedcurve.', 'Transomsz5.8/8.0; framewidth.055–.07m; ledgesz10.5/11.3/11.9m, .12mdepth.', 'Bluegrey glazing andpale stonematerial approximate; notphoto-texture orsampled calibratedcolor.'], 'occlusion': 'Trees/fountain/awnings obscureground; no exactdoors, signsorentrance reconstructed.'};(R/'references/cabot_place_photo_study.json').write_text(json.dumps(report,indent=2))
for name,tar,off,scale in [('overview',T,(-150,25,45),105),('detail',Vector((-235,-8,13)),(-85,16,8),34),('roof',Vector((-208,-13,22)),(-60,-50,150),105)]:
 scene.camera.location=tar+Vector(off);scene.camera.rotation_euler=(tar-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('BUILT',len(objects),sum(q['triangles'] for q in objects))
