"""img2city/webapp/server.py -- local demo web app for the parametric city pipeline.

Run:  img2city webapp   (or: python -m img2city.webapp.server)   -> http://localhost:8000
"""
import math
import re
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from img2city.webapp import areas
from img2city.webapp import jobs
from img2city.webapp import photo
from img2city.webapp import rebuild as rebuild_mod
from img2city.webapp import schema as spec_schema

WEBAPP = Path(__file__).resolve().parent
app = FastAPI(title="parametric city demo")


@app.middleware("http")
async def _no_cache_ui(request, call_next):
    """Never let the browser cache the UI source on this local demo server.

    A stale map.js or style.css after an edit is indistinguishable from a
    broken feature: the page loads and behaves, but the new controls simply
    are not there. Costs nothing over localhost.
    """
    resp = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".css")):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


@app.get("/api/schema")
def api_schema():
    return spec_schema.get_schema()


@app.get("/api/areas")
def api_areas():
    return areas.list_areas()


@app.patch("/api/areas/{name}")
def api_area_rename(name: str, body: dict):
    try:
        display = areas.set_display(name, body.get("display", ""))
    except KeyError:
        raise HTTPException(404, f"unknown area {name}")
    return {"name": name, "display": display}


@app.post("/api/areas/{name}/export")
def api_export(name: str, force: bool = False):
    try:
        glb, mp = areas.ensure_glb(name, force=force)
    except KeyError:
        raise HTTPException(404, f"unknown area {name}")
    except FileNotFoundError as e:
        raise HTTPException(409, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"glb": f"/api/areas/{name}/scene.glb", "map": f"/api/areas/{name}/map.json"}


@app.get("/api/areas/{name}/scene.glb")
def api_glb(name: str):
    glb = areas.CACHE / f"{name}.glb"
    if not glb.exists():
        raise HTTPException(404, "not exported yet")
    return FileResponse(glb, media_type="model/gltf-binary")


@app.get("/api/areas/{name}/map.json")
def api_map(name: str):
    mp = areas.CACHE / f"{name}_map.json"
    if not mp.exists():
        raise HTTPException(404, "not exported yet")
    return FileResponse(mp, media_type="application/json")


@app.get("/api/areas/{name}/buildings/{osmid}")
def api_building(name: str, osmid: int):
    try:
        info = areas.building_info(name, osmid)
        if info.get("spec") is not None:
            info["spec"] = rebuild_mod.effective_spec(name, osmid)
        info["history"] = rebuild_mod.history_depth(name, osmid)
        return info
    except KeyError:
        raise HTTPException(404, f"unknown area {name}")


@app.post("/api/areas/{name}/buildings/{osmid}/rebuild")
def api_rebuild(name: str, osmid: int, body: dict):
    spec = body.get("spec")
    if not isinstance(spec, dict):
        raise HTTPException(422, "body.spec must be an object")
    persist = bool(body.get("persist", False))
    try:
        res = rebuild_mod.rebuild(name, osmid, spec, persist=persist)
    except KeyError:
        raise HTTPException(404, f"unknown area {name}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"glb": f"/api/cache/{res['glb']}",
            "history": rebuild_mod.history_depth(name, osmid)}


@app.post("/api/areas/{name}/buildings/{osmid}/undo")
def api_undo(name: str, osmid: int):
    try:
        spec = rebuild_mod.pop_history(name, osmid)
        if spec is None:
            raise HTTPException(409, "no history to undo")
        res = rebuild_mod.rebuild(name, osmid, spec, persist=True)
        # the persist above pushed the replaced state back on -- pop it so the
        # stack strictly walks backwards
        rebuild_mod.pop_history(name, osmid)
    except KeyError:
        raise HTTPException(404, f"unknown area {name}")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"glb": f"/api/cache/{res['glb']}", "spec": spec,
            "history": rebuild_mod.history_depth(name, osmid)}


@app.get("/api/cache/{fname}")
def api_cache(fname: str):
    p = areas.CACHE / fname
    if "/" in fname or not p.exists():
        raise HTTPException(404, "no such file")
    return FileResponse(p, media_type="model/gltf-binary")


@app.post("/api/photo")
async def api_photo_upload(file: UploadFile):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "image too large")
    suffix = Path(file.filename or "u.png").suffix.lower() or ".png"
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPException(422, "png/jpg/webp only")
    try:
        pid = photo.create(data, suffix)
    except Exception as e:
        raise HTTPException(500, f"prediction/build failed: {e}")
    return photo.info(pid)


@app.get("/api/photo/{pid}")
def api_photo_info(pid: str):
    try:
        return photo.info(pid)
    except KeyError:
        raise HTTPException(404, "no such upload")


@app.get("/api/photo/{pid}/file/{fname}")
def api_photo_file(pid: str, fname: str):
    try:
        pdir = photo.dir_of(pid)
    except KeyError:
        raise HTTPException(404, "no such upload")
    p = pdir / fname
    if "/" in fname or not p.exists():
        raise HTTPException(404, "no such file")
    mt = "model/gltf-binary" if fname.endswith(".glb") else "image/png"
    return FileResponse(p, media_type=mt)


@app.post("/api/photo/{pid}/rebuild")
def api_photo_rebuild(pid: str, body: dict):
    spec = body.get("spec")
    if not isinstance(spec, dict):
        raise HTTPException(422, "body.spec must be an object")
    try:
        glb = photo.rebuild(pid, spec)
    except KeyError:
        raise HTTPException(404, "no such upload")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"glb": f"/api/photo/{pid}/file/{glb.name}"}


