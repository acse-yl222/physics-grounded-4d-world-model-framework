"""img2city/city/make_city.py -- ONE command: bbox in, verified 3D city model out.

The deliverable the project promised (08-13): circle an area
on the map; the Google/OSM APIs + the agent do the rest, and the result must
have CORRECT ROADS and CORRECT BASIC LANDMARKS. This orchestrator chains every
proven stage of the pipeline in order, resumably (each stage skips itself if
its artifact already exists, so a crashed run just re-runs the same command),
and finishes with a machine-checked verification report instead of a vibe.

  img2city make-city --bbox "51.5030,-0.0280,51.5085,-0.0140" --out data/city_x
  img2city make-city --query "Piazza San Marco, Venice" --span 350 --out data/city_ven
  (equivalently: python -m img2city.city.make_city ...)

Token-costing stages (specs / shop reads / glass looks / refine) only run with
--yes; without it the command executes every FREE stage (OSM, roads, heights,
functions, vehicles, traffic) and prints the scope + token estimate for the
paid remainder -- the standing present-cost-before-batch rule, built in.

Stage order (each idempotent):
  bootstrap  OSM ways+relations -> buildings.json; region.json via reverse
             geocode of the bbox centre (Google Geocoding API)
  heights    EA LiDAR DSM-DTM correction -- England bboxes only, else OSM tags
  functions  Places(New) POI-in-footprint -> per-building func
  specs      one agent spec per building (typology cards pick the dialect)
  scene      road_graph -> traffic.json; vehicle detection (torch env);
             traffic_sim -> traffic_anim.json; shop_assets -> shops.json
  shops/glass  agent street-view reads (paid)
  refine     landmark-first blanket at --refine-iters (default 2, the measured
             67%-of-lift / third-of-cost recipe) via overnight_refine.sh
  final      assembly --min-area 0 + regress baseline + packed .blend export
  verify     roads + landmarks + coverage report -> pipeline_report.json
"""
from __future__ import annotations
import argparse
import json
import math
import os
import socket
import subprocess
import sys

from img2city import config
from img2city.imagery import maps_fetch

# interpreter that carries torch/transformers (vehicle detection); see config
TORCH_PY = config.TORCH_PYTHON

# rough token prices of the paid stages, from measured campaigns

TOK_SPEC = 50_000        # per building, one-shot spec
TOK_REFINE = 500_000     # per building, refine-iters 2 (0.5M measured)
TOK_SHOP = 40_000        # per named shop unit street-view read
TOK_GLASS = 30_000       # per curtain-wall building look


def sh(cmd, env=None, check=True):
    """Run one pipeline stage as a subprocess from the repository root."""
    print(f"\n$ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(config.PROJECT_ROOT),
                       env=config.subprocess_env(env))
    if check and r.returncode != 0:
        raise SystemExit(f"[make-city] stage failed rc={r.returncode}: {' '.join(cmd[:3])}")
    return r.returncode


def stage(module, *args, python=None):
    """``python -m img2city.<module> <args>`` -- every stage is a module of the
    package, never a loose script."""
    return config.module_cmd(module, *args, python=python)


# ISO country codes that drive on the LEFT; everyone else keeps right
LEFT_DRIVE = {"GB", "IE", "MT", "CY", "JP", "AU", "NZ", "IN", "PK", "BD",
              "LK", "NP", "TH", "MY", "SG", "ID", "HK", "MO", "ZA", "KE",
              "TZ", "UG", "ZW", "ZM", "MW", "MZ", "BW", "NA", "JM", "TT",
              "GY", "SR", "BN", "MU", "MV", "FJ", "PG", "WS", "TO"}


def reverse_region(bbox):
    """(region, drive) for a bbox centre via the Geocoding API: city-level
    region tag (feeds the area-default dialect + BRIEF prior; typology cards
    do the per-building work) + which side of the road the country drives on
    (feeds lane offsets + arrow marks). Falls back to ('unknown', 'right')."""
    import urllib.request
    from img2city.imagery.maps_fetch import GEOCODE, _key
    lat, lng = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    url = f"{GEOCODE}?latlng={lat},{lng}&key={_key()}"
    region, drive = "unknown", "right"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
        for res in d.get("results", []):
            for c in res.get("address_components", []):
                if "locality" in c["types"] and region == "unknown":
                    region = c["long_name"].strip().lower().replace(" ", "_")
                if "country" in c["types"] and c.get("short_name"):
                    drive = ("left" if c["short_name"] in LEFT_DRIVE
                             else "right")
            if region != "unknown":
                break
    except Exception as e:
        print(f"[make-city] reverse geocode failed ({str(e)[:60]})")
    return region, drive


