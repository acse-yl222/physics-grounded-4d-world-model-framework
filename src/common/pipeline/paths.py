from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
from pathlib import Path
ROOT = repo_root()
OUTPUT = ROOT / 'output'


def project_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def scene_physics(scene, *parts):
    """output/<scene>/physics/<parts...>，例如 scene_physics('core008', 'scaled_latent')。"""
    return OUTPUT.joinpath(scene, 'physics', *parts)
