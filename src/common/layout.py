"""Locate the checkout independently of a module's depth."""

from pathlib import Path

from .locations import code_path, workspace_root


def repo_root():
    return workspace_root()


def agent_src():
    return code_path("src/urban_geometry/agent")


def authoring_path(relative=""):
    from .storage import Storage

    path = Path(relative)
    if path.parts and path.parts[0] == "src":
        return agent_src().joinpath(*path.parts[1:])
    return Storage.load().assets("south_ken", "geometry") / "authoring" / path


def expansion_run_dir(run):
    """Disposable directory shared by the expansion build, verify and render scripts."""
    from .storage import Storage

    return Storage.load().scratch("south_ken", "geometry", run)


def snapshot_key(path):
    """Name an expansion input src/... or project/..., wherever code and data are installed."""
    from .storage import Storage

    path = Path(path)
    code = code_path("src")
    if path.is_relative_to(code):
        return (Path("src") / path.relative_to(code)).as_posix()
    if path.is_relative_to(authoring_path()):
        return path.relative_to(Storage.load().data_root).as_posix()
    raise ValueError(f"Not an expansion code or authoring input: {path}")


def scene_input(scene, *parts):
    from .storage import Storage, within

    return within(Storage.load().assets(scene, "input"), *parts)
