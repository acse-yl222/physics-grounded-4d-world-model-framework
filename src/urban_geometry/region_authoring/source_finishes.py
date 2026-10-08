"""Apply explicitly mapped finishes to massing; not an image-verified facade."""
import re
from . import baseline


def linear_color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        return None
    rgb=[int(value[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)


def build(ctx, feature):
    result=baseline.build(ctx,feature)
    props=feature.get('source_properties',{})
    palettes={'brick':((.28,.105,.055),.85,0),'glass':((.18,.30,.34),.25,.18),
              'metal':((.42,.46,.48),.35,.7),'wood':((.25,.15,.075),.8,0),
              'slate':((.10,.12,.14),.8,0)}
    applied=[]
    for role in ['facade','roof']:
        material_type=props.get(role+'_material')
        explicit_color=linear_color(props.get(role+'_color'))
        if material_type not in palettes and explicit_color is None:
            continue
        default,rough,metal=palettes.get(material_type,((.4,.4,.4),.7,0))
        color=explicit_color or default
        key=f'mapped-{role}-{material_type or "unknown"}-{props.get(role+"_color", "illustrative")} '
        material=ctx.material(key,color,rough=rough,metal=metal)
        for ob in ctx.collection.objects:
            ob.data.materials.append(material);slot=len(ob.data.materials)-1
            for face in ob.data.polygons:
                if (role=='roof' and face.normal.z>.99) or (role=='facade' and abs(face.normal.z)<.01):
                    face.material_index=slot
        applied.append({'role':role,'mapped_material':material_type,'mapped_color':props.get(role+'_color'),
                        'color_basis':'mapped sRGB converted to linear' if explicit_color else 'illustrative material palette',
                        'shader_parameters':'illustrative, not measured'})
    result['parameters']['source_finishes']=applied
    result['uncertainty'].append('Source material tags only; shader response and unspecified color are illustrative. Glass facade massing is opaque; no claim of reconstructed glazing.')
    return result
