"""003 bounded recessed southwest facade; photographed hierarchy, estimated cadence."""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';source=R/'exports/westferry-house-massing-002/westferry_house_roof_study_002.json';r=json.loads(source.read_text());g=json.loads((R/'geometry.json').read_text());f=next(b for b in g['buildings'] if b['id']==r['building_id']);ring=np.array(f['geometry'][0]['outer']);body=trimesh.Trimesh(r['vertices'],r['faces'],process=False);cutters=[];parts={'glazing':[],'window_frames':[],'ground_frames':[],'stone_sills':[],'attic_louvers':[]};edges=[];windows=[]
def box(a,u,n,s0,s1,d0,d1,z0,z1):
 T=np.eye(4);T[:2,0]=u;T[2,0]=0;T[:2,1]=n;T[2,1]=0;T[:3,2]=[0,0,1];T[:3,3]=[*list(a+u*((s0+s1)/2)+n*((d0+d1)/2)),(z0+z1)/2];return trimesh.creation.box([s1-s0,d1-d0,z1-z0],transform=T)
for ei,count in [(5,4),(6,4),(9,16)]:
 a=ring[ei];b=ring[(ei+1)%len(ring)];u=b-a;length=np.linalg.norm(u);u/=length;n=np.array([-u[1],u[0]]);margin=.65;cadence=(length-2*margin)/count;edges.append({'edge_index':ei,'endpoints_enu_m':[a.tolist(),b.tolist()],'bay_count':count,'cadence_m':float(cadence),'window_width_m':float(min(1.7,cadence-.65)),'inward_normal':n.tolist(),'source':'pexels_ollie_11491155, southwest-edge owner projection','status':'Photo-supported feature hierarchy, all counts/depths estimated'})
 for j in range(count):
  mid=margin+(j+.5)*cadence;ww=min(1.7,cadence-.65)
  for row in range(7):
   bottom=16.3+row*3.8;top=bottom+2.72;lo=mid-ww/2;hi=mid+ww/2;cutters.append(box(a,u,n,lo,hi,-.025,.64,bottom,top));parts['glazing'].append(box(a,u,n,lo+.065,hi-.065,.57,.605,bottom+.065,top-.065))
   # Real recessed frame, central mullion, low transom, sill. No photo texture.
   frame=.065
   for s0,s1,z0,z1 in [(lo,lo+frame,bottom,top),(hi-frame,hi,bottom,top),(lo,hi,bottom,bottom+frame),(lo,hi,top-frame,top),(mid-.025,mid+.025,bottom+frame,top-frame),(lo+frame,hi-frame,bottom+.76,bottom+.81)]:parts['window_frames'].append(box(a,u,n,s0,s1,.42,.53,z0,z1))
   parts['stone_sills'].append(box(a,u,n,lo-.09,hi+.09,.03,.38,bottom+.015,bottom+.105));windows.append({'edge':ei,'bay':j,'row':row,'s_interval':[float(lo),float(hi)],'z_interval':[bottom,top],'glazing_inset_m':.57})
 # Ground bay hierarchy is wider than upper window bays in the inspectedphoto.
 ground_count={5:2,6:2,9:6}[ei];ground_cadence=(length-2*margin)/ground_count
 for j in range(ground_count):
  mid=margin+(j+.5)*ground_cadence;lo=mid-(ground_cadence-1.15)/2;hi=mid+(ground_cadence-1.15)/2
  cutters.append(box(a,u,n,lo,hi,-.025,2.25,7.0,15.45));parts['glazing'].append(box(a,u,n,lo+.075,hi-.075,1.95,1.995,7.12,15.28))
  for s0,s1,z0,z1 in [(lo,lo+.1,7.05,15.4),(hi-.1,hi,7.05,15.4),(lo,hi,7.05,7.15),(lo,hi,15.25,15.4),(lo,hi,10.9,11.0)]+[(q-.035,q+.035,7.1,15.3) for q in np.linspace(lo,hi,5)[1:-1]]:parts['ground_frames'].append(box(a,u,n,s0,s1,1.78,1.91,z0,z1))
 # Incised horizontal profile grooves leave stronger stone bands between window rows.
 for z in [15.55,15.82,27.55,27.77,34.6,34.8,42.5,43.15,44.18]:cutters.append(box(a,u,n,.1,length-.1,-.025,.10,z,z+.075))