@app.post("/api/photo/{pid}/refine")
def api_photo_refine(pid: str, body: dict = None):
    iters = (body or {}).get("iters", 4)
    try:
        j = photo.start_refine(pid, iters=int(iters))
    except KeyError:
        raise HTTPException(404, "no such upload")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"job": j.id}


# A whole building footprint has to fit inside the extent or Overpass returns
# nothing and the run produces an empty scene. Two 4 m and 15 m test extents
# went all the way through the pipeline to an INCOMPLETE verdict before this
# check existed -- free of tokens, but not of time.
MIN_EXTENT_M = 50.0


def extent_m(bbox):
    """(east-west, north-south) size of an [s, w, n, e] bbox, in metres."""
    s, w, n, e = (float(v) for v in bbox)
    return ((e - w) * 111320.0 * math.cos(math.radians((s + n) / 2)),
            (n - s) * 110540.0)


@app.post("/api/generate/resolve")
def api_resolve(body: dict):
    bbox = body.get("bbox")
    if not (isinstance(bbox, list) and len(bbox) == 4):
        raise HTTPException(422, "bbox must be [s,w,n,e]")
    # judge on the same rounded numbers that are shown, or a 49.7 m extent
    # reads back as "50 m, too small" and looks like a bug
    ew, ns = (round(v) for v in extent_m(bbox))
    return {"match": areas.match_bbox(*bbox),
            "extent_m": [ew, ns],
            "too_small": min(ew, ns) < MIN_EXTENT_M}


@app.post("/api/generate/start")
def api_gen_start(body: dict):
    import re as _re
    bbox = body.get("bbox")
    name = body.get("name") or ""
    if not (isinstance(bbox, list) and len(bbox) == 4):
        raise HTTPException(422, "bbox must be [s,w,n,e]")
    if not _re.fullmatch(r"[a-z0-9_\-]{3,40}", name):
        raise HTTPException(422, "name must be [a-z0-9_-]{3,40}")
    ew, ns = (round(v) for v in extent_m(bbox))
    if min(ew, ns) < MIN_EXTENT_M:
        raise HTTPException(422, "extent is %d x %d m; no building footprint "
                                 "fits in anything under %d m, so the run would "
                                 "find nothing" % (ew, ns, MIN_EXTENT_M))
    display = (body.get("display") or "").strip()[:60]
    if not display.isascii():
        raise HTTPException(422, "display name must be ASCII: it is served by "
                                 "/api/areas and shown as the area card title, "
                                 "and the site is English-only")
    meta = {}
    if display:
        meta["display"] = display
    if body.get("skip_refine"):
        meta["skip_refine"] = True
    try:
        j = jobs.create("generate", name, bbox=[float(v) for v in bbox],
                        meta=meta or None)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    if display:
        d = areas.DATA / name
        d.mkdir(parents=True, exist_ok=True)
        import json as _json
        (d / "display.json").write_text(
            _json.dumps({"name": display}, ensure_ascii=False))
    j.start_quote()
    return {"job": j.id}


@app.get("/api/jobs")
def api_jobs():
    return [j.to_dict(log_lines=0) for j in jobs.all_jobs()]


@app.get("/api/jobs/active")
def api_jobs_active():
    return {"count": jobs.active_count()}


@app.post("/api/jobs/{jid}/resume")
def api_job_resume(jid: str):
    j = jobs.get(jid)
    if not j:
        raise HTTPException(404, "no such job")
    try:
        j.resume()
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@app.get("/api/jobs/{jid}")
def api_job(jid: str):
    j = jobs.get(jid)
    if not j:
        raise HTTPException(404, "no such job")
    return j.to_dict()


@app.post("/api/jobs/{jid}/confirm")
def api_job_confirm(jid: str):
    j = jobs.get(jid)
    if not j:
        raise HTTPException(404, "no such job")
    if j.status != "awaiting_confirm":
        raise HTTPException(409, f"job is {j.status}")
    try:
        j.confirm_run()
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@app.post("/api/jobs/{jid}/cancel")
def api_job_cancel(jid: str):
    j = jobs.get(jid)
    if not j:
        raise HTTPException(404, "no such job")
    j.cancel()
    return {"ok": True}


UI = WEBAPP / "ui"


def _stamp(html):
    """Pin every local js/css/vendor URL to that file's mtime.

    no-store stops the browser caching from here on, but it cannot evict what
    is already cached: a page quietly running last week's map.js looks exactly
    like a feature that was never built, which cost real debugging time. A
    changed file now gets a changed URL, so the browser has no stale copy to
    serve and no hard refresh is needed.
    """
    def one(m):
        attr, path = m.group(1), m.group(2)
        f = UI / path.lstrip("/")
        if not f.is_file():
            return m.group(0)
        return '%s="%s?v=%d"' % (attr, path, f.stat().st_mtime)
    return re.sub(r'(src|href)="(/(?:js|css|vendor)/[^"?]+)"', one, html)


@app.get("/", include_in_schema=False)
@app.get("/{page}.html", include_in_schema=False)
def ui_page(page="index"):
    f = UI / ("%s.html" % page)
    if not f.is_file():
        raise HTTPException(404, "no such page")
    return HTMLResponse(_stamp(f.read_text()))


# everything else (js, css, vendor, assets) still comes straight off disk
app.mount("/", StaticFiles(directory=UI, html=True), name="ui")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="img2city demo web app")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
