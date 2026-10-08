"""Add explicitly estimated roof finishes without changing mapped roof outlines."""


def build(ctx, feature):
    plan = feature['roof_detail']
    level = plan['roof_level_m']
    mesh = ctx.mesh('ARTISTIC roof finish drainage and rooflights')
    finish = ctx.material('roof warm mineral finish', (.61, .58, .49), rough=.95)
    joint = ctx.material('roof recessed drainage strip', (.23, .25, .25), rough=.85)
    paver = ctx.material('roof pale maintenance pavers', (.76, .73, .65), rough=.9)
    curb = ctx.material('rooflight estimated metal curb', (.44, .46, .44), rough=.5, metal=.3)
    glass = ctx.material('rooflight estimated opaque glazing', (.18, .31, .34), rough=.3, metal=.25)
    mesh.surface(plan['drainage'], level + .018, joint)
    mesh.surface(plan['panels'], level + .025, finish)
    mesh.surface(plan['walks'], level + .035, paver)
    for center in plan['rooflights']:
        east, north = center
        mesh.box(east, north, level + .10, 1.8, 2.6, .15, curb)
        mesh.box(east, north, level + .20, 1.6, 2.4, .10, glass)
        mesh.box(east, north, level + .26, .045, 2.4, .035, curb)
        mesh.box(east, north, level + .26, 1.6, .045, .035, curb)
    obj = mesh.done()
    obj['detail_basis'] = 'ARTISTIC roof finish and rooflight estimates; not observed site facts'
    obj['source_building_id'] = feature['source_building_id']
    return {'created': [obj.name],
            'parameters': {'roof_level_m': level, 'rooflights': len(plan['rooflights']),
                           'within_existing_parapet_height': True},
            'interfaces': {}, 'evidence_source_ids': feature['evidence_source_ids'],
            'uncertainty': ['Roof finish, drainage strips, maintenance paving and opaque rooflight housings are visual estimates.',
                            'No hydraulic design, roof penetration, transmission or interior daylight simulation is represented.']}
