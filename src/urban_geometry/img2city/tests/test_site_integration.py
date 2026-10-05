"""Integration tests for the demo web app, run against a LIVE server
(`python -m img2city.webapp.server`, http://localhost:8000) with real generated areas
on disk. The whole module skips cleanly when the server is not running, so
the unit suite and CI stay fast; run it locally before demos:

    python -m pytest tests/test_site_integration.py -v

Covers: pages/assets, i18n key coverage, English-only output, area registry
and rename, pick-map <-> glb consistency, building info, the full edit loop
(preview / save / undo semantics against the real Blender worker), schema
flags, bbox resolve, jobs API, the photo-upload flow, and input guards.
"""
import json
import os
import re
import shutil
import struct
import urllib.error
import urllib.request

import pytest

from img2city.config import DATA_DIR, PACKAGE_DIR

BASE = os.environ.get("IMG2CITY_TEST_BASE", "http://localhost:8000").rstrip("/")

DATA = str(DATA_DIR)
TEST_AREA = "city_rah"
TEST_BID = 55471410


def _up():
    try:
        urllib.request.urlopen(BASE + "/api/areas", timeout=3)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _up(), reason="webapp server not running")


def get(path, timeout=300):
    return urllib.request.urlopen(BASE + path, timeout=timeout)


def getj(path, timeout=300):
    return json.loads(get(path, timeout).read())


def post(path, body=None, timeout=300, method="POST"):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body or {}).encode(),
        headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def glb_stats(raw):
    ln, = struct.unpack("<I", raw[12:16])
    doc = json.loads(raw[20:20 + ln])
    pos = {p["attributes"]["POSITION"] for m in doc["meshes"]
           for p in m["primitives"] if "POSITION" in p["attributes"]}
    verts = sum(doc["accessors"][i]["count"] for i in pos)
    names = [n.get("name", "") for n in doc.get("nodes", [])]
    return verts, names


def _spec():
    p = os.path.join(DATA, TEST_AREA, "buildings", str(TEST_BID), "spec.json")
    if not os.path.exists(p):
        pytest.skip(f"test area {TEST_AREA} not on disk")
    return json.load(open(p)), p


# ---------------- pages & static integrity

PAGES = ("/", "/viewer.html", "/map.html", "/upload.html", "/jobs.html")
ASSETS = ("/js/i18n.js", "/js/viewer.js", "/js/panel.js", "/js/map.js",
          "/js/upload.js", "/js/jobcard.js", "/js/topbar.js", "/css/style.css",
          "/vendor/three.module.min.js", "/vendor/GLTFLoader.js",
          "/utils/BufferGeometryUtils.js")


@pytest.mark.parametrize("path", PAGES + ASSETS)
def test_asset_served(path):
    assert len(get(path).read()) > 100


def test_i18n_keys_cover_everything_used():
    ui = os.path.join(PACKAGE_DIR, "webapp", "ui")
    keys = set(re.findall(r"'([\w.]+)':\s*'", open(os.path.join(ui, "js", "i18n.js")).read()))
    used = set()
    for root, _, files in os.walk(ui):
        if "vendor" in root:
            continue
        for f in files:
            if f == "i18n.js" or not f.endswith((".html", ".js")):
                continue
            src = open(os.path.join(root, f)).read()
            used |= set(re.findall(r'data-i18n="([\w.]+)"', src))
            used |= set(re.findall(r"(?<![\w])t\('([\w.]+)'", src))
    static = {u for u in used if "." in u
              and not u.startswith(("status.", "stage.", "kind."))}
    assert static <= keys, f"used but undefined: {sorted(static - keys)[:6]}"


def test_everything_served_is_english():
    # /api/areas carries user-typed display names -- one of them was CJK and
    # rendered as an area card title, which this test used to miss
    for p in PAGES + ("/js/i18n.js", "/api/schema", "/api/areas", "/api/jobs"):
        body = get(p).read().decode("utf-8", errors="ignore")
        assert not re.search(r"[一-鿿]", body), p


# ---------------- areas & viewer data

def test_areas_registry_fields():
    a = getj("/api/areas")
    assert a, "no areas on disk"
    need = {"name", "display", "bbox", "center", "buildings", "specs",
            "glb_ready", "preview", "stale"}
    assert need <= set(a[0].keys())


def test_area_rename_roundtrip():
    orig = next((x["display"] for x in getj("/api/areas")
                 if x["name"] == TEST_AREA), None)
    r = post(f"/api/areas/{TEST_AREA}", {"display": "integration temp"},
             method="PATCH")
    assert r["display"] == "integration temp"
    r = post(f"/api/areas/{TEST_AREA}", {"display": orig or ""}, method="PATCH")
    assert r["display"] == orig


def test_pick_map_matches_glb_nodes():
    ready = [x["name"] for x in getj("/api/areas") if x["glb_ready"]]
    if not ready:
        pytest.skip("no exported area glb")
    area = ready[0]
    mapped = set(getj(f"/api/areas/{area}/map.json")["buildings"].keys())
    _, names = glb_stats(get(f"/api/areas/{area}/scene.glb").read())
    present = mapped & {n for n in names if n.startswith(("Agent_", "Bldg_"))}
    assert len(present) >= 0.95 * len(mapped)


