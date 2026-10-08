"""Prepare coarse Overture context around a protected detailed core, same ENU.
Preserves entire AOI-intersecting footprints; core overlaps are excluded, not cut.
Parent residual polygons subtract mapped parts exactly as source baseline workflow.
"""
import argparse,collections,datetime,hashlib,json,struct
from pathlib import Path
import numpy as np
import mapbox_earcut
from pyproj import CRS,Transformer
from shapely.geometry import shape,box,Polygon,MultiPolygon
from shapely.ops import transform,unary_union
from shapely.geometry.polygon import orient


def polygon_parts(g):
    polys=[g]if g.geom_type=='Polygon'else list(g.geoms)if hasattr(g,'geoms')else[]
    out=[]
    for p in polys:
        if p.geom_type!='Polygon' or p.area<1e-5:continue
        p=orient(p,sign=1);rings=[np.array(x.coords[:-1],float)for x in [p.exterior,*p.interiors]];v=np.concatenate(rings);ends=np.cumsum([len(x)for x in rings],dtype=np.uint32);f=mapbox_earcut.triangulate_float64(v,ends).reshape(-1,3)
        assert abs(sum(Polygon(v[t]).area for t in f)-p.area)<max(1e-5,p.area*1e-8)
        out.append({'outer':rings[0].tolist(),'holes':[x.tolist()for x in rings[1:]],'vertices_xy':v.tolist(),'triangles':f.tolist()})
    return out


