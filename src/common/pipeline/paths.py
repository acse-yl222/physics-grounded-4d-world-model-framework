import os
from pathlib import Path

from common.locations import checkout_root, workspace_root

ROOT = (
    workspace_root()
    if os.environ.get("P4D_ROOT") or os.environ.get("UWM_ROOT")
    else checkout_root()
)


def project_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (workspace_root() / path).resolve()
