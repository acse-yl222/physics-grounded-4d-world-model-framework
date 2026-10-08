"""Compare authored footprints with paired elevation rasters; never mutate geometry.

Run with --project <region authoring directory>. Requires rasterio, shapely,
pyproj and numpy. Statistics are evidence, not automatic building heights.
"""
import argparse
import hashlib
import math
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon, mapping, box
from shapely.ops import transform


def sample(feature, transformer, origin, dsm, dtm):
    polygons=[Polygon(p['outer'],p.get('holes',[])) for p in feature['geometry']]
    shape=MultiPolygon(polygons)
    projected=transform(lambda x,y,z=None:transformer.transform(np.asarray(x)+origin[0],np.asarray(y)+origin[1]),shape)
    coverage=projected.intersection(box(*dsm.bounds)).area/projected.area
    core=projected.buffer(-1.5)
    row={'id':feature['id'],'name':feature['name'],'old_height_m':feature['height_m'],
         'old_height_basis':feature['height_basis'],'raster_footprint_coverage':coverage,
         'footprint_area_m2':projected.area,'interior_area_m2':core.area,'flags':[]}
    if coverage<.999:row['flags'].append('footprint_outside_raster')
    core=core.intersection(box(*dsm.bounds))
    if core.is_empty or core.area<9:
        row['flags'].append('insufficient_eroded_footprint');return row
    raw=from_bounds(*core.bounds,transform=dsm.transform)
    c0,r0=math.floor(raw.col_off),math.floor(raw.row_off)
    window=Window(c0,r0,math.ceil(raw.col_off+raw.width)-c0,math.ceil(raw.row_off+raw.height)-r0)
    window=window.intersection(Window(0,0,dsm.width,dsm.height))
    a=dsm.read(1,window=window,masked=True);b=dtm.read(1,window=window,masked=True)
    selected=geometry_mask([mapping(core)],out_shape=a.shape,transform=dsm.window_transform(window),invert=True)
    valid=selected & ~np.ma.getmaskarray(a) & ~np.ma.getmaskarray(b)
    count=int(valid.sum());row['interior_valid_pixels']=count
    if count<9:row['flags'].append('insufficient_valid_pixels');return row
    roof=np.asarray(a)[valid];ground=np.asarray(b)[valid];height=roof-ground
    row.update(dsm_elevation_odn_percentiles_m=np.percentile(roof,[5,50,95]).tolist(),
               dtm_elevation_odn_percentiles_m=np.percentile(ground,[5,50,95]).tolist(),
               relative_height_percentiles_m=np.percentile(height,[5,50,95]).tolist(),
               relative_height_p95_minus_current_m=float(np.percentile(height,95)-feature['height_m']))
    if np.percentile(height,95)-np.percentile(height,5)>4:row['flags'].append('variable_roof_or_contamination')
    if np.percentile(ground,95)-np.percentile(ground,5)>2:row['flags'].append('variable_terrain')
    if np.percentile(height,5)<1:row['flags'].append('low_or_missing_roof_returns')
    if feature.get('kind')=='part' or feature.get('parent_id'):row['flags'].append('multipart_vertical_ownership_review')
    if feature['source_properties'].get('facade_material')=='glass' or feature['source_properties'].get('roof_material')=='glass':row['flags'].append('glass_return_review')
    row['flags'].append('survey_vintage_vs_2026_footprint_unverified')
    return row


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True);args=parser.parse_args()
    root=args.project;geometry=json.loads((root/'geometry.json').read_text());refs=root/'references'
    with rasterio.open(refs/'ea_dsm_1m.tif') as dsm,rasterio.open(refs/'ea_dtm_1m.tif') as dtm:
        assert dsm.crs==dtm.crs and dsm.transform==dtm.transform and dsm.shape==dtm.shape
        transformer=Transformer.from_crs(geometry['crs'],dsm.crs,always_xy=True)
        rows=[sample(f,transformer,geometry['origin_projected_m'],dsm,dtm) for f in geometry['buildings'] if 'source_properties' in f]
    report={'method':'1.5 m footprint erosion; centre-selected native 1 m raster pixels; paired DSM minus DTM percentiles 5/50/95',
            'geometry_modified':False,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'geometry.json',refs/'ea_dsm_1m.tif',refs/'ea_dtm_1m.tif']},
            'vertical_reference':'DSM/DTM elevations metres ODN; differences local above modelled terrain; current scene z0 unsurveyed',
            'limitations':['2017–2018 and 2020 survey extents intersect AOI; per-pixel survey attribution unresolved','Roof percentiles are not eave or apex measurements','Trees, equipment, glass and changed buildings need individual review','Erosion reduces boundary contamination but does not prove correspondence'],
            'building_count':len(rows),'sampled_count':sum('relative_height_percentiles_m' in r for r in rows),'buildings':rows}
    output=refs/'lidar_building_height_evidence.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['building_count','sampled_count','geometry_modified']}))
    for row in rows:
        if row['name']=='Cabot Place Shopping Centre':print(json.dumps(row))

if __name__=='__main__':main()
