"""Closed footprint extrusion: explicitly a massing baseline, not facade reconstruction."""
import bpy


def build(ctx, feature):
    vertices, faces = [], []
    low, high = feature['min_height_m'], feature['height_m']
    def face(points):
        start = len(vertices); vertices.extend(points); faces.append(tuple(range(start, len(vertices))))
    for part in feature['geometry']:
        for triangle in part['triangles']:
            a,b,c=triangle
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]) < 0:
                triangle = list(reversed(triangle))
            face([(*p,high) for p in triangle]); face([(*p,low) for p in reversed(triangle)])
        for ring in [part['outer'], *part['holes']]:
            for a,b in zip(ring, ring[1:]+ring[:1]):
                face([(*a,low),(*b,low),(*b,high),(*a,high)])
    mesh=bpy.data.meshes.new(feature['id']);mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(feature['id'],mesh);ctx.collection.objects.link(ob)
    known=feature['height_basis']=='source_reported_height'
    material=ctx.material('Source height' if known else 'Estimated height', (.48,.64,.70) if known else (.72,.57,.38), rough=.7)
    ob.data.materials.append(material)
    ob['height_basis']=feature['height_basis'];ob['coverage']='massing baseline; facades unverified'
    return {'created':[ob.name], 'parameters':{'height_m':high,'min_height_m':low}, 'interfaces':{},
            'uncertainty':['No facade detail; flat roof except separately authored roof parts; unsurveyed ground'],
            'evidence_source_ids':feature['evidence_source_ids']}
