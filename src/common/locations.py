"""Separate installed code/resources from a user's scene workspace."""

from importlib.resources import files
import os
from pathlib import Path


def checkout_root():
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file() and (candidate / "src/common").is_dir():
        return candidate
    return None


def workspace_root(root=None):
    value = root or os.environ.get("P4D_ROOT") or os.environ.get("UWM_ROOT") or checkout_root()
    if value is None:
        raise ValueError("Set --root, P4D_ROOT or UWM_ROOT to an existing scene workspace")
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Workspace directory does not exist: {path}")
    return path


def code_path(relative):
    """Resolve a historical src/... code reference independently of scene storage."""
    path = Path(relative)
    if not path.parts or path.parts[0] != "src" or ".." in path.parts:
        raise ValueError("Code paths must start with src/ and remain inside the installed source")
    return Path(__file__).resolve().parents[1].joinpath(*path.parts[1:])


def resource_path(relative):
    """Canonical repository resources in editable mode; bundled resources in a wheel."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Resource paths must be relative")
    checkout = checkout_root()
    if checkout is not None:
        return checkout / path
    return Path(str(files("common").joinpath("resources", *path.parts)))
