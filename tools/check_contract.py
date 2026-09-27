#!/usr/bin/env python3
"""Validate protocol v1 manifests and the minimum JSON asset encoding."""
import argparse
import json
import math
from pathlib import Path, PurePosixPath
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'{path}: duplicate JSON key {key}')
            result[key] = value
        return result
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates)
    def finite(value):
        if isinstance(value, float):
            require(math.isfinite(value), f'{path}: non-finite number')
        elif isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    finite(data)
    return data


def numeric(value, shape, integer=False):
    if not shape:
        require(type(value) is int if integer else type(value) in (int, float), 'invalid numeric value')
        return
    require(isinstance(value, list) and len(value) == shape[0], f'expected array shape {shape}')
    for child in value:
        numeric(child, shape[1:], integer)


def count(value):
    require(isinstance(value, list) and len(value) > 0, 'expected nonempty array')
    return len(value)


def validate(path):
    path = Path(path).resolve()
    manifest = read_json(path)
    schema = read_json(ROOT / 'schemas/run-manifest-v1.schema.json')
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    bounds = manifest['spatial']['bounds_m']
    require(all(a <= b for a, b in zip(bounds['min'], bounds['max'])), 'reversed spatial bounds')
    samples = manifest['time']['samples']
    require(all(a < b for a, b in zip(samples, samples[1:])), 'time samples must strictly increase')
    ids = [layer['id'] for layer in manifest['layers']]
    require(len(ids) == len(set(ids)), 'duplicate layer IDs')
    dynamic = any(layer['sampling'] != 'static' for layer in manifest['layers'])
    require(bool(samples) == dynamic, 'dynamic layers require samples; static runs require empty samples')
    for layer in manifest['layers']:
        rel = PurePosixPath(layer['asset'])
        require(not rel.is_absolute() and '..' not in rel.parts and ':' not in layer['asset']
                and '\\' not in layer['asset'], 'asset must be a relative path within the run')
        asset = (path.parent / str(rel)).resolve()
        require(asset.is_relative_to(path.parent), 'asset escapes run directory')
        require(asset.is_file(), f'missing asset: {layer["asset"]}')
        data = read_json(asset)
        require(isinstance(data, dict), 'asset must be a JSON object')
        kind = layer['kind']
        expected = {'mesh': {'positions', 'triangles'}, 'scalar_field': {'positions', 'values'},
                    'vector_field': {'positions', 'vectors'}, 'trajectories': {'ids', 'positions'},
                    'time_series': {'labels', 'values'}}[kind]
        require(set(data) == expected, f'{kind}: unexpected or missing payload fields')
        if kind in ('mesh', 'scalar_field', 'vector_field'):
            n = count(data['positions'])
            numeric(data['positions'], [n, 3])
        elif kind == 'trajectories':
            n = count(data['ids'])
            require(all(isinstance(i, str) and i for i in data['ids']), 'invalid entity IDs')
            require(len(set(data['ids'])) == n, 'duplicate entity IDs')
        else:
            n = count(data['labels'])
            require(all(isinstance(i, str) and i for i in data['labels']), 'invalid channel labels')
            require(len(set(data['labels'])) == n, 'duplicate channel labels')
        prefix = [] if layer['sampling'] == 'static' else [len(samples)]
        if kind == 'mesh':
            numeric(data['triangles'], [count(data['triangles']), 3], integer=True)
            require(all(0 <= i < n for tri in data['triangles'] for i in tri), 'mesh index out of range')
        elif kind in ('scalar_field', 'time_series'):
            numeric(data['values'], prefix + [n])
        elif kind == 'vector_field':
            numeric(data['vectors'], prefix + [n, 3])
        else:
            numeric(data['positions'], prefix + [n, 3])
        display = layer['display']
        if 'range' in display:
            require(display['range'][0] < display['range'][1], 'display range must increase')
    return len(manifest['layers'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        layers = validate(args.manifest)
    except Exception as exc:
        print(f'INVALID: {exc}', file=sys.stderr)
        return 1
    print(f'VALID: {args.manifest} ({layers} layers; JSON assets checked)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
