"""Scene and view registry validation, including cross-run space/time agreement."""
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .contract import ROOT, read_json, validate, require
from .storage import scene_id, identifier


def schema_check(data,name):
    schema=read_json(ROOT/'schemas'/name)
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)


def project(storage,scene):
    scene=scene_id(scene);data=read_json(storage.metadata(scene)/'project.json')
    schema_check(data,'project-v1.schema.json')
    require(data['scene_id']==scene,'Scene ID differs from directory')
    return data


def view(storage,scene,name,check_assets=True):
    identifier(name);metadata=project(storage,scene)
    data=read_json(storage.metadata(scene)/'views'/f'{name}.json')
    schema_check(data,'view-v1.schema.json')
    require(data['scene_id']==metadata['scene_id'],'View belongs to another scene')
    runs={}
    for run_id in data['runs']:
        path=storage.run(scene,run_id)/'manifest.json'
        if check_assets:validate(path)
        manifest=read_json(path)
        require(manifest['status']=='complete','View references an incomplete run')
        require(manifest['scene_id']==metadata['scene_id'],'Run belongs to another scene')
        require(manifest['spatial'].get('georeferenced',True)==metadata['spatial'].get('georeferenced',True), 'Run georeferencing differs from scene')
        require(manifest['spatial']['frame']==metadata['spatial']['frame'] and manifest['spatial']['units']==metadata['spatial']['units'] and manifest['spatial']['origin']==metadata['spatial']['origin'],'Run spatial frame differs from scene')
        if data['time_alignment']=='absolute' and manifest['time']['samples']:
            require('epoch' in manifest['time'],'Absolute alignment requires run epochs')
        runs[run_id]=manifest
    ids=set()
    for layer in data['layers']:
        key=(layer['run_id'],layer['layer_id']);require(key not in ids,'Duplicate view layer');ids.add(key)
        require(layer['run_id'] in runs,'View layer references unknown run')
        require(layer['layer_id'] in [item['id'] for item in runs[layer['run_id']]['layers']],'View references missing layer')
    return data,runs
