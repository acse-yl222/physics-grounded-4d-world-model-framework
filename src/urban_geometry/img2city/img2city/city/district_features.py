"""Agent-authored, evidence-linked scene structures beyond building footprints."""
from pathlib import Path
import json
import math
from img2city import config,kit


def validate(plan, metas, anchor):
    from img2city.building.generate import validate_desc
    from img2city.library.audit import registry_names
    known=registry_names(str(kit.COMPONENTS_PY),'BUILDERS') | registry_names(str(kit.PARTS_LEARNED_PY),'PARTS_LEARNED')
    errors=[];features=plan.get('features')
    if not isinstance(features,list) or len(features)>16:
        return ['features must be a list of at most 16 instances']
    s,w,n,e=anchor['bbox'];kx=111320*math.cos(math.radians(anchor['lat0']))
    bounds=((w-anchor['lon0'])*kx,(e-anchor['lon0'])*kx,(s-anchor['lat0'])*110540,(n-anchor['lat0'])*110540)
    ids=set()
    from shapely.geometry import Polygon,box
    from shapely.affinity import rotate,translate
    existing=[Polygon(m['pts']) for m in metas]
    for feature in features:
        try:
            fid=feature['id'];pos=feature['position_m'];angle=float(feature['rotation_deg']);desc=feature['spec']
            if not isinstance(fid,str) or fid in ids:raise ValueError('duplicate/invalid id')
            ids.add(fid)
            if not isinstance(feature.get('evidence'),str) or not feature['evidence'].strip():raise ValueError('evidence required')
            if len(pos)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in pos):raise ValueError('invalid position')
            if not bounds[0]<=pos[0]<=bounds[1] or not bounds[2]<=pos[1]<=bounds[3] or not -10<=pos[2]<=20:raise ValueError('position outside district')
            _,errs=validate_desc(json.dumps(desc));errors.extend(f'{fid}: {e}' for e in errs)
            L,W=desc['footprint']
            if not 0<L<=250 or not 0<W<=100:raise ValueError('invalid feature extent')
            shape=translate(rotate(box(-L/2,-W/2,L/2,W/2),angle,origin=(0,0)),pos[0],pos[1])
            if any(shape.intersection(p).area > max(3,shape.area*0.05) for p in existing):
                raise ValueError('feature bounding footprint overlaps an existing building; separate adjacent station components')
            for part in desc.get('extra_parts') or []:
                if part.get('type') not in known:raise ValueError('unknown part '+str(part.get('type')))
        except (KeyError,TypeError,ValueError) as exc:
            errors.append(str(exc))
    return errors


def plan(out, feedback=None, model=config.SPEC_MODEL):
    from img2city.city.quality import _ask,_write
    from img2city.building.generate import spec_schema_tags
    out=Path(out);data=json.loads((out/'buildings.json').read_text());anchor=data['anchor'];metas=data['buildings']
    station=next(m for m in metas if m.get('btype')=='train_station')
    paths=[out/'block_sat_bbox.png',out/'buildings'/str(station['id'])/'satellite.png']
    platform=out/'station_platform_reference.png'
    if platform.exists():paths.append(platform)
    prompt=('You are the Img2City district assembly agent. Plan missing, OBSERVED station-complex '
            'structures that are NOT represented by the supplied building footprints. The station '
            'building must not be replaced with its adjacent platform canopy. Image 1 covers the '
            'district bbox north-up; image 2 is a close satellite view centered at the supplied station coordinate; '
            'optional image 3 is the station platform environment, NOT the station-house facade. '
            'Use satellite evidence for positions, extents and alignment. Do not duplicate existing buildings '
            'or hallucinate invisible underground structures. Keep unsupported details as limitations. '
            'Return JSON {"features":[{"id":string,"position_m":[east,north,z],"rotation_deg":number,'
            '"evidence":string,"spec":building_spec}],"limitations":[strings]}. '
            'Scene east/north are relative to the supplied anchor. Building local +x is its length; '
            'rotation_deg is counterclockwise from scene east. Explicit empty masses builds ONLY extra_parts. '
            'At most 16 compact feature groups. Reuse the kit. For straight platforms/rail strips, core '
            'extra_parts may use {type:"plinth",at:[x,y,z],size:[length,width,thickness],material:name}; '
            'these are plain editable cuboids. Do not add a generic large pedestal. '
            'If elevation/depth cannot be recovered, disclose its assumed value. Keep OSM tunnel sections '
            'underground. An empty plan is allowed only if evidence supports no missing features.\n'
            + spec_schema_tags(['london','rail_terminus'])+'\nMaterials: '+','.join(kit.material_names()))
    payload={'anchor':anchor,'station_image_center':station['center_latlng'],
             'existing_building_footprints':[{'id':m['id'],'pts':m['pts']} for m in metas],
             'transport_sources':json.loads((out/'transport_raw.json').read_text()),'review_feedback':feedback}
    previous=None
    for attempt in range(3):
        response,usage=_ask(prompt,dict(payload,previous=previous),[str(p) for p in paths],model)
        errors=validate(response,metas,anchor)
        _write(out/f'district_features_attempt_{attempt}.json',{'response':response,'errors':errors,'usage':usage})
        if not errors:
            response['model']=model;_write(out/'district_features.json',response);return response
        previous={'proposal':response,'validation_errors':errors}
    raise RuntimeError('Agent feature plan failed validation: '+str(errors))