def test_building_info_and_404():
    d = getj(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}")
    assert d["spec"] and d["path"] in ("poly", "obb") and "history" in d
    with pytest.raises(urllib.error.HTTPError) as e:
        getj("/api/areas/no_such_area/buildings/1")
    assert e.value.code == 404


# ---------------- the edit loop (real Blender worker)

def test_preview_rebuild_changes_geometry_without_persisting():
    spec, path = _spec()
    before = open(path, "rb").read()
    taller = json.loads(json.dumps(spec))
    taller["masses"] = [dict(taller["masses"][0],
                             floors=taller["masses"][0]["floors"] + 4)]
    r = post(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}/rebuild",
             {"spec": taller, "persist": False})
    v_tall, _ = glb_stats(get(r["glb"]).read())
    b = post(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}/rebuild",
             {"spec": spec, "persist": False})
    v_base, _ = glb_stats(get(b["glb"]).read())
    assert v_tall > v_base + 1000, "extra floors must add window geometry"
    assert open(path, "rb").read() == before, "preview must not write spec.json"


def test_save_then_undo_restores_spec():
    spec, path = _spec()
    edited = json.loads(json.dumps(spec))
    edited["masses"] = [dict(edited["masses"][0],
                             floors=edited["masses"][0]["floors"] + 1)]
    r = post(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}/rebuild",
             {"spec": edited, "persist": True})
    assert r["history"] >= 1
    now = json.load(open(path))
    assert now["masses"][0]["floors"] == edited["masses"][0]["floors"]
    post(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}/undo")
    back = json.load(open(path))
    assert back["masses"][0]["floors"] == spec["masses"][0]["floors"]


def test_rebuild_input_guards():
    with pytest.raises(urllib.error.HTTPError) as e:
        post(f"/api/areas/{TEST_AREA}/buildings/{TEST_BID}/rebuild",
             {"spec": "not an object"})
    assert e.value.code == 422


def test_schema_editor_flags():
    sc = getj("/api/schema")
    fields = {f["path"]: f for g in sc["groups"] for f in g["fields"]}
    assert fields["floors"].get("live") and fields["floors"].get("masses_override")
    assert fields["terrace.balcony"].get("poly_drop")


# ---------------- map & jobs

def test_bbox_resolve_hit_and_miss():
    # any area on disk with a .blend must resolve to itself
    live = [a for a in getj("/api/areas") if a["has_blend"] and not a["stale"]]
    if not live:
        pytest.skip("no exported area on disk")
    hit = post("/api/generate/resolve", {"bbox": live[0]["bbox"]})["match"]
    assert hit and hit["name"] == live[0]["name"]
    miss = post("/api/generate/resolve", {"bbox": [40.0, 0.0, 40.01, 0.01]})["match"]
    assert miss is None


def test_generate_start_rejects_bad_name():
    with pytest.raises(urllib.error.HTTPError) as e:
        post("/api/generate/start",
             {"bbox": [51, 0, 51.01, 0.01], "name": "BAD NAME!"})
    assert e.value.code == 422


def test_jobs_api():
    assert isinstance(getj("/api/jobs"), list)
    assert isinstance(getj("/api/jobs/active")["count"], int)
    with pytest.raises(urllib.error.HTTPError) as e:
        getj("/api/jobs/zzzzzz")
    assert e.value.code == 404


# ---------------- photo flow

def _multipart(filename, content, ctype):
    b = "IntegrationBoundary"
    body = (f'--{b}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'
            ).encode() + content + f"\r\n--{b}--\r\n".encode()
    return urllib.request.Request(
        BASE + "/api/photo", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={b}"})


def test_photo_upload_edit_and_cleanup():
    img_path = os.path.join(DATA, "business_school", "satellite.png")
    if not os.path.exists(img_path):
        pytest.skip("no sample image on disk")
    d = json.loads(urllib.request.urlopen(
        _multipart("t.png", open(img_path, "rb").read(), "image/png"),
        timeout=300).read())
    try:
        v0, _ = glb_stats(get(f"/api/photo/{d['id']}/file/{d['glb']}").read())
        edited = dict(d["desc"])
        edited["masses"] = [dict(m, floors=m["floors"] + 3)
                            for m in edited["masses"]]
        r = post(f"/api/photo/{d['id']}/rebuild", {"spec": edited})
        v1, _ = glb_stats(get(r["glb"]).read())
        assert v1 != v0
    finally:
        shutil.rmtree(os.path.join(DATA, "web_uploads", d["id"]),
                      ignore_errors=True)


def test_photo_rejects_non_image():
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(
            _multipart("t.exe", b"xx", "application/octet-stream"), timeout=60)
    assert e.value.code == 422


def test_cache_endpoint_blocks_traversal():
    with pytest.raises(urllib.error.HTTPError) as e:
        get("/api/cache/..%2F..%2Fserver.py")
    assert e.value.code == 404
