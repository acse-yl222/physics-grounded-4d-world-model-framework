"""Export SUMO lane-width polygons and junction outlines, without rasterization.

Source ENU geometry and topology are retained separately. Presentation is flattened
in y to match the existing corridor buildings and recorded vehicle display.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely import make_valid
import mapbox_earcut

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def export(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    index = json.loads((source/'road_network.json').read_text())
    network = {k: [] for k in ['edges','lanes','connections','junctions']}
    for entry in index['chunks']:
        assert sha(source/entry['asset']) == entry['sha256'], entry['asset']
        part = json.loads((source/entry['asset']).read_text())
        for k in network: network[k].extend(part[k])
    for k in network: assert len(network[k]) == index['counts'][k], k
    for c in network['connections']:
        for k in ['from_lane','to_lane','via']:
            assert c[k] is None or 0 <= c[k] < len(network['lanes'])
    groups = {k: {'positions': [], 'indices': [], 'vertices': 0, 'polygons': 0} for k in
              ['carriageways','junction_connections','junction_surfaces','lane_boundaries']}
    extent = box(-4096,-4096,4096,4096)
    audit = {'source_counts': index['counts'], 'source_provenance': index['provenance'],
             'source_index_sha256': sha(source/'road_network.json'), 'display_counts': {},
             'clipped_lane_ids': [], 'invalid_junctions_repaired': [], 'degenerate_lane_ids': [],
             'source_code_sha256': sha(__file__), 'dependencies': {'shapely':shapely.__version__,
             'mapbox_earcut':mapbox_earcut.__version__, 'numpy':np.__version__}, 'limits': [
             'Full source motor-road network; pedestrian-, bicycle- and rail-only lanes were excluded upstream.',
             'Lane widths and junction outlines are vector geometry. Source precision is 0.1 m; this is not a surveyed road model.',
             'Display is flattened to match the existing buildings and recorded vehicles. Original source elevations and estimated bridge classifications are retained in source JSON.',
             'Optional lane boundaries show geometric widths, not surveyed painted markings.',
             'Only display polygons are clipped to the 8192 m domain; original paths and topology are preserved.']}
    def add(poly, name, height):
        if poly.is_empty: return
        if poly.geom_type != 'Polygon':
            for item in getattr(poly,'geoms',[]): add(item,name,height)
            return
        if poly.area < 1e-8: return
        rings = [np.asarray(r.coords)[:-1,:2] for r in [poly.exterior,*poly.interiors]]
        xy = np.concatenate(rings)
        faces = mapbox_earcut.triangulate_float64(xy,np.cumsum([len(r) for r in rings],dtype=np.uint32)).reshape(-1,3)
        tri = xy[faces]
        area = np.abs((tri[:,1,0]-tri[:,0,0])*(tri[:,2,1]-tri[:,0,1])-(tri[:,1,1]-tri[:,0,1])*(tri[:,2,0]-tri[:,0,0])).sum()/2
        assert abs(area-poly.area) <= max(.001,poly.area*1e-6), (name,area,poly.area)
        g=groups[name]
        vertices=np.column_stack([xy[:,0],np.full(len(xy),height),-xy[:,1]]).astype('<f4')
        assert np.isfinite(vertices).all()
        g['positions'].append(vertices);g['indices'].append((faces+g['vertices']).astype('<u4'))
        g['vertices']+=len(xy);g['polygons']+=1
    for lane in network['lanes']:
        points=np.asarray(lane['shape'])[:,:2]
        assert lane['width']>0 and np.isfinite(points).all()
        if len(points)<2 or LineString(points).length<1e-6:
            audit['degenerate_lane_ids'].append(lane['id']);continue
        surface=LineString(points).buffer(lane['width']/2,cap_style='flat',join_style='mitre',mitre_limit=2)
        if not extent.covers(surface):audit['clipped_lane_ids'].append(lane['id'])
        name='junction_connections' if lane['edge'] is None else 'carriageways'
        add(surface.intersection(extent),name,.025)
        if lane['edge'] is not None:
            add(surface.boundary.buffer(.045,join_style='mitre').intersection(extent),'lane_boundaries',.055)
    for junction in network['junctions']:
        if len(junction['shape'])<3:continue
        poly=Polygon([p[:2] for p in junction['shape']])
        if not poly.is_valid:
            audit['invalid_junctions_repaired'].append(junction['id']);poly=make_valid(poly)
        add(poly.intersection(extent),'junction_surfaces',.03)
    materials=[]
    for name,color in [('Road surface',[.12,.13,.14,1]),('Lane width boundaries (schematic)',[.72,.68,.5,1])]:
        materials.append({'name':name,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':color,'metallicFactor':0,'roughnessFactor':1},'extensions':{'KHR_materials_unlit':{}}})
    doc={'asset':{'version':'2.0','generator':'vector_roads.py'},'extensionsUsed':['KHR_materials_unlit'],
         'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],'accessors':[],'bufferViews':[],
         'buffers':[],'materials':materials,'extras':{'source_frame':'ENU metres','display_transform':'x=east,y=flat display offset,z=-north','source_index_sha256':audit['source_index_sha256']}}
    binary=bytearray()
    def accessor(array,typ,component,target):
        start=len(binary);data=array.tobytes();binary.extend(data);binary.extend(b'\0'*((-len(binary))%4))
        view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(data),'target':target})
        a={'bufferView':view,'componentType':component,'count':len(array) if typ=='VEC3' else array.size,'type':typ}
        if typ=='VEC3':a.update(min=array.min(axis=0).tolist(),max=array.max(axis=0).tolist())
        doc['accessors'].append(a);return len(doc['accessors'])-1
    for name,g in groups.items():
        if not g['positions']:continue
        v=np.concatenate(g['positions']);f=np.concatenate(g['indices'])
        pos=accessor(v,'VEC3',5126,34962);idx=accessor(f,'SCALAR',5125,34963)
        mesh=len(doc['meshes']);doc['meshes'].append({'name':name,'primitives':[{'attributes':{'POSITION':pos},'indices':idx,'material':1 if name=='lane_boundaries' else 0}]})
        doc['scenes'][0]['nodes'].append(len(doc['nodes']));doc['nodes'].append({'name':name,'mesh':mesh})
        audit['display_counts'][name]={'vertices':len(v),'triangles':len(f),'polygons':g['polygons']}
    doc['buffers']=[{'byteLength':len(binary)}]
    data=json.dumps(doc,separators=(',',':')).encode();data+=b' '*((-len(data))%4)
    glb=struct.pack('<IIIII',0x46546c67,2,28+len(data)+len(binary),len(data),0x4e4f534a)+data+struct.pack('<II',len(binary),0x004e4942)+binary
    (destination/'roads.glb').write_bytes(glb)
    audit.update(geometry_sha256=sha(destination/'roads.glb'),geometry_bytes=len(glb))
    for name in ['road_network.json',*[c['asset'] for c in index['chunks']]]:shutil.copy2(source/name,destination/name)
    (destination/'roads-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k] for k in ['geometry_bytes','display_counts']}))
    return audit

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('destination')
    args=parser.parse_args();export(args.source,args.destination)
