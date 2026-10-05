"""img2city/webapp/rebuild.py -- server-side single-building rebuild orchestration.

Takes the edited spec from the panel, refreshes the building's
agent_placements.json entry (poly_params for polygon-footprint buildings,
shop flags from shops.json, photo palette from facade_colors), runs the
headless Blender rebuild (rebuild_bpy.py) against the packed .blend, and
persists spec.json + agent_placements.json on success.
"""
import json
import subprocess
import tempfile
import time
from pathlib import Path

from img2city import config
from img2city.kit import load_kit_src
from img2city.webapp import areas

OBB_FACE = ["-y", "+x", "+y", "-x"]

_city_generate = None

_worker = None
_worker_lock = None


def _worker_build(job_path, timeout=180):
    """Send one job to the resident Blender worker (start/restart on demand)."""
    global _worker, _worker_lock
    import threading
    if _worker_lock is None:
        _worker_lock = threading.Lock()
    with _worker_lock:
        if _worker is None or _worker.poll() is not None:
            src_p = areas.CACHE / "_components_src.py"
            src_p.write_text(components_src())
            _worker = subprocess.Popen(
                [areas.BLENDER, "-b", "--python",
                 str(Path(__file__).parent / "rebuild_bpy.py"),
                 "--", "--worker", "--components", str(src_p)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            for line in _worker.stdout:
                if "WORKER_READY" in line:
                    break
        _worker.stdin.write(job_path + "\n")
        _worker.stdin.flush()
        import time as _t
        deadline = _t.time() + timeout
        for line in _worker.stdout:
            if line.startswith("DONE "):
                return None
            if line.startswith("FAIL "):
                return line[5:].strip()
            if _t.time() > deadline:
                break
        try:
            _worker.kill()
        except Exception:
            pass
        _worker = None
        return "worker died or timed out"


def _cg():
    """Lazy import: city_generate drags in torch/dreamsim; only needed here."""
    global _city_generate
    if _city_generate is None:
        from img2city.city import generate as city_generate
        _city_generate = city_generate
    return _city_generate


def components_src():
    """The Blender-side kit source (img2city.kit) without importing generate."""
    return load_kit_src()


def _shop_context(out_dir, osmid, entry):
    sj = out_dir / "shops.json"
    if not sj.exists():
        return
    try:
        units = json.loads(sj.read_text())["units"]
    except Exception:
        return
    ek = sorted({u["edge"] for u in units if u["host"] == osmid})
    if not ek:
        return
    if "poly" in entry:
        entry["shop_edges"] = ek
    else:
        entry["desc"]["shop_faces"] = sorted({OBB_FACE[k] for k in ek if k < 4})


def effective_spec(area, osmid):
    """spec.json + assembly-time palette injection, as the panel should see it."""
    d = areas.area_dir(area)
    sp = d / "buildings" / str(osmid) / "spec.json"
    if not sp.exists():
        return None
    spec = json.loads(sp.read_text())
    if "colors" not in spec:
        try:
            from img2city.building.facade_colors import colors_for
            c = colors_for(str(d), osmid)
            if c:
                spec["colors"] = c
                spec["_colors_measured"] = True
        except Exception:
            pass
    return spec


HISTORY_CAP = 20


def _push_history(bdir):
    """Current saved spec -> spec_history/<epoch>.json (newest-20 kept)."""
    sp = bdir / "spec.json"
    if not sp.exists():
        return
    hd = bdir / "spec_history"
    hd.mkdir(exist_ok=True)
    (hd / f"{int(time.time()*1000)}.json").write_text(sp.read_text())
    for old in sorted(hd.glob("*.json"))[:-HISTORY_CAP]:
        old.unlink()


def pop_history(area, osmid):
    """Latest history entry, removed from the stack; None if empty."""
    d = areas.area_dir(area)
    hd = d / "buildings" / str(osmid) / "spec_history"
    ents = sorted(hd.glob("*.json")) if hd.is_dir() else []
    if not ents:
        return None
    spec = json.loads(ents[-1].read_text())
    ents[-1].unlink()
    return spec


def history_depth(area, osmid):
    d = areas.area_dir(area)
    hd = d / "buildings" / str(osmid) / "spec_history"
    return len(list(hd.glob("*.json"))) if hd.is_dir() else 0


def rebuild(area, osmid, new_spec, persist=True):
    """Rebuild one building; returns dict with mini-glb path. Raises on failure.
    persist=False -> preview only: geometry swaps in the viewer but nothing is
    written (spec.json, placements, blend all untouched)."""
    d = areas.area_dir(area)
    blend = None
    for c in sorted(d.glob("*_textured.blend")):
        blend = c
        break
    if blend is None:
        raise RuntimeError("area has no packed .blend")
    pl_path = d / "agent_placements.json"
    if not pl_path.exists():
        raise RuntimeError("area has no agent_placements.json")
    placements = json.loads(pl_path.read_text())
    entry = next((e for e in placements if e["id"] == osmid), None)
    if entry is None:
        raise RuntimeError("building is not in the placement list (special form or LoD1); web rebuild unsupported")

    measured = bool(new_spec.pop("_colors_measured", False))
    # footprint is the OSM/OBB contract -- never editable from the web
    old_spec_path = d / "buildings" / str(osmid) / "spec.json"
    old_spec = json.loads(old_spec_path.read_text()) if old_spec_path.exists() else {}
    if "footprint" in old_spec:
        new_spec["footprint"] = old_spec["footprint"]

    entry["desc"] = new_spec
    if "poly" in entry:
        derived = _cg().poly_params(new_spec)
        for k, v in derived.items():
            entry[k] = v
    if new_spec.get("colors"):
        entry["colors"] = new_spec["colors"]
        if "poly" not in entry:
            entry["desc"]["colors"] = new_spec["colors"]
    _shop_context(d, osmid, entry)

    tdir = d / "buildings" / str(osmid) / "textures"
    glb_out = areas.CACHE / f"{area}_b{osmid}_{int(time.time())}.glb"
    areas.CACHE.mkdir(exist_ok=True)
    src_p = areas.CACHE / "_components_src.py"
    src_p.write_text(components_src())
    job = {"entry": entry, "components_src": str(src_p),
           "texture_dir": str(tdir) if tdir.is_dir() else None,
           "save_blend": True, "glb_out": str(glb_out)}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     dir=areas.CACHE) as f:
        json.dump(job, f)
        job_p = f.name

    # FAST path via the WARM worker (parts kit resident): latency is
    # build+export only; the packed city blend syncs in a background thread
    # afterwards so the editor loop never waits on a 30 MB file.
    err = _worker_build(job_p)
    if err:
        raise RuntimeError("Blender rebuild failed:\n" + err)
    # prune older mini-glbs for this building (keep the newest 3)
    minis = sorted(areas.CACHE.glob(f"{area}_b{osmid}_*.glb"))
    for old_glb in minis[:-3]:
        old_glb.unlink(missing_ok=True)

    if persist:
        def _sync_blend():
            try:
                with areas._lock_for(area):
                    subprocess.run(
                        [areas.BLENDER, "-b", str(blend), "--python",
                         str(Path(__file__).parent / "rebuild_bpy.py"), "--", "--job", job_p],
                        capture_output=True, text=True, timeout=900)
            finally:
                Path(job_p).unlink(missing_ok=True)
        import threading
        threading.Thread(target=_sync_blend, daemon=True).start()
    else:
        Path(job_p).unlink(missing_ok=True)
        return {"glb": glb_out.name}

    # persist: spec.json (undo history + first-time backup) + placements.
    # Keep spec.json free of a palette identical to the measured one -- that is
    # assembly-time injection, not an author edit; a CHANGED palette stays.
    doc = dict(new_spec)
    if measured and doc.get("colors") == effective_measured(d, osmid):
        doc.pop("colors", None)
    bak = old_spec_path.with_suffix(".json.web.bak")
    if old_spec_path.exists() and not bak.exists():
        bak.write_text(old_spec_path.read_text())
    _push_history(old_spec_path.parent)
    old_spec_path.parent.mkdir(parents=True, exist_ok=True)
    old_spec_path.write_text(json.dumps(doc, indent=1))
    pl_path.write_text(json.dumps(placements, indent=1))
    return {"glb": glb_out.name}


def effective_measured(d, osmid):
    try:
        from img2city.building.facade_colors import colors_for
        return colors_for(str(d), osmid)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Edit-success benchmark (report: plan objective 5, "editing success rate")
# ---------------------------------------------------------------------------
def _glb_verts(path):
    import struct
    raw = Path(path).read_bytes()
    ln, = struct.unpack("<I", raw[12:16])
    doc = json.loads(raw[20:20 + ln])
    pos = {p["attributes"]["POSITION"] for m in doc["meshes"]
           for p in m["primitives"] if "POSITION" in p["attributes"]}
    return sum(doc["accessors"][i]["count"] for i in pos)


def _apply_edit(spec, field, rng):
    """One random VALID value for a schema field, applied the way panel.js
    applies it (dotted path; masses_override writes every mass). Returns the
    new value or None if the field does not apply to this spec."""
    path, t = field["path"], field["type"]
    parts = path.split(".")
    if parts[0] == "terrace" and not spec.get("terrace"):
        return None                        # OBB building: no terrace block
    cur = spec
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}                    # null sub-object -> start one (as the panel does)
        cur = cur[p]
    old = cur.get(parts[-1])
    if t == "int":
        v = rng.randint(field["min"], min(field["max"], 12))
        if v == old:
            v = v + 1 if v < field["max"] else v - 1
    elif t == "float":
        step = field.get("step", 0.1)
        n = int(round((field["max"] - field["min"]) / step))
        v = round(field["min"] + step * rng.randint(0, n), 2)
        if old is not None and abs(v - old) < 1e-6:
            v = round(min(field["max"], v + step), 2)
    elif t == "enum":
        v = rng.choice([c for c in field["choices"] if c != old] or field["choices"])
    elif t == "bool":
        v = not bool(old)
    elif t == "color":
        # linear RGB triple, exactly what panel.js sends (hex2lin)
        v = [round((rng.randint(0, 255) / 255.0) ** 2.2, 4) for _ in range(3)]
    else:
        return None
    cur[parts[-1]] = v
    if field.get("masses_override") and isinstance(spec.get("masses"), list):
        for m in spec["masses"]:
            m[parts[-1]] = v
    return v


