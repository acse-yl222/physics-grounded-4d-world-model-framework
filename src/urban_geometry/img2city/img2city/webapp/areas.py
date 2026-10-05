"""img2city/webapp/areas.py -- registry over the generated areas (config.DATA_DIR/*): which generated areas exist,
bbox matching for the map page, and cached headless glb export."""
import json
import math
import subprocess
import threading
import time
from pathlib import Path

from img2city import config

HARNESS = config.PROJECT_ROOT          # cwd for stage subprocesses
DATA = config.DATA_DIR
CACHE = config.CACHE_DIR / "webapp"
BLENDER = config.BLENDER_BIN
EXPORT_PY = Path(__file__).resolve().parent / "export_glb.py"
CACHE.mkdir(parents=True, exist_ok=True)   # regenerable: glbs, pick maps, job records

_export_locks = {}
_locks_guard = threading.Lock()


def _lock_for(name):
    with _locks_guard:
        return _export_locks.setdefault(name, threading.Lock())


def _blend_of(d):
    cands = sorted(d.glob("*_textured.blend"))
    return cands[0] if cands else None


def _display_of(d):
    p = d / "display.json"
    if p.exists():
        try:
            return json.loads(p.read_text()).get("name") or None
        except Exception:
            pass
    return None


def set_display(name, display):
    """Human-readable name for an area; stored beside the data, the
    directory itself is never renamed (pipeline paths depend on it)."""
    d = area_dir(name)
    display = (display or "").strip()[:60]
    if display:
        (d / "display.json").write_text(json.dumps({"name": display},
                                                   ensure_ascii=False))
    elif (d / "display.json").exists():
        (d / "display.json").unlink()
    return display or None


def list_areas():
    out = []
    for d in sorted(DATA.iterdir()):
        bj = d / "buildings.json"
        if not d.is_dir() or not bj.exists():
            continue
        try:
            doc = json.loads(bj.read_text())
        except Exception:
            continue
        anchor = doc.get("anchor") or {}
        bbox = anchor.get("bbox")
        if not bbox:
            continue
        metas = doc.get("buildings", [])
        blend = _blend_of(d)
        report = d / "pipeline_report.json"
        verdict = None
        if report.exists():
            try:
                verdict = json.loads(report.read_text()).get("verdict")
            except Exception:
                pass
        region = None
        rj = d / "region.json"
        if rj.exists():
            try:
                region = json.loads(rj.read_text()).get("region")
            except Exception:
                pass
        specs = len(list(d.glob("buildings/*/spec.json")))
        glb = CACHE / f"{d.name}.glb"
        out.append({
            "name": d.name,
            "display": _display_of(d),
            "bbox": bbox,
            "center": [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2],
            "region": region,
            "buildings": len(metas),
            "specs": specs,
            "verdict": verdict,
            "has_blend": blend is not None,
            "blend": blend.name if blend else None,
            "glb_ready": glb.exists() and blend is not None
                         and glb.stat().st_mtime >= blend.stat().st_mtime,
            "preview": blend is not None and specs == 0,   # LoD1 white boxes only
            "stale": d.name.endswith("_stale"),
        })
    return out


def area_dir(name):
    d = DATA / name
    if not d.is_dir() or not (d / "buildings.json").exists() or "/" in name:
        raise KeyError(name)
    return d


def match_bbox(s, w, n, e):
    """Existing area whose anchor bbox covers roughly the same ground.
    Centre within 25% of the requested span and spans within 2x either way."""
    lat_c, lng_c = (s + n) / 2, (w + e) / 2
    span_lat = n - s
    best = None
    for a in list_areas():
        if a["stale"] or not a["has_blend"]:
            continue
        ab = a["bbox"]
        a_lat_c, a_lng_c = (ab[0] + ab[2]) / 2, (ab[1] + ab[3]) / 2
        a_span = ab[2] - ab[0]
        if abs(a_lat_c - lat_c) > 0.25 * max(span_lat, a_span):
            continue
        klng = math.cos(math.radians(lat_c))
        if abs(a_lng_c - lng_c) * klng > 0.25 * max(span_lat, a_span):
            continue
        r = a_span / span_lat if span_lat else 99
        if not (0.5 <= r <= 2.0):
            continue
        if best is None or a["specs"] > best["specs"]:
            best = a
    return best


def ensure_glb(name, force=False):
    """Cached headless export; returns (glb_path, map_path). Blocking."""
    d = area_dir(name)
    blend = _blend_of(d)
    if blend is None:
        raise FileNotFoundError(f"{name}: no *_textured.blend yet")
    CACHE.mkdir(parents=True, exist_ok=True)
    glb = CACHE / f"{name}.glb"
    mp = CACHE / f"{name}_map.json"
    with _lock_for(name):
        fresh = (glb.exists() and mp.exists()
                 and glb.stat().st_mtime >= blend.stat().st_mtime)
        if fresh and not force:
            return glb, mp
        t0 = time.time()
        r = subprocess.run(
            [BLENDER, "-b", str(blend), "--python", str(EXPORT_PY), "--",
             "--out", str(glb), "--map", str(mp), "--animations"],
            capture_output=True, text=True, timeout=900)
        if "EXPORT_OK" not in r.stdout:
            raise RuntimeError(
                f"glb export failed for {name}:\n{r.stdout[-2000:]}\n{r.stderr[-1000:]}")
        print(f"[areas] exported {name} in {time.time()-t0:.0f}s")
    return glb, mp


def building_info(name, osmid):
    """Merged per-building document: meta + spec + provenance extras."""
    d = area_dir(name)
    doc = json.loads((d / "buildings.json").read_text())
    meta = next((m for m in doc.get("buildings", []) if m["id"] == osmid), None)
    bdir = d / "buildings" / str(osmid)
    out = {"osmid": osmid, "meta": meta, "spec": None, "typology": None,
           "gate": None, "refined": False}
    sp = bdir / "spec.json"
    if sp.exists():
        try:
            out["spec"] = json.loads(sp.read_text())
        except Exception:
            pass
    for key, fn in (("typology", "typology.json"), ("gate", "gate.json")):
        p = bdir / fn
        if p.exists():
            try:
                out[key] = json.loads(p.read_text())
            except Exception:
                pass
    out["refined"] = (bdir / "refine" / "result.json").exists()
    out["path"] = "obb"
    pl = d / "agent_placements.json"
    if pl.exists():
        try:
            e = next((x for x in json.loads(pl.read_text()) if x["id"] == osmid), None)
            if e and "poly" in e:
                out["path"] = "poly"
        except Exception:
            pass
    return out
