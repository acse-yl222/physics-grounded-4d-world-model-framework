"""Extract bounded OSM ways and reference-complete relations from a licensed PBF."""
from pathlib import Path
import argparse,json,hashlib,datetime
import osmium
from pyproj import CRS,Transformer

def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--bbox',nargs=4,type=float);p.add_argument('--half-width',type=float,default=2400);a=p.parse_args()
 crs=CRS.from_proj4('+proj=aeqd +lat_0=51.5053 +lon_0=-0.0188 +datum=WGS84 +units=m');inv=Transformer.from_crs(crs,4326,always_xy=True);corners=[inv.transform(x,y)for x in [-a.half_width,a.half_width]for y in [-a.half_width,a.half_width]];west=min(x for x,y in corners);east=max(x for x,y in corners);south=min(y for x,y in corners);north=max(y for x,y in corners)
 if a.bbox:west,south,east,north=a.bbox
 a.output.parent.mkdir(parents=True,exist_ok=True)
 selected=set();counts={'node':0,'way':0,'relation':0}
 with osmium.BackReferenceWriter(a.output,a.source,remove_tags=False,relation_depth=3)as writer:
  for o in osmium.FileProcessor(a.source).with_locations():
   if o.is_node():
    if west<=o.lon<=east and south<=o.lat<=north:writer.add(o);counts['node']+=1
   elif o.is_way():
    points=[(n.lon,n.lat)for n in o.nodes if n.location.valid()]
    if points and min(x for x,y in points)<=east and max(x for x,y in points)>=west and min(y for x,y in points)<=north and max(y for x,y in points)>=south:writer.add(o);selected.add(o.id);counts['way']+=1
   elif any(m.type=='w'and m.ref in selected for m in o.members):writer.add(o);counts['relation']+=1
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 a.output.with_suffix('.provenance.json').write_text(json.dumps({'url':'https://download.geofabrik.de/europe/united-kingdom/england/greater-london-261007.osm.pbf','source_sha256':sha(a.source),'sha256':sha(a.output),'bbox_wgs84':[west,south,east,north],'license':'OpenStreetMap contributors, ODbL1.0; Geofabrik public extract','counts_selected':counts,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Bounding-intersecting ways plus local nodes and containing relations, reference-complete extraction; full relations may extend outside target; traffic clipped separately','projection':'Explicit WGS84 bounding box; no local-frame claim' if a.bbox else crs.to_string(),'api_policy':'https://operations.osmfoundation.org/policies/api/; editing API not used'},indent=2));print(counts)
if __name__=='__main__':main()
