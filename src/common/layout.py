"""Locate the checkout independently of a module's depth."""
from pathlib import Path
from .locations import code_path, workspace_root


def repo_root():
    return workspace_root()


def agent_src():
    return code_path('src/urban_geometry/agent')


def authoring_path(relative=''):
    from .storage import Storage
    path=Path(relative)
    if path.parts and path.parts[0]=='src':
        return agent_src().joinpath(*path.parts[1:])
    return Storage.load().assets('south_ken','geometry')/'authoring'/path


def scene_input(scene, *parts):
    from .storage import Storage, within
    return within(Storage.load().assets(scene, 'input'), *parts)
