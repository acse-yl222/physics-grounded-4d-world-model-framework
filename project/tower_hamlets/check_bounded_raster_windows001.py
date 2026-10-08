import json,numpy as np,rasterio
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds,Window
from rasterio.transform import from_origin
from shapely.geometry import Polygon
from shapely.ops import transform,unary_union
from pyproj import Transformer
from pathlib import Path
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';g=json.loads((R/'geometry.json').read_text());tr=Transformer.from_crs(g['crs'],27700,always_xy=True);rows=[]
cases=[('999ceaf7',80,'audit_credit999001.py'),('3a202b7c',80,'audit_credit3a001.py'),('207561e0',80,'audit_207561_identity.py / prepare_one_bank001.py / audit_one_bank_low_returns002.py'),('4cf43bea',5,'analyze_western_curve.py'),('c3bef968',6,'analyze_five_canada.py'),('33773280',6,'analyze_twenty_cabot.py / prepare_twenty_cabot_spatial001.py /002.py'),('3c1883b4',8,'audit_state_street001.py / prepare_state_street001.py'),('c9f4e448',35,'analyze_crossrail_lidar.py'),('6019910a',20,'analyze_westferry_lidar.py boundless=True')]
with rasterio.open(R/'references/ea_dsm_1m.tif') as ds:
 full=Window(0,0,ds.width,ds.height)
 for prefix,buffer,script in cases:
  fs=[f for f in g['buildings'] if prefix in f['id'] or prefix in str(f.get('parent_id',''))];p=unary_union([Polygon(t['outer'],t.get('holes',[])) for f in fs for t in f['geometry']]);w=from_bounds(*transform(tr.transform,p.buffer(buffer)).bounds,ds.transform).round_offsets().round_lengths();clipped=w.intersection(full);offset=[clipped.col_off-w.col_off,clipped.row_off-w.row_off];rows.append({'target':prefix,'scripts':script,'buffer_m':buffer,'requested_window':list(w.flatten()),'clipped_window':list(clipped.flatten()),'array_origin_offset_pixels_if_unclipped_coordinates_used':offset,'affected':any(offset) and 'boundless=True' not in script,'dimension_clipping':w!=clipped})
# Synthetic encoded pixel values prove clipped coordinates, even for outside upper-left request.
with MemoryFile() as memory:
 with memory.open(driver='GTiff',width=5,height=4,count=1,dtype='float32',crs='EPSG:27700',transform=from_origin(100,200,1,1)) as ds:
  data=np.arange(20,dtype=np.float32).reshape(4,5);ds.write(data,1);requested=Window(-2,-1,6,4);clipped=requested.intersection(Window(0,0,ds.width,ds.height));actual=ds.read(1,window=clipped);assert actual.shape==(3,4);assert actual[0,0]==0;xy=rasterio.transform.xy(ds.window_transform(clipped),0,0);assert xy==(100.5,199.5);wrong=rasterio.transform.xy(ds.window_transform(requested),0,0);assert wrong==(98.5,200.5);synthetic={'passed':True,'correct_first_pixel_center':xy,'wrong_unclipped_center':wrong,'expected_origin_error_m':[2,-1]}
report={'cases':rows,'synthetic_regression':synthetic,'conclusion':'Only99980m audit among these cases has an unhandled clipped origin. Model-generating crops forWesternCurve/OneBank/FiveCanada/TwentyCabot/StateStreet/Crossrail do not clip. 7Westferry20m crop clips but script usesboundless=True, preserving requested pixel coordinates.'};(R/'references/bounded_raster_window_audit001.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
