"""Resolve repository metadata, retained scene assets and disposable run workspaces."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

ALIASES = {'south_kensington': 'south_ken', 'core008': 'south_ken'}


def identifier(value, *, run=False):
    pattern = r'[A-Za-z0-9][A-Za-z0-9_-]*' if run else r'[a-z][a-z0-9_]*'
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f'Invalid {"run" if run else "scene/module"} identifier: {value!r}')
    return value


def scene_id(value):
    return identifier(ALIASES.get(value, value))


def within(base, *parts):
    base = Path(base).resolve()
    target = base.joinpath(*parts).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f'Path escapes configured storage: {target}')
    return target


@dataclass(frozen=True)
class Storage:
    root: Path
    data_root: Path
    cache_root: Path

    @classmethod
    def load(cls, root=None):
        root = Path(root or os.environ.get('UWM_ROOT') or Path(__file__).resolve().parents[2]).resolve()
        if not (root / 'AGENTS.md').is_file() or not (root / 'schemas/run-manifest-v1.schema.json').is_file():
            raise ValueError(f'Not an Physics-Grounded 4D World Model Framework root: {root}')
        config_path = root / 'storage.local.json'
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        if not isinstance(config, dict) or set(config) - {'data_root', 'cache_root'}:
            raise ValueError('storage.local.json accepts only data_root and cache_root')
        def configured(key, default):
            value = config.get(key, str(default))
            if not isinstance(value, str) or not value or not Path(value).expanduser().is_absolute():
                raise ValueError(f'{key} must be an absolute path')
            return Path(value).expanduser().resolve()
        data = configured('data_root', root)
        cache = configured('cache_root', root / 'cache')
        # Cache deletion must never encompass source or retained data.
        if root.is_relative_to(cache) or data.is_relative_to(cache) or cache.is_relative_to(data / 'project'):
            raise ValueError('cache_root must be separate from retained project data and must not contain the repository')
        return cls(root, data, cache)

    def metadata(self, scene):
        return within(self.root, 'project', scene_id(scene))

    def assets(self, scene, category):
        if category not in {'input', 'geometry', 'runs'}:
            raise ValueError(f'Unknown asset category: {category}')
        return within(self.data_root, 'project', scene_id(scene), category)

    def run(self, scene, run_id):
        return within(self.assets(scene, 'runs'), identifier(run_id, run=True))

    def scratch(self, scene, simulation, run_id):
        return within(self.cache_root, scene_id(scene), identifier(simulation), identifier(run_id, run=True))

    def describe(self, scene):
        return {'scene_id': scene_id(scene), 'metadata': str(self.metadata(scene)),
                **{kind: str(self.assets(scene, kind)) for kind in ('input', 'geometry', 'runs')},
                'cache_root': str(self.cache_root)}
