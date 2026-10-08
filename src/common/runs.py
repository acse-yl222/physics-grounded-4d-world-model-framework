"""Retain a verified run without losing its trial workspace or overwriting history."""

import json
import os
from pathlib import Path
import shutil
import tempfile
from .contract import validate, asset_references
from .storage import scene_id


def promote(storage, source):
    source = Path(source).resolve()
    validate(source / "manifest.json")
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Only complete runs can be retained")
    if manifest["scene_id"] != scene_id(manifest["scene_id"]):
        raise ValueError("Export with the canonical scene ID before retaining a run")
    destination = storage.run(manifest["scene_id"], manifest["run_id"])
    if destination == source or destination.is_relative_to(source):
        raise ValueError("Source and destination must be separate run directories")
    # Only manifest-declared assets are promoted; logs/checkpoints stay in the trial workspace.
    assets = set().union(*(asset_references(layer) for layer in manifest["layers"])) | {
        item["asset"] for item in manifest.get("artifacts", [])
    }
    if any((source / asset).is_symlink() for asset in assets):
        raise ValueError("Materialize linked assets before retaining the run")
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.parent / f".{destination.name}.lock"
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    staging = None
    try:
        os.close(descriptor)
        if destination.exists():
            raise FileExistsError(f"Run already exists: {destination}")
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
        for rel in sorted(assets | {"manifest.json"}):
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, target)
        validate(staging / "manifest.json")
        # Lock serializes framework writers. Atomic rename exposes only a fully checked run.
        staging.rename(destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()
    return destination


def promote_bundle(storage, source):
    """Retain all declared runs, then expose a validated view; never replace a view."""
    from .catalog import schema_check, view as check_view
    from .storage import identifier

    source = Path(source).resolve()
    bundle = json.loads((source / "bundle.json").read_text())
    scene = scene_id(bundle["scene_id"])
    view_id = identifier(bundle["view_id"])
    schema_check(bundle["view"], "view-v1.schema.json")
    schema_check(bundle["project"], "project-v1.schema.json")
    if bundle["view"]["scene_id"] != scene or bundle["project"]["scene_id"] != scene:
        raise ValueError("Bundle scene mismatch")
    if set(bundle["runs"]) != set(bundle["view"]["runs"]):
        raise ValueError("Bundle run list differs from view")
    metadata = storage.metadata(scene)
    view_path = metadata / "views" / f"{view_id}.json"
    if view_path.exists():
        raise FileExistsError(view_path)
    for run_id in bundle["runs"]:
        identifier(run_id, run=True)
        path = source / run_id / "manifest.json"
        validate(path)
        manifest = json.loads(path.read_text())
        if manifest["scene_id"] != scene or manifest["run_id"] != run_id:
            raise ValueError("Bundle run identity mismatch")
        if storage.run(scene, run_id).exists():
            raise FileExistsError(storage.run(scene, run_id))
    # Preflight coordinate/frame and layer references before copying any retained data.
    for layer in bundle["view"]["layers"]:
        m = json.loads((source / layer["run_id"] / "manifest.json").read_text())
        if layer["layer_id"] not in {x["id"] for x in m["layers"]}:
            raise ValueError("Unknown bundle layer")
        if m["spatial"]["origin"] != bundle["project"]["spatial"]["origin"]:
            raise ValueError("Bundle origins differ")
    created = []
    new_project = False
    created_view = False
    try:
        for run_id in bundle["runs"]:
            created.append(promote(storage, source / run_id))
        metadata.mkdir(parents=True, exist_ok=True)
        project_path = metadata / "project.json"
        if not project_path.exists():
            document = dict(bundle["project"], default_view=view_id)
            with project_path.open("x") as f:
                json.dump(document, f, indent=2)
            new_project = True
        view_path.parent.mkdir(parents=True, exist_ok=True)
        with view_path.open("x") as f:
            created_view = True
            json.dump(bundle["view"], f, indent=2)
        check_view(storage, scene, view_id)
        refresh_catalog(storage)
    except Exception:
        if created_view:
            view_path.unlink()
        if new_project:
            (metadata / "project.json").unlink()
        for path in created:
            shutil.rmtree(path)
        raise
    return view_path


def refresh_catalog(storage):
    entries = []
    for path in sorted((storage.root / "project").glob("*/project.json")):
        document = json.loads(path.read_text())
        entries.append(
            {
                "scene_id": document["scene_id"],
                "title": document["title"],
                "views": sorted(p.stem for p in (path.parent / "views").glob("*.json")),
            }
        )
    target = storage.root / "project/index.json"
    default = json.loads(target.read_text()).get("default") if target.exists() else None
    if default not in {entry["scene_id"] for entry in entries}:
        default = entries[0]["scene_id"] if entries else None
    data = json.dumps({"default": default, "scenes": entries}, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", dir=target.parent, prefix=".catalog-", delete=False
    ) as handle:
        handle.write(data)
        tmp = Path(handle.name)
    tmp.replace(target)
