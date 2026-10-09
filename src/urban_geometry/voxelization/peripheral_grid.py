"""Raster coarse source extrusions + aligned validated core volume without replacing it."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box
from shapely import contains_xy

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--outer',type=Path,required=True);ap.add_argument('--core',type=Path);ap.add_argument('--spacing',type=float,default=8);ap.add_argument('--origin',nargs=3,type=float,default=[-2000,-2000,0]);ap.add_argument('--shape',nargs=3,type=int,default=[64,500,500]);ap.add_argument('--project',type=Path,help='Canonical project metadata for geographic origin/datum');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);d=json.load(open(a.outer));cell=a.spacing;origin=np.array(a.origin);nz,ny,nx=a.shape;solid=np.zeros((nz,ny,nx),bool);height=np.zeros((ny,nx),np.float32);floor=np.full((ny,nx),np.inf,np.float32);xs=origin[0]+(np.arange(nx)+.5)*cell;ys=origin[1]+(np.arange(ny)+.5)*cell;zs=origin[2]+(np.arange(nz)+.5)*cell
 for row in d['buildings']:
  for p in row['geometry']:
   poly=Polygon(p['outer'],p['holes']);x0,y0,x1,y1=poly.bounds;ix=np.where((xs>=x0)&(xs<=x1))[0];iy=np.where((ys>=y0)&(ys<=y1))[0]
   if not len(ix)or not len(iy):continue
   xx,yy=np.meshgrid(xs[ix],ys[iy]);inside=contains_xy(poly,xx,yy);yyi,xxi=np.where(inside);xxi=ix[xxi];yyi=iy[yyi];height[yyi,xxi]=np.maximum(height[yyi,xxi],row['height_m']);floor[yyi,xxi]=np.minimum(floor[yyi,xxi],row['min_height_m']);iz=np.where((zs>=row['min_height_m'])&(zs<row['height_m']))[0]
   for z in iz:solid[z,yyi,xxi]=True
 cm={'geographic_origin':{'longitude':-.0188,'latitude':51.5053,'height_m':0}}
 if a.core:
  cm=json.load(open(a.core/'metadata.json'));assert np.allclose(cm['spacing_xyz_m'],[cell]*3),'Core spacing mismatch; resampling is not permitted';cs=np.load(a.core/'solid.npy');co=np.array(cm['source_region_origin_xyz_m']);off=((co-origin)/cell).astype(int);assert np.allclose(co-origin,off*cell);z,y,x=off[2],off[1],off[0];existing=solid[z:z+cs.shape[0],y:y+cs.shape[1],x:x+cs.shape[2]].copy();solid[z:z+cs.shape[0],y:y+cs.shape[1],x:x+cs.shape[2]]|=cs;coreh=np.load(a.core/'surface_height_m.npy') if (a.core/'surface_height_m.npy').exists() else np.max(np.where(cs,co[2]+(np.arange(cs.shape[0])[:,None,None]+1)*cell,0),axis=0);height[y:y+cs.shape[1],x:x+cs.shape[2]]=np.maximum(height[y:y+cs.shape[1],x:x+cs.shape[2]],coreh)
 coverage=np.zeros((ny,nx),np.uint8);xx,yy=np.meshgrid(xs,ys);coverage[(abs(xx)<=2000)&(abs(yy)<=2000)]=1;coverage[(abs(xx)<=500)&(abs(yy)<=500)]=2
 if a.project:cm['geographic_origin']=json.load(open(a.project))['spatial']['origin']
 np.save(a.out/'solid.npy',solid);np.save(a.out/'height_m.npy',height);np.save(a.out/'building_footprint.npy',solid.any(0));near_index=int(np.argmin(abs(zs-2)));np.save(a.out/'near_ground_building_mask.npy',solid[near_index]);np.save(a.out/'source_coverage.npy',coverage)
 m={'shape_zyx':list(solid.shape),'spacing_xyz_m':[cell]*3,'origin_xyz_m':origin.tolist(),'source_region_origin_xyz_m':origin.tolist(),'axis_order':'zyx','aoi_bounds_enu':[-2000,-2000,2000,2000],'geographic_origin':cm['geographic_origin'],'occupied_cells':int(solid.sum()),'max_height_m':float(height.max()),'outer_records':len(d['buildings']),'core_mask_sha256':hashlib.sha256((a.core/'solid.npy').read_bytes()).hexdigest() if a.core else None,'outer_geometry_sha256':hashlib.sha256(a.outer.read_bytes()).hexdigest(),'core_occupied_preserved':bool(np.all(solid[z:z+cs.shape[0],y:y+cs.shape[1],x:x+cs.shape[2]][cs])) if a.core else None,'source_coverage_codes':{'0':'Outside source AOI; unknown context, not evidence of empty surroundings','1':'Overture queried AOI context, not completeness guarantee','2':'Protected detailed core'},'near_ground_mask_center_height_m':float(zs[near_index]),'height_semantics':'Outer source/assumed extrusion heights; core direct native triangle top intersections where available, otherwise explicit occupied voxel upperface' ,'limits':['Planar unsurveyed ground; no DTM.','Cell centres miss small buildings; sourcecoverage means supplieddataset coverage not realworld completeness.','Core3Dvolume retained; thermal heightcolumns are an explicit downstream approximation.']};(a.out/'metadata.json').write_text(json.dumps(m,indent=2));print(json.dumps(m))
if __name__=='__main__':main()
