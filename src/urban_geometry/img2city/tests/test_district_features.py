import json
from img2city.city.district_features import validate

ANCHOR={'lat0':51,'lon0':0,'bbox':[50.99,-.01,51.01,.01]}

def feature(x=100):
    return {'features':[{'id':'platform','position_m':[x,100,0], 'rotation_deg':0,'evidence':'visible in satellite',
        'spec':{'footprint':[20,5],'masses':[],'extra_parts':[{'type':'platform_canopy','length':20,'width':5}]}}]}

def test_feature_requires_evidence_and_district_bounds():
    assert not validate(feature(),[],ANCHOR)
    assert validate(feature(99999),[],ANCHOR)
    bad=feature();bad['features'][0]['evidence']=''
    assert validate(bad,[],ANCHOR)

def test_scene_features_cannot_duplicate_existing_buildings():
    assert validate(feature(),[{'pts':[[80,80],[120,80],[120,120],[80,120]]}],ANCHOR)

def test_agent_colour_contract():
    from img2city.building.generate import validate_desc
    spec={'footprint':[30,20],'colors':{'wall':[.6,.03,.02]}}
    assert not validate_desc(json.dumps(spec))[1]
    spec['colors']['wall']=[255,0,0]
    assert validate_desc(json.dumps(spec))[1]


def test_below_grade_features_are_not_hidden_by_ground():
    from img2city.city.district_features import ground_mesh
    p=feature(0);p['features'][0]['position_m']=[0,0,-5]
    ground=ground_mesh(p,[{'pts':[[-50,-50],[50,-50],[50,50],[-50,50]]}])
    from shapely.geometry import Polygon
    triangles=[Polygon([ground['vertices'][i][:2] for i in face]) for face in ground['faces']]
    assert abs(sum(t.area for t in triangles)-(220*220-100))<1e-6
    assert all(not t.contains(__import__('shapely').geometry.Point(0,0)) for t in triangles)


def test_ground_covers_rotated_overlapping_excavation_boundaries():
    from img2city.city.district_features import ground_mesh
    from shapely.geometry import Polygon, box
    from shapely.affinity import rotate, translate
    from shapely.ops import unary_union
    p={'features':[]}; openings=[]
    for x,y,L,W,angle in [(95,10.6,86,18,-8),(112,9.4,120,19,-8),(102,24,90,.85,-8)]:
        f=feature()['features'][0]
        f.update(position_m=[x,y,-5],rotation_deg=angle)
        f['spec']['footprint']=[L,W]
        p['features'].append(f)
        openings.append(translate(rotate(box(-L/2,-W/2,L/2,W/2),angle,origin=(0,0)),x,y))
    ground=ground_mesh(p,[{'pts':[[-200,-200],[200,-200],[200,200],[-200,200]]}])
    actual=unary_union([Polygon([ground['vertices'][i][:2] for i in face]) for face in ground['faces']])
    expected=box(-260,-260,260,260).difference(unary_union(openings))
    assert actual.symmetric_difference(expected).area < 1e-6