BUILD = r'''
import json as _dfj, mathutils as _dfm, math as _dfmath
for _feature in _dfj.loads(%r):
    _desc = dict(_feature['spec']); _desc['plinth'] = False
    _objects = build_building(_desc)
    _matrix = (_dfm.Matrix.Translation(_feature['position_m']) @
               _dfm.Matrix.Rotation(_dfmath.radians(_feature['rotation_deg']), 4, 'Z'))
    for _object in _objects:
        _object.matrix_world = _matrix @ _object.matrix_world
        _object.name = 'DistrictFeature_' + _feature['id'] + '_' + _object.name
print('DISTRICT_FEATURES_OK')
'''


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--model',default=config.SPEC_MODEL)
    args=parser.parse_args()
    result=plan(args.out,model=args.model)
    print('Agent planned',len(result['features']),'district features')


if __name__=='__main__':
    main()


def ground_mesh(feature_plan, metas):
    """Expose agent-planned below-grade features rather than bury them under Ground."""
    from shapely.geometry import box
    from shapely.affinity import rotate,translate
    from shapely.ops import unary_union
    from shapely import constrained_delaunay_triangles
    points=[p for m in metas for p in m['pts']]
    outer=box(min(p[0] for p in points)-60,min(p[1] for p in points)-60,
              max(p[0] for p in points)+60,max(p[1] for p in points)+60)
    openings=[]
    for f in feature_plan.get('features',[]):
        if f['position_m'][2]>=-.1:continue
        L,W=f['spec']['footprint'];x,y,_=f['position_m']
        openings.append(translate(rotate(box(-L/2,-W/2,L/2,W/2),f['rotation_deg'],origin=(0,0)),x,y))
    if not openings:return None
    surface=outer.difference(unary_union(openings))
    # Unconstrained triangulation can cross excavation edges; dropping those
    # triangles leaves gaps around overlapping, rotated station footprints.
    triangles=list(constrained_delaunay_triangles(surface).geoms)
    if abs(sum(t.area for t in triangles)-surface.area)>max(1e-4,surface.area*1e-8):
        raise ValueError('Ground triangulation did not cover the excavation boundary')
    vertices=[];faces=[]
    for t in triangles:
        start=len(vertices);vertices.extend([[x,y,-.1] for x,y in list(t.exterior.coords)[:3]]);faces.append([start,start+1,start+2])
    return {'vertices':vertices,'faces':faces}


GROUND = r'''
_ground_data = __import__('json').loads(%r)
_ground_object = bpy.data.objects.get('Ground')
if _ground_object:
    _ground_materials = list(_ground_object.data.materials)
    _ground_mesh = bpy.data.meshes.new('AgentDistrictGround')
    _ground_mesh.from_pydata(_ground_data['vertices'], [], _ground_data['faces'])
    for _material in _ground_materials: _ground_mesh.materials.append(_material)
    _ground_object.data = _ground_mesh
'''
