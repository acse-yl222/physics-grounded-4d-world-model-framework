"""Reproject licensed measured EA terrain to the exact4m ENU scene grid.

No extrapolated terrain: unknown/nodata cells remain explicitly invalid.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import rasterio
from pyproj import CRS,Transformer

def main(out):
 out.mkdir(parents=True,exist_ok=False);n=1000;x=-2000+(np.arange(n)+.5)*4;xx,yy=np.meshgrid(x,x);enu=CRS.from_proj4('+proj=aeqd +lat_0=51.5053 +lon_0=-0.0188 +datum=WGS84 +units=m');tr=Transformer.from_crs(enu,'EPSG:27700',always_xy=True);east,north=tr.transform(xx,yy);terrain=np.full((n,n),np.nan,np.float32);sources=[]
 for p in sorted(Path('project/tower_hamlets/input/canary_wharf_20261007/references').glob('*dtm*.tif')):
  with rasterio.open(p)as ds:
   col=((east-ds.transform.c)/ds.transform.a).astype(int);row=((north-ds.transform.f)/ds.transform.e).astype(int);inside=(east>=ds.bounds.left)&(east<ds.bounds.right)&(north>=ds.bounds.bottom)&(north<ds.bounds.top);a=ds.read(1,masked=True);rr=row.clip(0,ds.height-1);cc=col.clip(0,ds.width-1);valid=inside&~np.ma.getmaskarray(a)[rr,cc];terrain[valid]=a.data[rr[valid],cc[valid]]
  sources.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 valid=np.isfinite(terrain);np.save(out/'terrain_odn_m.npy',terrain);np.save(out/'terrain_valid.npy',valid)
 meta={'shape_yx':[1000,1000],'origin_xy_m':[-2000,-2000],'cell_m':4,'axis':'row north/column east','terrain_datum':'EA DTM OrdnanceDatumNewlyn; usedunchangedforhydraulicgradients','display_datum':'Localflatgeometryz0 unsurveyed; depthoverlaydoesnotassertterrain/buildingverticalregistration','resampling':'nearest original1m DTM at4mcellcentres; no extrapolation','valid_cells':int(valid.sum()),'source_files':sources};(out/'terrain_metadata.json').write_text(json.dumps(meta,indent=2));print(meta['valid_cells'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
