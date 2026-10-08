from common.locations import checkout_root, workspace_root
import os
from pathlib import Path

ROOT = (
    workspace_root()
    if os.environ.get("P4D_ROOT") or os.environ.get("UWM_ROOT")
    else checkout_root()
)


def project_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (workspace_root() / path).resolve()


def scene_physics(scene, *parts):
    """Legacy convenience function; computation belongs in the current cache trial."""
    from common.runtime import trial_root
    from common.storage import within

    return within(trial_root(scene, "pipeline"), "physics", *parts)
