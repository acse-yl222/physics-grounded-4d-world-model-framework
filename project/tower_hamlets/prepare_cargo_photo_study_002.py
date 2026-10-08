from pathlib import Path
import json,numpy as np,trimesh
from shapely.geometry import Polygon
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());bid='overture-building-2e7e0c13-18cf-47a2-bca4-3dfa829260a4';f=next(f for f in g['buildings'] if f['id']==bid);ring=np.array(f['geometry'][0]['outer']);p=Polygon(ring);body=trimesh.creation.extrude_polygon(p,79.8,engine='earcut');baseline=body.copy();a=ring[13];b=ring[0];L=np.linalg.norm(b-a);t=(b-a)/L;n=np.array([-t[1],t[0]]);meshes={'glass':[],'frame':[],'spandrel':[]}
def box(s0,s1,d0,d1,z0,z1):
 T=np.eye(4);T[:2,0]=t;T[:2,1]=n;T[:3,3]=[*list(a+t*(s0+s1)/2+n*(d0+d1)/2),(z0+z1)/2];return trimesh.creation.box([s1-s0,d1-d0,z1-z0],transform=T)
margin=.4;lo=18.;hi=79.4;cut=box(margin,L-margin,-.02,.32,lo,hi);body=trimesh.boolean.difference([body,cut],engine='manifold');assert body.is_watertight
nb=round((L-2*margin)/2.1);nr=round((hi-lo)/3.6);w=(L-2*margin)/nb;h=(hi-lo)/nr
for j in range(nr):
 z=lo+j*h
 for k in range(nb):
  x=margin+k*w;meshes['glass'].append(box(x+.035,x+w-.035,.23,.26,z+.66,z+h-.035));meshes['spandrel'].append(box(x+.035,x+w-.035,.20,.23,z+.035,z+.64))
 for zz in [z,z+.64]:meshes['frame'].append(box(margin,L-margin,.05,.135,zz,zz+.035))
for k in range(nb+1):
 x=margin+k*w;meshes['frame'].append(box(max(margin,x-.0175),min(L-margin,x+.0175),.05,.14,lo,hi))
meshes['frame'].append(box(margin,L-margin,.05,.14,hi-.035,hi));objs=[]
def obj(name,kind,m):objs.append({'name':name,'kind':kind,'building_id':bid,'vertices':m.vertices.tolist(),'roof_faces':m.faces.tolist(),'wall_faces':[],'bottom_faces':[]})
obj('Cargo_mapped_body_partial_north_recess','stone',body)
for kind,ms in meshes.items():obj('Cargo_northeast_'+kind,kind,trimesh.util.concatenate(ms))
r={'objects':objs,'baseline_mesh':{'vertices':baseline.vertices.tolist(),'faces':baseline.faces.tolist()},'building_id':bid,'scope':'Cargo25NorthColonnade partial northeastedge13 facadestudy. Tomphoto rightedge broadlightglasswall identified comparatively; centraltrellis belongs5Canada andnotused. Mappedwholefootprint79.8m preserved, no inventedroofcanopy/terrace/curvedcorner. Onlyedge13z18..79.4 has true0.32mrecess withglazing,smallspandrels,slimjoints. Pixelcorrespondence andcadenceestimated; imagecrop hidespartofwall. Lower18m/otherfacesplainunknown. Noidentifiedentrance. Historicalcaptureunknown,2022refurbishmenttext not fused into exactappearance.','visible_source_edge_index':13,'visible_edge_xy':[a.tolist(),b.tolist()],'estimated_cadence':{'bays':nb,'facade_rows':nr,'bay_width_m':w,'row_height_m':h,'not_actual_floor_count':True},'source_photo_id':'pexels_tom_10391373','identity_report':'references/cargo_photo_identity_002.json','rejected_prior':'cargo-photo-study-001 trellis attribution withdrawn; preservedhistoricalcandidate','checks':{'body_watertight':bool(body.is_watertight),'body_winding':bool(body.is_winding_consistent),'source_footprint_area_m2':p.area,'height_m':79.8},'limitations':['Approximate4landmarkcamera residual15.9px; uncertainroofcenters,principalpoint/crop andOCS210mcorner correspondence.','Roundedcorner visibleinphoto cannot reliablytrace tomappedvertex; no planreshape.','Onepartialwallimprovementonly, not allfacades verified.','Materialcolor/lightglassratio estimated fromovercastphoto; no exactcurtainwallproductassignment.']};(R/'references/cargo_photo_study_002.json').write_text(json.dumps(r,indent=2));print('objects',len(objs),'bays',nb,'rows',nr)
