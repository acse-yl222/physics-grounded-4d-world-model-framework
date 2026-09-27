"""Locate the checkout independently of a module's depth."""
import os
from pathlib import Path


def repo_root():
    value=os.environ.get('UWM_ROOT')
    if value:return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def agent_src():
    return repo_root() / 'src/urban_geometry/agent'


def authoring_path(relative=''):
    from .storage import Storage
    path=Path(relative)
    if path.parts and path.parts[0]=='src':
        return agent_src().joinpath(*path.parts[1:])
    return Storage.load().assets('south_ken','geometry')/'authoring'/path


def scene_input(scene, *parts):
    from .storage import Storage, within
    return within(Storage.load().assets(scene, 'input'), *parts)
