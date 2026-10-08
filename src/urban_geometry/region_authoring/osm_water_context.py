"""Extract source-tagged OSM water polygons/relations into exact local ENU AOI."""
import argparse,json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from pyproj import CRS,Transformer
from shapely.geometry import Polygon,LineString,box,mapping
from shapely.ops import polygonize,unary_union,transform
from shapely import contains_xy,make_valid

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--osm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);nodes={};ways={};relations=[]
 for ev,e in ET.iterparse(a.osm,events=['end']):
  if e.tag=='node':nodes[e.attrib['id']]=(float(e.attrib['lon']),float(e.attrib['lat']));e.clear()
  elif e.tag=='way':ways[e.attrib['id']]=([n.attrib['ref']for n in e.findall('nd')],{t.attrib['k']:t.attrib['v']for t in e.findall('tag')});e.clear()
  elif e.tag=='relation':relations.append((e.attrib['id'],[(m.attrib['ref'],m.attrib.get('role',''))for m in e.findall('member')if m.attrib['type']=='way'],{t.attrib['k']:t.attrib['v']for t in e.findall('tag')}));e.clear()
 def water(t):return t.get('natural')=='water'or t.get('waterway')=='riverbank'or t.get('landuse')in ['reservoir','basin']
 trans=Transformer.from_crs(4326,CRS.from_proj4('+proj=aeqd +lat_0=51.5053 +lon_0=-.0188 +datum=WGS84 +units=m'),always_xy=True).transform;domain=box(-2000,-2000,2000,2000);features=[];members=set();issues=[]
 def add(ident,g,tags):
  if not g.is_valid:g=make_valid(g)
  g=transform(trans,g).intersection(domain)
  if g.is_empty or g.area<=0:return
  features.append({'type':'Feature','id':ident,'properties':{'osm_tags':tags,'basis':'Source OSM water polygon; planar, no surveyed depth'},'geometry':mapping(g)})
 for ident,refs,tags in relations:
  if not water(tags):continue
  outer=[];inner=[]
  for ref,role in refs:
   if ref not in ways:issues.append({'relation':ident,'missing_way':ref});continue
   ns,wt=ways[ref]
   if any(n not in nodes for n in ns):issues.append({'relation':ident,'missing_nodes_way':ref});continue
   if len(ns)<2:continue
   (inner if role=='inner'else outer).append(LineString([nodes[n]for n in ns]));members.add(ref)
  if outer:
   po=unary_union(list(polygonize(unary_union(outer))));pi=unary_union(list(polygonize(unary_union(inner))))if inner else Polygon();add('osm-relation-'+ident,po.difference(pi),tags)
 for ident,(ns,tags)in ways.items():
  if ident in members or not water(tags)or len(ns)<4 or ns[0]!=ns[-1]or any(n not in nodes for n in ns):continue
  add('osm-way-'+ident,Polygon([nodes[n]for n in ns]),tags)
 (a.out/'water_enu.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'Scene local ENU AEQD; NOT geographic GeoJSON longitude/latitude','features':features},separators=(',',':')))
 from shapely.geometry import shape
 union=unary_union([shape(f['geometry'])for f in features]);xs=-2000+(np.arange(500)+.5)*8;xx,yy=np.meshgrid(xs,xs);mask=contains_xy(union,xx,yy);np.save(a.out/'water_8m.npy',mask)
 meta={'source':str(a.osm),'source_sha256':hashlib.sha256(a.osm.read_bytes()).hexdigest(),'provider':'OpenStreetMap contributors via Geofabrik Greater London261007','license':'ODbL-1.0','license_url':'https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors','features':len(features),'water_area_m2':union.area,'shape_yx':[500,500],'origin_xy_m':[-2000,-2000],'spacing_m':8,'axes':'ENU x east y north; axis order yx','water_cells':int(mask.sum()),'missing_member_issues':issues,'limits':['Source-tagged water polygons only, not guaranteed complete.','Flat water surface; no bathymetry or tidal elevation.','Raster uses centre sampling; narrow water features may be missed.']};(a.out/'metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps({k:v for k,v in meta.items()if k!='missing_member_issues'}))
if __name__=='__main__':main()
