"""Explicit historical inputs and isolated experiment outputs; never restore directory links."""
import json
import os
from pathlib import Path
import time
import uuid
from .storage import Storage, identifier, within, scene_id

_TRIALS={}


def source_path(name,*parts,scene='windfarm'):
    identifier(name)
    storage=Storage.load();path=storage.root/'sources.local.json'
    config=json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('sources.local.json must be an object of named absolute paths')
    value=os.environ.get('UWM_SOURCE_'+name.upper()) or config.get(name)
    if value is None:
        # No implicit access to another checkout or old filesystem root.
        return within(storage.assets(scene, 'input'), name, *parts)
    if not isinstance(value, str) or not value:
        raise ValueError(f'External source {name} must be a nonempty absolute path')
    root=Path(value).expanduser()
    if not root.is_absolute():raise ValueError(f'External source {name} must be absolute')
    return within(root,*parts)


def trial_root(scene,simulation):
    storage = Storage.load()
    scene = scene_id(scene)
    identifier(simulation)
    key=(str(storage.cache_root),scene,simulation)
    run_id=os.environ.get('UWM_RUN_ID')
    if run_id is None:
        if key not in _TRIALS:_TRIALS[key]=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+uuid.uuid4().hex[:8]
        run_id=_TRIALS[key]
    return storage.scratch(scene,simulation,identifier(run_id,run=True))