def bench(area_names, n_buildings, seed, out_path):
    """Edit-success benchmark: for a seeded sample of buildings, apply every
    editable schema field once with a random valid value and rebuild as a
    PREVIEW (nothing persisted). Records success, wall-clock latency and the
    vertex-count delta; also rebuilds the UNCHANGED spec twice as the
    determinism control (same spec -> same vertex count). Zero LLM tokens."""
    import random
    import statistics as st
    from img2city.webapp.schema import get_schema
    from img2city.agent.tokens import provenance
    rng = random.Random(seed)
    fields = [f for g in get_schema()["groups"] for f in g["fields"]
              if not f.get("poly_drop")]
    cands = []
    for area in area_names:
        d = areas.area_dir(area)
        pl = json.loads((d / "agent_placements.json").read_text())
        for e in pl:
            sp = d / "buildings" / str(e["id"]) / "spec.json"
            if sp.exists():
                cands.append((area, e["id"]))
    rng.shuffle(cands)
    sample = cands[:n_buildings]
    rows, controls = [], []
    for area, osmid in sample:
        base = effective_spec(area, osmid)
        # control: unchanged spec twice
        vc = []
        for _ in range(2):
            t0 = time.time()
            try:
                r = rebuild(area, osmid, json.loads(json.dumps(base)), persist=False)
                vc.append((_glb_verts(areas.CACHE / r["glb"]), time.time() - t0))
            except Exception as e:
                vc.append((None, time.time() - t0))
        controls.append({"area": area, "id": osmid, "verts": [v for v, _ in vc],
                         "latency_s": [round(t, 2) for _, t in vc]})
        v0 = vc[0][0]
        for f in fields:
            spec = json.loads(json.dumps(base))
            v = _apply_edit(spec, f, rng)
            if v is None:
                continue
            t0 = time.time()
            try:
                r = rebuild(area, osmid, spec, persist=False)
                verts = _glb_verts(areas.CACHE / r["glb"])
                ok, err = True, None
            except Exception as e:
                verts, ok, err = None, False, str(e)[:160]
            rows.append({"area": area, "id": osmid, "field": f["path"],
                         "type": f["type"], "value": v, "ok": ok,
                         "latency_s": round(time.time() - t0, 2),
                         "verts": verts, "verts_base": v0,
                         "geometry_changed": (verts is not None and v0 is not None
                                              and verts != v0),
                         "err": err})
            print(f"[bench] {area}/{osmid} {f['path']}={v} ok={ok} "
                  f"{rows[-1]['latency_s']}s dverts="
                  f"{(verts - v0) if (verts is not None and v0 is not None) else None}",
                  flush=True)
    oks = [r for r in rows if r["ok"]]
    lat = [r["latency_s"] for r in oks]
    geo_fields = {"floors", "floor_h", "facade", "typology", "plinth",
                  "terrace.roof_form", "terrace.dormers", "terrace.bay_m"}
    geo = [r for r in oks if r["field"] in geo_fields]
    det = [c for c in controls if c["verts"][0] is not None and c["verts"][0] == c["verts"][1]]
    by_field = {}
    for r in rows:
        b = by_field.setdefault(r["field"], {"n": 0, "ok": 0, "changed": 0})
        b["n"] += 1; b["ok"] += int(r["ok"]); b["changed"] += int(r["geometry_changed"])
    summary = {"buildings": len(sample), "areas": area_names, "edits": len(rows),
               "success": len(oks), "success_rate": len(oks) / len(rows) if rows else None,
               "latency_median_s": st.median(lat) if lat else None,
               "latency_p90_s": sorted(lat)[int(0.9 * (len(lat) - 1))] if lat else None,
               "latency_mean_s": st.mean(lat) if lat else None,
               "latency_sd_s": st.pstdev(lat) if len(lat) > 1 else None,
               "geometry_edits": len(geo),
               "geometry_edits_changed_mesh": sum(r["geometry_changed"] for r in geo),
               "determinism_controls": len(controls),
               "determinism_identical": len(det),
               "by_field": by_field,
               "provenance": provenance(seed=seed, llm_tokens=0)}
    json.dump({"rows": rows, "controls": controls, "summary": summary},
              open(out_path, "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("by_field", "provenance")}, indent=1))
    print(f"-> {out_path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--areas", nargs="*", default=["city_sk", "city_rah", "city_cw"])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(config.CACHE_DIR / "edit_bench.json"))
    a = ap.parse_args()
    if a.bench:
        bench(a.areas, a.n, a.seed, a.out)