# Attic openings only on long west/south faces of002upperterrace, no roof edits.
from shapely.geometry import Polygon
attic_edges=[];attic_windows=[]
for partition in r['partitions']:
 if partition['class']!=1:continue
 poly=Polygon(partition['outer'],partition.get('holes',[]));rr=np.array(poly.exterior.coords)
 for edge_index,(a,b) in enumerate(zip(rr[:-1],rr[1:])):
  u=b-a;length=np.linalg.norm(u);u/=length;n=np.array([-u[1],u[0]])*(1 if poly.exterior.is_ccw else -1);out=-n
  if length<15 or not(out[0]<-.85 or out[1]<-.85):continue
  count=max(1,round(length/3));margin=.65;step=(length-2*margin)/count;attic_edges.append({'upper_terrace_edge_index':edge_index,'endpoints':[a.tolist(),b.tolist()],'estimated_bays':count})
  for j in range(count):
   mid=margin+(j+.5)*step;ww=min(1.5,step-.7);lo,hi=mid-ww/2,mid+ww/2;bottom=45.35;top=49.25;cutters.append(box(a,u,n,lo,hi,-.025,.48,bottom,top));parts['glazing'].append(box(a,u,n,lo+.06,hi-.06,.40,.435,bottom+.06,top-.06))
   for s0,s1,z0,z1 in [(lo,lo+.065,bottom,top),(hi-.065,hi,bottom,top),(lo,hi,bottom,bottom+.065),(lo,hi,top-.065,top)]:parts['window_frames'].append(box(a,u,n,s0,s1,.28,.38,z0,z1))
   for z in [48.3,48.55,48.8]:parts['attic_louvers'].append(box(a,u,n,lo+.065,hi-.065,.12,.30,z,z+.065))
   attic_windows.append({'edge':edge_index,'bay':j,'z':[bottom,top]})
newbody=trimesh.boolean.difference([body,*cutters],engine='manifold');assert newbody.is_watertight and newbody.is_winding_consistent
# Body keeps002 roof planes; verify horizontal top faces at those two elevations only.
rooflevels=np.array(r['levels_scene_m']);centers=newbody.triangles_center;roofmask=(newbody.face_normals[:,2]>.999)&(abs(centers[:,2,None]-rooflevels).min(axis=1)<1e-4);roofarea=float(newbody.area_faces[roofmask].sum());assert abs(roofarea-r['checks']['source_footprint_area_m2'])<.003
objects=[{'name':'WestferryHouse_recessed_stone_body','kind':'body','vertices':newbody.vertices.tolist(),'faces':newbody.faces.tolist(),'materials':[1 if isroof else 0 for isroof in roofmask]}]
for kind,meshes in parts.items():
 m=trimesh.util.concatenate(meshes);objects.append({'name':'WestferryHouse_'+kind,'kind':kind,'vertices':m.vertices.tolist(),'faces':m.faces.tolist()})
rep={'building_id':r['building_id'],'revision':'003 bounded southwest facade study','objects':objects,'roof_levels_scene_m':r['levels_scene_m'],'source_002_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_photo_id':'pexels_ollie_11491155','source_photo_hash':'1b198fe233b77314e38e956d4e50d9901c439e6e62f2928498029b5249980e78','camera_projection_report':'references/westferry_house_photo_projection.json','visible_edges':edges,'untouched_shared_edge_index':4,'upper_window_count':len(windows),'upper_windows':windows,'ground_bay_count':10,'attic_window_count':len(attic_windows),'attic_edges':attic_edges,'public_level_scene_m':7,'ground_bay_top_scene_m':15.45,'ground_datum_basis':'Estimated appearance only; upper/lower Circus support and foundations unresolved','scope':'Actual3D recessedwindows,frames,mullions,sills anddeepgroundbays onexactowneredges5,6,9only. Cadence3mclass,7upperrows,levels anddepthsestimatedfromphoto hierarchy. No sourcephoto textures. Otherwalls plain;west/southatticbays estimated;002roofplanes/notch preserved. Groundrecesses are notverified entrances. No continuouscurvedfrontage copied across7Westferryowner seam.','checks':{'body_finite':bool(np.isfinite(newbody.vertices).all()),'body_watertight':bool(newbody.is_watertight),'body_consistent_winding':bool(newbody.is_winding_consistent),'roof_projected_area_m2':roofarea,'source_footprint_area_m2':r['checks']['source_footprint_area_m2'],'roof_area_difference_m2':roofarea-r['checks']['source_footprint_area_m2'],'body_volume_m3':float(newbody.volume),'body_triangle_count':len(newbody.faces),'cutout_count':len(cutters)},'source_hashes':{str(source.relative_to(R)):hashlib.sha256(source.read_bytes()).hexdigest(),'geometry_owner_record':hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest()},'uncertainty':['Approximate landmark fit is not calibrated photogrammetry; nearby corner sensitivity is reported separately.','7rows and4/4/16baycounts are architectural estimates, not individually measuredwindowcounts.','Photo upperattic supports hierarchy but not a reliableassignment ofroofedgeopenings; atticwindows onvisiblewest/southupperfaces estimated; hiddenatticfaces plain.','Smallreturnedges7,8 andshared4 remainplain. Hiddennorth/eastfacesunverified.','No foundation,steps,publicground adjustment orautomaticglowingwindowlights.']}
(R/'references/westferry_house_facade_study_003.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(rep['checks'],indent=2));print('upperwindows',len(windows),'edges',edges)
