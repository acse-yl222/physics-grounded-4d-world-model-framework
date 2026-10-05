"""The Blender-side parts kit.

`components.py` (core parametric parts + `build_building(desc)`) and
`parts_learned.py` (region-dialect parts authored by `img2city.library.grow`)
are NOT imported by the host process: they run INSIDE Blender, where `bpy`
and `mathutils` exist.  The host reads their source text, concatenates it
(core first, learned parts after so they register via `PARTS.update`) and
ships it over the BlenderMCP socket or into a headless `blender --python`
job.  This module is the single place that knows where those files live.

`spec_dialect.json` holds the learned schema lines (data, not source) and
`vendor/bpypolyskel` is the straight-skeleton roof engine, imported inside
Blender via the injected `_VENDOR_DIR`.
"""
from __future__ import annotations
import os
import ast
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent
COMPONENTS_PY = KIT_DIR / "components.py"
PARTS_LEARNED_PY = Path(os.environ.get("IMG2CITY_LEARNED_PARTS", KIT_DIR / "parts_learned.py"))
SPEC_DIALECT_JSON = Path(os.environ.get("IMG2CITY_SPEC_DIALECT", KIT_DIR / "spec_dialect.json"))
VENDOR_DIR = KIT_DIR / "vendor"


def load_kit_src() -> str:
    """components.py + parts_learned.py as one Blender-executable source blob,
    prefixed with the absolute vendor path (exec'd source has no __file__)."""
    src = COMPONENTS_PY.read_text()
    # LEARNED parts are concatenated AFTER the core kit so they see box()/MAT/
    # PARTS and register themselves.  Additive only -- library.grow's gate 0
    # rejects any learned definition whose name already exists in
    # components.py, because a later def would silently SHADOW the core part.
    if PARTS_LEARNED_PY.exists():
        src += "\n\n" + PARTS_LEARNED_PY.read_text()
    return ("_VENDOR_DIR = %r\n" % str(VENDOR_DIR)) + src


def kit_sources() -> list[str]:
    """Paths of the kit source files that exist (for AST audits / vocabulary
    mining)."""
    return [str(p) for p in (COMPONENTS_PY, PARTS_LEARNED_PY) if os.path.exists(p)]


def material_names() -> list[str]:
    """Read the actual palette without importing Blender-side code."""
    for node in ast.parse(COMPONENTS_PY.read_text()).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "MAT_SPEC" for t in node.targets):
            return sorted(ast.literal_eval(node.value))
    raise RuntimeError("Kit MAT_SPEC palette is missing")