def bbox_from_query(query, span_m):
    from img2city.imagery.maps_fetch import geocode
    lat, lng = geocode(query)
    dlat = span_m / 2 / 110540.0
    dlng = span_m / 2 / (111320.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lng - dlng, lat + dlat, lng + dlng)


def in_england(bbox):
    lat, lng = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return 49.9 <= lat <= 55.9 and -6.5 <= lng <= 1.8


def export_blend(out):
    """Pack textures + save the deliverable .blend through the live Blender."""
    out = os.path.abspath(out)              # Blender's cwd is not ours
    name = os.path.basename(out.rstrip("/"))
    path = os.path.join(out, f"{name}_textured.blend")
    code = ("import bpy\n"
            "try: bpy.ops.file.pack_all()\n"
            "except Exception as e: print(e)\n"
            f"bpy.ops.wm.save_as_mainfile(filepath=r\"{path}\", "
            "compress=True, copy=True)\nprint('saved')")
    payload = json.dumps({"type": "execute_code",
                          "params": {"code": code}}).encode()
    buf = b""
    with socket.create_connection((config.MCP_HOST, config.MCP_PORT), timeout=900) as s:
        s.settimeout(900)
        s.sendall(payload)
        while True:
            ch = s.recv(65536)
            if not ch:
                break
            buf += ch
            try:
                json.loads(buf.decode())
                break
            except Exception:
                continue
    print(f"[make-city] deliverable -> {path} "
          f"({os.path.getsize(path)/1048576:.1f} MB)")
    return path


def rescue_landmarks(out):
    """Ring-sample fresh street views for landmark-sized named buildings whose
    gate judged the original imagery unusable. Returns how many were rescued
    (their spec.json/gate.json are cleared, so the spec stage regenerates)."""
    from img2city.imagery.rescue_imagery import rescue_building
    from img2city.imagery.maps_fetch import _key
    d = json.load(open(os.path.join(out, "buildings.json")))
    n = 0
    for m in d["buildings"]:
        if not m.get("name") or m["area_m2"] < 300:
            continue
        bdir = os.path.join(out, "buildings", str(m["id"]))
        gp = os.path.join(bdir, "gate.json")
        try:
            if not (os.path.exists(gp) and json.load(open(gp)).get("fallback")):
                continue
        except Exception:
            continue
        try:
            got = rescue_building(m, bdir, _key())
        except Exception as e:
            print(f"[rescue] {m['id']} {maps_fetch.latin_only(m['name'])}: {str(e)[:60]}")
            got = None
        print(f"[rescue] {m['id']} '{maps_fetch.latin_only(m['name'])}': "
              + (f"new vantage at {got:.0f} m" if got else "no usable vantage"))
        n += bool(got)
    return n


