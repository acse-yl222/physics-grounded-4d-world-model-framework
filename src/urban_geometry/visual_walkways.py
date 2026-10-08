"""User-authorized hypothetical shade structures above mapped walking routes."""


def build(ctx, feature):
    mesh = ctx.mesh('ARTISTIC proposed covered walks; not surveyed')
    roof = ctx.material('visual walkway pale canopy', (.69, .65, .54), rough=.8)
    post = ctx.material('visual walkway posts', (.40, .33, .26), rough=.7)
    for route in feature['routes']:
        mesh.shell(route['geometry'], 3.05, 3.22, roof)
        mesh.surface(route['geometry'], 3.05, roof)
        for position in route['posts']:
            mesh.box(position[0], position[1], 1.525, .14, .14, 3.05, post)
    obj = mesh.done()
    obj['support_not_building'] = True
    obj['detail_basis'] = 'Hypothetical canopy on mapped walking route; not observed connecting architecture'
    return {'created': [obj.name], 'parameters': {'proposed_routes': len(feature['routes']), 'artistic': True},
            'interfaces': {}, 'evidence_source_ids': feature['evidence_source_ids'],
            'uncertainty': ['Mapped route location retained; canopy, posts and all dimensions are artistic estimates.',
                            'No actual building access, covered connection or accessibility compliance asserted.']}