def write_glb(rows,path,color=None):
    binary=bytearray();views=[];accessors=[];meshes=[];nodes=[]
    def accessor(a,component,typ):
        while len(binary)%4:binary.append(0)
        offset=len(binary);binary.extend(a.tobytes());vi=len(views);views.append({'buffer':0,'byteOffset':offset,'byteLength':a.nbytes});idx=len(accessors);rec={'bufferView':vi,'componentType':component,'count':len(a),'type':typ}
        if typ=='VEC3':rec.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        accessors.append(rec);return idx
    tri_count=0
    for row in rows:
        vertices=[];faces=[]
        for p in row['geometry']:
            v=np.asarray(p['vertices_xy']);n=len(v);off=len(vertices);vertices.extend((float(x),row['min_height_m'],float(-y))for x,y in v);vertices.extend((float(x),row['height_m'],float(-y))for x,y in v)
            for a,b,c in p['triangles']:faces.extend([(off+c,off+b,off+a),(off+n+a,off+n+b,off+n+c)])
            start=0
            for ring in [p['outer'],*p['holes']]:
                count=len(ring)
                for j in range(count):a=off+start+j;b=off+start+(j+1)%count;faces.extend([(a,b,b+n),(a,b+n,a+n)])
                start+=count
        v=np.array(vertices,dtype='<f4');f=np.array(faces,dtype='<u4');norm=np.zeros_like(v)
        for t in f:
            normal=np.cross(v[t[1]]-v[t[0]],v[t[2]]-v[t[0]]);norm[t]+=normal
        norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12)
        pos=accessor(v,5126,'VEC3');nor=accessor(norm.astype('<f4'),5126,'VEC3');ix=accessor(f.reshape(-1),5125,'SCALAR');meshes.append({'primitives':[{'attributes':{'POSITION':pos,'NORMAL':nor},'indices':ix,'material':0}]});nodes.append({'name':row['id'],'mesh':len(meshes)-1,'extras':{'building_id':row['id'],'parent_id':row['parent_id'],'height_basis':row['height_basis'],'coverage':'Coarse source footprint extrusion; unverified facade','boundary_crossing':row['boundary_crossing'],'semantic_type':'site' if row.get('kind')=='site' else 'building'}});tri_count+=len(f)
    doc={'asset':{'version':'2.0','generator':'prepare_peripheral_overture.py'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'materials':[{'name':'Coarse peripheral neutral stone','pbrMetallicRoughness':{'baseColorFactor':color or [.55,.59,.61,1],'metallicFactor':0,'roughnessFactor':.85}}],'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors};j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*(-len(j)%4);binary.extend(b'\0'*(-len(binary)%4));path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\0')+binary);return tri_count


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--core',type=Path,required=True);args=ap.parse_args();root=args.input;core=json.load(open(args.core));crs=CRS.from_proj4('+proj=aeqd +lat_0=51.5053 +lon_0=-.0188 +datum=WGS84 +units=m');project=Transformer.from_crs(4326,crs,always_xy=True).transform;aoi=box(-2000,-2000,2000,2000)
    core_ids={x['id']for x in core['buildings']};corepolys=[Polygon(p['outer'],p.get('holes',[]))for x in core['buildings']if x['kind']!='site'for p in x['geometry']];protect=unary_union([box(-500,-500,500,500),*corepolys]);features={};rawcounts={};exclusions=[]
    for kind,file in [('building','buildings.geojson'),('part','building_parts.geojson')]:
        data=json.load(open(root/'references'/file));rawcounts[kind]=len(data['features'])
        for f in data['features']:
            g=transform(project,shape(f['geometry']));ident='overture-'+kind+'-'+f['id']
            if not g.is_valid:exclusions.append({'id':ident,'reason':'invalid_source_polygon'});continue
            if not g.intersects(aoi):continue
            features[ident]=(f,g,kind)
    children=collections.defaultdict(list)
    for ident,(f,g,kind)in features.items():
        if kind=='part'and not f['properties'].get('is_underground'):children[f['properties'].get('building_id')].append(g)
    rows=[]
    for ident,(f,g,kind)in features.items():
        p=f['properties'];why=None
        if ident in core_ids:why='existing_detailed_core_id'
        elif p.get('is_underground'):why='underground_not_exterior'
        if why:exclusions.append({'id':ident,'reason':why});continue
        if kind=='building'and children[f['id']]:g=g.difference(unary_union(children[f['id']]))
        if g.is_empty or g.area<1e-4:exclusions.append({'id':ident,'reason':'parent_covered_by_source_parts'});continue
        if g.intersection(protect).area>1e-4:exclusions.append({'id':ident,'reason':'overlaps_protected_core_full_feature_excluded','overlap_m2':g.intersection(protect).area});continue
        h=p.get('height');basis='source_reported_height'
        if h is None:h=(p.get('num_floors')or 3)*3;basis='source_floors_times_assumed_3m'if p.get('num_floors')else'assumed_9m_unknown_height'
        z=p.get('min_height');minimum_basis='source_reported_min_height'
        if z is None:z=(p.get('min_floor')or 0)*3;minimum_basis='source_min_floor_times_assumed_3m_or_zero'
        if h<=z:exclusions.append({'id':ident,'reason':'nonpositive_vertical_interval'});continue
        pieces=polygon_parts(g)
        if not pieces:continue
        rows.append({'id':ident,'name':(p.get('names')or{}).get('primary')or f['id'],'parent_id':p.get('building_id'),'kind':kind,'geometry':pieces,'height_m':float(h),'min_height_m':float(z),'height_basis':basis,'minimum_height_basis':minimum_basis,'boundary_crossing':not aoi.covers(g),'source_properties':p,'area_m2':g.area})
    out=root/'outer';out.mkdir(exist_ok=True);document={'crs':crs.to_string(),'origin_projected_m':[0,0],'axes':'X east Y north Z up, metres','vertical_datum':'Unsurveyed flat ground z=0; coarse assumed/source heights','aoi_bounds_enu':[-2000,-2000,2000,2000],'buildings':rows};(out/'geometry.json').write_text(json.dumps(document,separators=(',',':')));triangles=write_glb(rows,out/'outer.glb');report={'raw_feature_counts':rawcounts,'retained_building_and_part_records':len(rows),'triangles':triangles,'height_basis':dict(collections.Counter(r['height_basis']for r in rows)),'boundary_crossing':sum(r['boundary_crossing']for r in rows),'max_height_m':max(r['height_m']for r in rows),'core_owner_id_overlap':len(core_ids&{r['id']for r in rows}),'protected_core_overlap_area_m2':0,'excluded_reason_counts':dict(collections.Counter(x['reason']for x in exclusions)),'excluded':exclusions,'source_hashes':{n:hashlib.sha256((root/'references'/n).read_bytes()).hexdigest()for n in ['buildings.geojson','building_parts.geojson']},'outer_glb_sha256':hashlib.sha256((out/'outer.glb').read_bytes()).hexdigest(),'limits':['Full AOI-crossing footprints retained, bounds may extend beyond4km.','Parent envelopes subtract mapped part polygons; height assumptions explicit.','Existing detailedcore IDs and protectedcore overlap excluded wholesale, not clipped.','No facade details, terrain survey or imagery-derived geometry.']};(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='excluded'}))
if __name__=='__main__':main()
