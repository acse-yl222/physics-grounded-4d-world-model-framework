"""Explicitly artistic exterior detailing on preserved mapped building footprints."""
import math


PALETTES = {'sandstone': (.62, .39, .27), 'cream': (.72, .67, .52), 'brick': (.48, .27, .20)}


def build(ctx, feature):
    plan = feature['visual_detail']
    profile = plan['profile']
    height = float(feature['height_m'])
    roof_level = height - profile['parapet_height_m']
    floors = plan['floors']
    storey = roof_level / floors
    walls = ctx.mesh('ARTISTIC inferred facades')
    details = ctx.mesh('ARTISTIC frames shades and roof edges')
    glazing = ctx.mesh('ARTISTIC recessed glazing')
    wall = ctx.material('visual ' + profile['palette'], PALETTES[profile['palette']], rough=.82)
    trim = ctx.material('visual limestone trim', (.74, .71, .62), rough=.75)
    glass = ctx.material('visual blue grey glass', (.11, .23, .27), rough=.25, metal=.15)
    frame = ctx.material('visual dark metal', (.15, .18, .18), rough=.4, metal=.4)
    roof = ctx.material('visual roof finish', (.43, .43, .39), rough=.95)
    openings_count = 0
    for edge in plan['edges']:
        start, end = edge['start'], edge['end']
        length = math.dist(start, end)
        tangent = [(end[axis] - start[axis]) / length for axis in (0, 1)]
        normal = [tangent[1], -tangent[0]]
        angle = math.atan2(tangent[1], tangent[0])

        def point(distance, elevation, inset=0):
            return (start[0] + tangent[0] * distance - normal[0] * inset,
                    start[1] + tangent[1] * distance - normal[1] * inset, elevation)

        def panel(left, right, bottom, top, material):
            if right - left > 1e-7 and top - bottom > 1e-7:
                walls.face([point(left, bottom), point(right, bottom), point(right, top), point(left, top)], material)

        count = max(1, int(length / profile['bay_pitch_m']))
        pitch = length / count
        width = min(profile['window_width_m'], pitch * .57)
        for floor in range(floors):
            base, top = floor * storey, (floor + 1) * storey
            exposed = edge['exposed'] or base >= edge.get('blocked_height_m', height) + .01
            eligible = exposed and length >= 1.7 and storey > 1.7
            if not eligible:
                panel(0, length, base, top, wall)
                continue
            for bay in range(count):
                left, right = bay * pitch, (bay + 1) * pitch
                center = (left + right) / 2
                is_door = edge.get('entrance') and floor == 0 and bay == count // 2
                lower = base if is_door else base + storey * .28
                upper = min(top - .30, lower + (2.15 if is_door else profile['window_height_m']))
                opening_left, opening_right = center - width / 2, center + width / 2
                panel(left, opening_left, base, top, wall)
                panel(opening_right, right, base, top, wall)
                panel(opening_left, opening_right, base, lower, wall)
                panel(opening_left, opening_right, upper, top, wall)
                depth = min(.14, pitch * .06)
                outer = [point(opening_left, lower), point(opening_right, lower),
                         point(opening_right, upper), point(opening_left, upper)]
                inner = [point(opening_left, lower, depth), point(opening_right, lower, depth),
                         point(opening_right, upper, depth), point(opening_left, upper, depth)]
                for index in range(4):
                    next_index = (index + 1) % 4
                    walls.face([outer[index], outer[next_index], inner[next_index], inner[index]], trim)
                glazing.face(inner, glass)
                for distance in (opening_left + .03, center, opening_right - .03):
                    details.box(*point(distance, (lower + upper) / 2, depth - .025),
                                .06, .055, upper - lower, frame, angle=angle)
                for elevation in (lower + .03, upper - .03):
                    details.box(*point(center, elevation, depth - .025), width, .055, .06, frame, angle=angle)
                if not is_door:
                    shade = min(profile['shade_depth_m'], max(.02, edge['clearance_m']) * .4)
                    details.box(*point(center, upper + .08, -shade / 2), width + .14, shade, .10, trim, angle=angle)
                openings_count += 1
            details.box(*point(length / 2, top - .06, .012), length, .035, .10, trim, angle=angle)
    walls.surface(feature['geometry'], roof_level, roof)
    for part in plan['parapets']:
        for ring in [part['outer'], *part['holes']]:
            for start, end in zip(ring, ring[1:] + ring[:1]):
                details.face([(*start, roof_level), (*end, roof_level), (*end, height), (*start, height)], wall)
    details.surface(plan['parapets'], height, trim)
    objects = [mesh.done() for mesh in (walls, details, glazing)]
    for obj in objects:
        if obj is not None:
            obj['detail_basis'] = 'USER AUTHORIZED ARTISTIC ESTIMATE; not measured or photo-recovered'
            obj['height_basis'] = feature['height_basis']
            obj['inferred_floors'] = floors
    return {'created': [obj.name for obj in objects if obj is not None],
            'parameters': {'height_m': height, 'floors': floors, 'openings': openings_count,
                           'profile': profile, 'footprint_preserved': True, 'artistic': True},
            'interfaces': {}, 'evidence_source_ids': feature['evidence_source_ids'],
            'uncertainty': ['Mapped outline retained; facade, entrances, floor spacing, shading and roof-edge design are artistic estimates.',
                            'This visual asset is not a surveyed building or a calibrated simulation obstacle.']}
