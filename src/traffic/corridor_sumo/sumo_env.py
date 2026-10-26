"""Locate a SUMO installation (``SUMO_HOME`` or the ``eclipse-sumo`` wheel)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path


@cache
def sumo_home() -> Path:
    """SUMO_HOME from the environment, else the ``sumo`` package of eclipse-sumo."""
    env = os.environ.get("SUMO_HOME")
    if env and (Path(env) / "tools").is_dir():
        return Path(env)
    try:
        import sumo  # eclipse-sumo wheel
    except ImportError as exc:
        raise RuntimeError(
            "SUMO not found: set SUMO_HOME or `python3 -m pip install eclipse-sumo`"
        ) from exc
    return Path(sumo.SUMO_HOME)


def binary(name: str) -> str:
    """Path of a SUMO executable such as ``netconvert`` or ``sumo``."""
    candidate = sumo_home() / "bin" / name
    if candidate.is_file():
        return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f"SUMO binary {name!r} not found under {sumo_home()}/bin or PATH")


def tool(*parts: str) -> Path:
    """Path of a script in ``$SUMO_HOME/tools`` (e.g. ``randomTrips.py``)."""
    return sumo_home().joinpath("tools", *parts)


def sumolib():
    """Import ``sumolib`` from ``$SUMO_HOME/tools``."""
    tools = str(tool())
    if tools not in sys.path:
        sys.path.append(tools)
    import sumolib as module

    return module


@cache
def version() -> str:
    out = subprocess.run([binary("sumo"), "--version"], capture_output=True, text=True, check=True)
    first = out.stdout.strip().splitlines()[0]
    return first.replace("Eclipse SUMO sumo ", "").strip()


def run(cmd, log: Path | None = None, **kw) -> None:
    """Run a SUMO command, echoing it, teeing output to ``log`` when given."""
    cmd = [str(c) for c in cmd]
    print("+", " ".join(cmd), flush=True)
    env = {**os.environ, "SUMO_HOME": str(sumo_home())}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False, **kw)
    if log is not None:
        with log.open("a") as handle:
            handle.write("$ " + " ".join(cmd) + "\n" + result.stdout + result.stderr + "\n")
    if result.returncode != 0:
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-20:])
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({result.returncode}):\n{tail}")
