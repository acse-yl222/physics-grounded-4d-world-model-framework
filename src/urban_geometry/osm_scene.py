"""Retained OSM footprints, explicitly assumed heights, and local ENU meshes."""
import math
import re
import xml.etree.ElementTree as ET

import numpy as np
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import polygonize, triangulate, unary_union
from shapely import intersects_xy

from traffic.sumo_pipeline import lonlat_to_scene


def metric_height(value):
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(m|ft|feet)?\s*', value or '')
    if not match:
        return None
    height = float(match[1]) * (0.3048 if match[2] in ('ft', 'feet') else 1)
    return height if math.isfinite(height) and height > 0 else None


def building_height(tags, default_height, level_height):
    height = metric_height(tags.get('height'))
    if height is not None:
        return height, 'osm_height'
    levels = metric_height(tags.get('building:levels'))
    if levels is not None:
        return levels * level_height, 'osm_levels_times_assumed_floor_height'
    return default_height, 'assumed_unknown_height'


def footprints(path, transform, default_height=9, level_height=3, project=None):
    document = ET.parse(path).getroot()
    nodes = {element.get('id'): [float(element.get('lon')), float(element.get('lat'))]
             for element in document.findall('node')}
    ways = {element.get('id'): element for element in document.findall('way')}
    features, skipped, members = [], [], set()

    def tags_of(element):
        return {tag.get('k'): tag.get('v') for tag in element.findall('tag')}

    def coordinates(element):
        references = [node.get('ref') for node in element.findall('nd')]
        if len(references) < 3 or any(reference not in nodes for reference in references):
            raise ValueError('Incomplete footprint node references')
        points = [nodes[reference] for reference in references]
        return np.asarray(project(points)) if project else lonlat_to_scene(points, transform)

    def append(element, geometry):
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError('Invalid footprint polygon')
        tags = tags_of(element)
        height, basis = building_height(tags, default_height, level_height)
        features.append({'id': element.tag + '/' + element.get('id'), 'geometry': geometry,
                         'height_m': height, 'height_basis': basis, 'tags': tags})

    for relation in document.findall('relation'):
        tags = tags_of(relation)
        if not (tags.get('building', 'no') != 'no' or tags.get('building:part', 'no') != 'no'):
            continue
        try:
            outer, inner, used = [], [], []
            for member in relation.findall('member'):
                if member.get('type') != 'way':
                    continue
                way = ways[member.get('ref')]
                (inner if member.get('role') == 'inner' else outer).append(LineString(coordinates(way)))
                used.append(member.get('ref'))
            geometry = unary_union(list(polygonize(outer)))
            if inner:
                geometry = geometry.difference(unary_union(list(polygonize(inner))))
            append(relation, geometry)
            members.update(used)
        except (KeyError, ValueError) as error:
            skipped.append({'id': 'relation/' + relation.get('id'), 'reason': str(error)})
    for identity, way in ways.items():
        tags = tags_of(way)
        if identity in members or not (tags.get('building', 'no') != 'no' or tags.get('building:part', 'no') != 'no'):
            continue
        try:
            points = coordinates(way)
            if not np.array_equal(points[0], points[-1]):
                raise ValueError('Open building outline')
            append(way, Polygon(points))
        except ValueError as error:
            skipped.append({'id': 'way/' + identity, 'reason': str(error)})
    return features, skipped


def height_grid(features, half_width, cell):
    size = round(2 * half_width / cell)
    if not math.isclose(size * cell, 2 * half_width):
        raise ValueError('Domain must be divisible by grid spacing')
    height = np.zeros((size, size), dtype=np.float32)
    axis = -half_width + (np.arange(size) + .5) * cell
    for feature in features:
        geometry = feature['geometry']
        west, south, east, north = geometry.bounds
        columns = np.flatnonzero((axis >= west) & (axis <= east))
        rows = np.flatnonzero((axis >= south) & (axis <= north))
        if not len(columns) or not len(rows):
            continue
        covered = intersects_xy(geometry, axis[columns][None, :], axis[rows][:, None])
        selection = np.ix_(rows, columns)
        height[selection] = np.maximum(height[selection], covered * feature['height_m'])
    return height


def mesh(features, bounds):
    positions, triangles = [], []
    domain = box(*bounds)

    def triangle(points):
        start = len(positions)
        positions.extend(points)
        triangles.append([start, start + 1, start + 2])

    for feature in features:
        clipped = feature['geometry'].intersection(domain)
        polygons = [clipped] if clipped.geom_type == 'Polygon' else getattr(clipped, 'geoms', [])
        height = feature['height_m']
        for polygon in polygons:
            if polygon.geom_type != 'Polygon' or polygon.is_empty:
                continue
            for face in triangulate(polygon):
                if polygon.covers(face):
                    triangle([[float(east), float(north), height] for east, north in list(face.exterior.coords)[:3]])
            for ring in [polygon.exterior, *polygon.interiors]:
                points = list(ring.coords)
                for first, second in zip(points[:-1], points[1:]):
                    bottom_first, bottom_second = [*first, 0.], [*second, 0.]
                    top_first, top_second = [*first, height], [*second, height]
                    triangle([bottom_first, bottom_second, top_second])
                    triangle([bottom_first, top_second, top_first])
    return {'positions': positions, 'triangles': triangles}


def feature_collection(features):
    return {'type': 'FeatureCollection', 'coordinate_frame': 'local ENU metres; not WGS84 GeoJSON',
            'features': [{'type': 'Feature', 'geometry': mapping(feature['geometry']),
                          'properties': {key: value for key, value in feature.items() if key != 'geometry'}}
                         for feature in features]}
