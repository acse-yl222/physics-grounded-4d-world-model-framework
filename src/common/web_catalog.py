"""Combine published entries with explicitly selected local presentation runs."""

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

from .locations import resource_path
from .storage import identifier, scene_id, within

LOG = logging.getLogger(__name__)


def local_entry(storage, path):
    entry = json.loads(path.read_text())
    if not isinstance(entry, dict):
        raise ValueError("Scene entry must be an object")
    scene = scene_id(path.parents[1].name)
    if not entry.get("enabled", True):
        return None
    run_id = identifier(entry["run_id"], run=True)
    base = storage.run(scene, run_id)
    manifest_path = within(base, "manifest.json")
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError("Presentation manifest must be an object")
    if (
        manifest.get("status") != "complete"
        or manifest.get("scene_id") != scene
        or manifest.get("run_id") != run_id
        or manifest.get("simulation") != "city_presentation"
    ):
        return None
    artifacts, layers = manifest.get("artifacts", []), manifest.get("layers", [])
    if not isinstance(artifacts, list) or not isinstance(layers, list):
        raise ValueError("Presentation assets must be lists")
    if not all(isinstance(asset, dict) for asset in artifacts + layers):
        raise ValueError("Presentation asset must be an object")
    descriptor = next((a for a in artifacts if a["id"] == "city_scene"), None)
    if not descriptor:
        return None
    # A removed model/field must not leave a clickable but broken scene card.
    assets = [a["asset"] for a in artifacts + layers]
    for asset in assets:
        if (
            not isinstance(asset, str)
            or Path(asset).is_absolute()
            or ".." in Path(asset).parts
            or "\\" in asset
        ):
            raise ValueError("Invalid presentation asset path")
        if not within(base, asset).is_file():
            return None
    preferences = entry.get("launch", {})
    if set(preferences) - {"pose", "fields", "mode", "phase", "step", "lite"}:
        raise ValueError("Unsupported scene launch preference")
    for key in ["title", "description"]:
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise ValueError("Missing scene display text")
    query = urlencode({"scene": scene, "run": run_id, **preferences})
    return {
        "scene_id": scene,
        "title": entry["title"],
        "tag": entry.get("tag", "Urban environment"),
        "description": entry["description"],
        "viewer_url": "src/visualization/legacy/viewer/3d/?" + query,
        "resource_ids": [],
    }


def load_web_catalog(storage):
    catalog = json.loads(resource_path("src/visualization/public-scenes.json").read_text())
    for item in catalog["scenes"]:
        if not storage.assets(item["scene_id"], "runs").is_dir():
            item["viewer_url"] = (
                catalog["published_site"].rstrip("/")
                + "/"
                + item["viewer_url"].removeprefix("src/visualization/legacy/")
            )
    known = {item["scene_id"] for item in catalog["scenes"]}
    for path in sorted((storage.root / "project").glob("*/configs/web_entry.json")):
        try:
            item = local_entry(storage, path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            LOG.warning(
                "Skipping invalid local scene entry %s: %s",
                path.parent.parent.name,
                type(error).__name__,
            )
            continue
        if item is not None and item["scene_id"] not in known:
            catalog["scenes"].append(item)
            known.add(item["scene_id"])
    return catalog
