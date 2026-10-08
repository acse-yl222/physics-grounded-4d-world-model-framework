"""Flat cartographic support; no terrain or water-level measurement is implied."""
import bpy


def build(ctx, feature):
    created=[]
    for label,parts,z,color in [('ground',feature['geometry'],-.1,(.20,.24,.26)),('water',feature['water'],.01,(.12,.32,.40))]:
        vertices=[];faces=[]
        for part in parts:
            for t in part['triangles']:
                start=len(vertices); vertices.extend([(*p,z) for p in t]);faces.append((start,start+1,start+2))
        if not faces:continue
        mesh=bpy.data.meshes.new(label);mesh.from_pydata(vertices,[],faces);mesh.update()
        ob=bpy.data.objects.new(label,mesh);ctx.collection.objects.link(ob);ob.data.materials.append(ctx.material(label,color,rough=.9));created.append(ob.name)
    return {'created':created,'parameters':{'ground_z_m':-.1,'water_z_m':.01},'interfaces':{},
            'uncertainty':['Flat cartographic support only; water/terrain elevations unmeasured'],
            'evidence_source_ids':feature['evidence_source_ids']}