def verify(out):
    """Machine checks for the two hard requirements: ROADS and LANDMARKS."""
    rep = {"area": out}
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas = d["buildings"]

    # ---- roads: every OSM highway class in the bbox must be one scene_assets
    # knows how to draw (the Cromwell Road lesson: an unknown class is a road
    # that silently never renders)
    from img2city.scene.assets import ROAD_WIDTH, ROAD_SKIP_OK
    classes, named = {}, set()
    try:
        raw = json.load(open(os.path.join(out, "roads_raw.json")))
        for el in (raw if isinstance(raw, list) else raw.get("elements", [])):
            hw = el.get("tags", {}).get("highway")
            if hw:
                classes[hw] = classes.get(hw, 0) + 1
                if el["tags"].get("name"):
                    named.add(el["tags"]["name"])
    except FileNotFoundError:
        pass
    unknown = {c: n for c, n in classes.items()
               if c not in ROAD_WIDTH and c not in ROAD_SKIP_OK}
    arcs = 0
    try:
        arcs = len(json.load(open(os.path.join(out, "traffic.json")))["arcs"])
    except Exception:
        pass
    rep["roads"] = {"classes": classes, "UNDRAWN_classes": unknown,
                    "named_streets": sorted(named), "directed_arcs": arcs,
                    "ok": not unknown and arcs > 0}

    # ---- landmarks: every NAMED building of substance must have a real agent
    # spec (not a fallback shell) and a refine result; the 300 m2 floor keeps
    # station entrances / single shop units out of the landmark ledger (the
    # 67 m2 "Canada Square Car Park Entrance" is a door, not a landmark)
    lm, miss_spec, miss_ref = [], [], []
    for m in metas:
        if not m.get("name") or m["area_m2"] < 300:
            continue
        bdir = os.path.join(out, "buildings", str(m["id"]))
        fb = False
        gp = os.path.join(bdir, "gate.json")
        if os.path.exists(gp):
            try:
                fb = json.load(open(gp)).get("fallback", False)
            except Exception:
                pass
        has_spec = os.path.exists(os.path.join(bdir, "spec.json")) and not fb
        rj = os.path.join(bdir, "refine", "result.json")
        score = None
        if os.path.exists(rj):
            try:
                r = json.load(open(rj))
                score = r.get("best_pass_rate", r.get("best", "done"))
            except Exception:
                pass
        lm.append({"id": m["id"], "name": m["name"], "spec": has_spec,
                   "refined": score})
        if not has_spec:
            miss_spec.append(m["name"])
        elif score is None:
            miss_ref.append(m["name"])
    rep["landmarks"] = {"n": len(lm), "no_spec": miss_spec,
                        "not_refined": miss_ref, "detail": lm,
                        "ok": not miss_spec and not miss_ref}

    # ---- coverage + scene layers present
    n_spec = n_fb = n_ref = 0
    for m in metas:
        bdir = os.path.join(out, "buildings", str(m["id"]))
        if os.path.exists(os.path.join(bdir, "spec.json")):
            n_spec += 1
            gp = os.path.join(bdir, "gate.json")
            try:
                if os.path.exists(gp) and json.load(open(gp)).get("fallback"):
                    n_fb += 1
            except Exception:
                pass
        if os.path.exists(os.path.join(bdir, "refine", "result.json")):
            n_ref += 1
    layers = {f: os.path.exists(os.path.join(out, f)) for f in
              ("traffic.json", "vehicles.json", "traffic_anim.json",
               "shops.json", "green_raw.json", "transport_raw.json")}
    rep["coverage"] = {"buildings": len(metas), "specs": n_spec,
                       "fallback_shells": n_fb, "refined": n_ref}
    rep["layers"] = layers
    # ---- vehicles: no rendered body inside a built outline, no two bodies
    # overlapping, animated traffic clear of buildings / parked cars / itself
    # (08-19: cars crashed into shops and into each other)
    if layers["vehicles.json"]:
        try:
            from img2city.scene.traffic_audit import audit
            va = audit(out, verbose=False)
            va["ok"] = not any(v for k, v in va.items() if k != "moving_samples")
        except Exception as e:
            va = {"ok": False, "error": str(e)}
        rep["vehicles"] = va
    else:
        rep["vehicles"] = {"ok": True, "note": "no vehicle layer"}
    rep["ok"] = rep["roads"]["ok"] and rep["landmarks"]["ok"] and rep["vehicles"]["ok"]

    with open(os.path.join(out, "pipeline_report.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(f"\n[verify] roads: {sum(classes.values())} ways / "
          f"{len(named)} named streets / {arcs} arcs"
          + (f"  !! UNDRAWN classes {unknown}" if unknown else "  OK"))
    print(f"[verify] landmarks: {len(lm)} named; "
          f"no-spec {len(miss_spec)} {miss_spec[:5]}; "
          f"unrefined {len(miss_ref)} {miss_ref[:5]}")
    print(f"[verify] coverage: {n_spec}/{len(metas)} specs "
          f"({n_fb} honest shells), {n_ref} refined; layers "
          + ", ".join(k for k, v in layers.items() if v))
    print(f"[verify] vehicles: {'OK' if rep['vehicles']['ok'] else 'COLLISIONS'} "
          + json.dumps({k: v for k, v in rep['vehicles'].items() if k != 'ok'}))
    print(f"[verify] MACHINE CHECKS: {'PASS' if rep['ok'] else 'INCOMPLETE'} "
          f"-> {out}/pipeline_report.json")
    return rep


def main():
    ap = argparse.ArgumentParser(description="bbox -> verified 3D city model")
    ap.add_argument("--bbox", help="s,w,n,e")
    ap.add_argument("--query", help="place name; geocoded to a --span bbox")
    ap.add_argument("--span", type=float, default=400.0,
                    help="bbox edge in metres when using --query")
    ap.add_argument("--out", required=True)
    ap.add_argument("--region", default=None,
                    help="override the reverse-geocoded region tag")
    ap.add_argument("--model", default=config.SPEC_MODEL)
    ap.add_argument("--refine-iters", type=int, default=2)
    ap.add_argument("--refine-min-area", type=int, default=60,
                    help="passed to scripts/overnight_refine.sh as its $2 (MIN-AREA)")
    ap.add_argument("--yes", action="store_true",
                    help="run the token-costing stages (specs/shops/glass/"
                         "refine); without it, free stages only + a cost quote")
    ap.add_argument("--skip-refine", action="store_true")
    ap.add_argument("--skip-export", action="store_true",
                    help="stop before Blender assembly/export (no live Blender)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    # ---- bbox
    bbp = os.path.join(out, "bbox.json")
    if os.path.exists(bbp):
        bbox = tuple(json.load(open(bbp)))
    elif a.bbox:
        bbox = tuple(float(v) for v in a.bbox.split(","))
    elif a.query:
        bbox = bbox_from_query(a.query, a.span)
        print(f"[make-city] '{a.query}' -> bbox {bbox}")
    else:
        raise SystemExit("need --bbox or --query (or an existing bbox.json)")
    json.dump(list(bbox), open(bbp, "w"))

    # ---- stale-dir guard (08-16 incident: data/city_sk2 was a leftover dir
    # holding an OLD copy of another area's buildings.json; resume trusted it
    # and rebuilt the wrong area — 60M tokens on a duplicate and a wrong
    # roads.geojson to the collaborator). An existing buildings.json must
    # AGREE with the requested bbox or the run refuses to continue.
    bj = os.path.join(out, "buildings.json")
    if os.path.exists(bj):
        got = json.load(open(bj))["anchor"]["bbox"]
        if any(abs(g - b) > 1e-4 for g, b in zip(got, bbox)):
            raise SystemExit(
                f"[make-city] REFUSING: {bj} covers bbox {got} but this run "
                f"asked for {list(bbox)} — stale directory? Move it aside or "
                "pass the matching bbox.")

    # ---- bootstrap (free)
    if not os.path.exists(os.path.join(out, "buildings.json")):
        from img2city.city.lod1 import fetch_osm, to_local
        raw = fetch_osm(bbox, os.path.join(out, "osm_raw.json"))
        metas, anchor = to_local(raw, bbox)
        json.dump({"anchor": anchor, "buildings": metas},
                  open(os.path.join(out, "buildings.json"), "w"), indent=1)
        print(f"[make-city] {len(metas)} footprints")
    rp = os.path.join(out, "region.json")
    if not os.path.exists(rp):
        region, drive = reverse_region(bbox)
        region = a.region or region
        json.dump({"region": region, "drive": drive}, open(rp, "w"))
        print(f"[make-city] region -> {region} (drives on the {drive})")

    # ---- heights (free; England only)
    if in_england(bbox) and not os.path.exists(os.path.join(out, "height_check.json")):
        sh(stage("city.height_check", "--out", out, "--apply"),
           check=False)

    # ---- functions (Places $, cents not tokens)
    if not os.path.exists(os.path.join(out, "buildings.json.func.bak")):
        sh(stage("city.building_function", "--out", out), check=False)

    # ---- scope + quote
    d = json.load(open(os.path.join(out, "buildings.json")))
    metas = d["buildings"]
    n_spec_todo = sum(1 for m in metas if not os.path.exists(
        os.path.join(out, "buildings", str(m["id"]), "spec.json")))
    tok_refine = 0 if a.skip_refine else len(metas) * TOK_REFINE
    est = n_spec_todo * TOK_SPEC + tok_refine
    refine_part = ("refine skipped" if a.skip_refine else
                   f"refine-iters-{a.refine_iters} worst case "
                   f"{tok_refine/1e6:.0f}M")
    print(f"\n[make-city] scope: {len(metas)} buildings; {n_spec_todo} specs to "
          f"write; paid stages ~{est/1e6:.2f}M tokens upper bound "
          f"(specs {n_spec_todo * TOK_SPEC/1e6:.2f}M + {refine_part}"
          " -- gate-skips reduce it)")
    if not a.yes:
        print("[make-city] dry quote done -- re-run with --yes to spend tokens")
        # still finish every remaining FREE stage below where possible
    else:
        # ---- specs (paid; resumable; assembly included -> needs Blender
        # unless we defer): run spec generation only, assemble at the end
        spec_cmd = stage("city.generate", "--out", out, "--min-area", "0",
                         "--model", a.model, "--workers", "3",
                         *(["--assemble-only"] if a.skip_export else []))
        sh(spec_cmd, check=False)
        # ---- typology cards (cheap haiku pass) AFTER specs: classification
        # needs the per-building photos, which the spec stage's ensure_imagery
        # fetches -- running it earlier classifies against nothing (08-16 sk2:
        # 3/229). Specs run on the area fallback; the CARD tags kick in where
        # the real lift happens (rescue re-specs + the refine loop), including
        # graduated-card dialects (a haussmann-reading mansion block pulls the
        # paris balcony vocabulary here).
        sh(stage("building.typology", "--out", out), check=False)
        # ---- landmark rescue: a named >=300 m2 building stuck as a fallback
        # shell fails the deliverable's landmark bar; ring-sample a better
        # vantage (rescue clears its spec/gate) and re-run the spec pass
        if rescue_landmarks(out):
            sh(spec_cmd, check=False)

    # ---- deterministic scene layers (free)
    sh(stage("scene.road_graph", "--out", out), check=False)
    if os.path.exists(TORCH_PY):
        sh(stage("scene.vehicles", "--out", out, python=TORCH_PY), check=False)
    else:
        print("[make-city] WARNING: IMG2CITY_TORCH_PYTHON not found -- no vehicle detection")
    if os.path.exists(os.path.join(out, "vehicles.json")):
        sh(stage("scene.traffic_sim", "--out", out), check=False)
        sh(stage("scene.traffic_audit", "--out", out), check=False)
    sh(stage("scene.shops", "--out", out), check=False)

    if a.yes:
        # ---- paid street-view reads
        if os.path.exists(os.path.join(out, "shops.json")):
            sh(stage("scene.shop_agent", "--out", out, "--model", a.model), check=False)
        sh(stage("building.glass_agent", "--out", out, "--model", a.model), check=False)
        # ---- refine blanket, landmark-first (refine_todo ordering)
        if not a.skip_refine:
            sh([str(config.PROJECT_ROOT / "scripts" / "overnight_refine.sh"), out, str(a.refine_min_area), a.model],
               env={"ITERS": str(a.refine_iters), "PYTHON": sys.executable}, check=False)

    # ---- facade colour measurement (free: deterministic pixel math over the
    # cached photos/facts/satellite crops) + region palette derivation. Was a
    # manual step until 09-04 -- Delhi shipped with 0 measured walls/roofs
    # because nobody remembered to run it; now it is a stage.
    sh(stage("building.facade_colors", "--out", out), check=False)

    # ---- final assembly + baseline + export (needs live Blender :9876)
    if not a.skip_export:
        sh(stage("city.generate", "--out", out, "--assemble-only", "--min-area", "0"))
        sh(stage("city.render_regress", "--snapshot", "--out", out),
           check=False)
        export_blend(out)

    verify(out)
    if a.yes and not a.skip_export:
        from img2city.city.quality import assess
        report = assess(out)
        print(f"[make-city] AGENT ACCEPTANCE: {report['status']}")
        return 0 if report["status"].startswith("PASS") else 2
    print("[make-city] Visual acceptance not run; this is not an accepted district.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
