"""Run the bird model inside a framework scene and write the city viewer's bird replay.

  python -m urban_geometry.birds.scene.run fetch-fields --scene white_city --dest <fields>
  python -m urban_geometry.birds.scene.run fetch-model --scene white_city --fields <fields> --dest <models>
  python -m urban_geometry.birds.scene.run prepare-geometry --scene white_city --glb <models>/<city>.glb --out <geo>
  python -m urban_geometry.birds.scene.run run --scene white_city --geometry <geo> --fields <fields>

fetch-fields      downloads the scene's published scene.json and wind / pollution / temperature frames
fetch-model       downloads the scene's city GLB (scene.json model.parts_manifest, SHA-256 checked)
                  and its supplement GLB if any
prepare-geometry  bakes the scene's city GLB and voxelises it with the framework voxeliser (2 m),
                  plus bird land cover (parks, trees, water)
run               chooses, per flock, a roost + its own forage sites from the land cover, runs each
                  flock roost-to-roost over the span of the scene's wind frames with the scene's
                  fields and sun (one process per flock), merges them into one replay and writes
                  project/<scene>/input/<version>/bird_replay.* and project/<scene>/configs/bird_visualization.json
"""

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# canonical scene id -> city viewer scene id, and what the scene itself does not record
SCENES = {
    "south_ken": {"viewer": "south_kensington", "supplement": "models/buildings_supplement.glb"},
    "white_city": {"viewer": "white_city"},
    "tower_hamlets": {
        "viewer": "tower_hamlets",
        # the published scene records no georeference or daily solar run; these are the public
        # coordinates of Canary Wharf, used only for the sun clock
        "location": (51.5054, -0.0235),
    },
}
ALIASES = {"south_kensington": "south_ken", "core008": "south_ken", "canary_wharf": "tower_hamlets"}
DOMAIN_MARGIN_M = 300.0  # flying room around the sites
AIR_ABOVE_ROOFS_M = 60.0  # geometry kept above the tallest roof in the domain
ROUTE_CELL_M = 8.0  # wave-routing grid (collision stays at the geometry's 2 m)
MAX_REPLAY_FRAMES = 5000  # caps the replay at ~72 MB for 4 x 300 birds


def scene_entry(scene):
    scene = ALIASES.get(scene, scene)
    if scene not in SCENES:
        raise SystemExit(f"unknown scene {scene!r}; known: {sorted(SCENES)}")
    return scene, SCENES[scene]


def cmd_prepare_geometry(args):
    from urban_geometry.birds.scene.geometry import prepare

    meta, cover = prepare(args.glb, args.out, args.supplement or (), cell=args.cell)
    print(
        json.dumps({"shape_zyx": meta["shape_zyx"], "origin": meta["source_region_origin_xyz_m"]})
    )
    print(json.dumps(cover, indent=1))


def cmd_fetch_fields(args):
    from urban_geometry.birds.scene.fields import PUBLIC_SITE, fetch_scene

    _, entry = scene_entry(args.scene)
    dest = fetch_scene(entry["viewer"], args.dest, args.base_url or PUBLIC_SITE)
    print(f"fields in {dest}")


def cmd_fetch_model(args):
    from urban_geometry.birds.scene.fields import PUBLIC_SITE, fetch_model

    glb, supplements = fetch_model(
        args.fields, args.dest, args.base_url or PUBLIC_SITE, args.resources_url
    )
    extra = "".join(f" --supplement {s}" for s in supplements)
    print(
        f"model: {glb}\nnext: prepare-geometry --scene {args.scene} --glb {glb}{extra} --out <dir>"
    )


def _field_box(scene_json):
    g = scene_json["grid"]
    x0, y0 = float(g["x0"]), -float(g["z_south"])
    return [x0, y0, x0 + g["cols"] * g["cell_m"], y0 + g["rows"] * g["cell_m"]]


def _place_roosted(state, config, rng):
    """All birds start on the roost surface in ROOST (the run goes roost -> day -> roost)."""
    import numpy as np

    from urban_geometry.birds.sim.states import ROOST

    roost = config.world["roosts"][0]
    n = state["pos"].shape[0]
    half = np.array(roost["size"]) / 2 * 0.8
    fwd = np.array(roost["forward"], dtype=float)
    side = np.cross([0.0, 0.0, 1.0], fwd)
    u = rng.uniform(-half[0], half[0], n)
    v = rng.uniform(-half[1], half[1], n)
    state["pos"] = np.array(roost["center"], dtype=float) + u[:, None] * fwd + v[:, None] * side
    # sit each bird on the top of its own voxel column: the roost's z is the footprint's mean
    # height, which can fall inside the top voxel, and a bird starting inside solid never gets out
    geo = np.load(config.geometry_path)
    solid, sp, origin = geo["geometry"], float(geo["grid_spacing"]), geo["grid_origin"]
    gi = np.clip(((state["pos"][:, 0] - origin[0]) / sp).astype(int), 0, solid.shape[2] - 1)
    gj = np.clip(((state["pos"][:, 1] - origin[1]) / sp).astype(int), 0, solid.shape[1] - 1)
    column = solid[:, gj, gi]  # (nz, n)
    filled = column.any(axis=0)
    top = origin[2] + (solid.shape[0] - np.argmax(column[::-1], axis=0)) * float(
        geo["grid_spacing_z"]
    )
    state["pos"][filled, 2] = top[filled] + 0.01
    heading = rng.uniform(0, 2 * np.pi, n)
    state["vel"] = np.stack([np.cos(heading), np.sin(heading), np.zeros(n)], axis=1) * 0.01
    state["bank"] = np.zeros(n)
    state["bstate"] = np.full(n, ROOST, dtype=np.int32)
    return state


def _clock(args, entry, fields, duration):
    from urban_geometry.birds.scene.fields import SunClock

    clock = SunClock.from_manifest(fields.manifest, args.date, duration)
    if clock is None:
        if args.latitude is not None:
            location = (args.latitude, args.longitude)
        elif "location" in entry:
            location = entry["location"]
        else:
            raise SystemExit(f"no solar run for {args.date}; pass --latitude/--longitude")
        clock = SunClock.from_location(*location, args.date, duration)
    return clock


def _domain(g, world, field_box):
    """Flying box around one flock's sites (inside the field coverage) and its tallest roof."""
    import numpy as np

    pts = np.array([s["center"][:2] for s in world["roosts"] + world["forage_sites"]])
    box = [*(pts.min(0) - DOMAIN_MARGIN_M), *(pts.max(0) + DOMAIN_MARGIN_M)]
    box = [max(box[0], field_box[0]), max(box[1], field_box[1])] + [
        min(box[2], field_box[2]),
        min(box[3], field_box[3]),
    ]
    r0, c0 = g.index(box[0], box[1])
    r1, c1 = g.index(box[2], box[3])
    return box, float(g.height[max(r0, 0) : r1, max(c0, 0) : c1].max())


def _run_flock(job):
    """
    One flock = one independent simulation (own geometry crop, fields, seed), run in its own
    process. Returns its saved frames and per-flock checks; all flocks share dt, duration and
    frame spacing, so their frames line up and are merged along the bird axis.
    """
    import numpy as np

    from urban_geometry.birds.scene.fields import SceneFields
    from urban_geometry.birds.sim.config import SimConfig
    from urban_geometry.birds.sim.integrator import init_state, step
    from urban_geometry.birds.sim.states import ROOST

    args, entry, k = job["args"], job["entry"], job["flock"]
    tag = f"[birds] flock {k + 1}"
    fields = SceneFields(args.fields, job["box"])
    clock = _clock(args, entry, fields, job["duration"])
    config = SimConfig(
        n_birds=args.n_birds,
        dt=job["dt"],
        n_steps=round(job["duration"] / job["dt"]),
        seed=args.seed + k,
        geometry_path=job["geometry"]["file"],
        scaled_grid_origin=tuple(job["geometry"]["origin_xyz_m"]),
        world_generation="off",
        world=job["world"],
        wind_mode="none",  # superseded by the scene wind in external_fields
        start_state=ROOST,
        enable_predator=False,
        save_every=job["save_every"],
        external_fields=fields.samplers(),
        day_clock=clock,
        route_cell_m=ROUTE_CELL_M,
        route_block_fraction=args.route_block_fraction,
    )
    np.random.seed(config.seed)
    state = init_state(config)
    state = _place_roosted(state, config, np.random.RandomState(config.seed + 7))
    frames = {k: [] for k in ("pos", "vel", "bank", "bstate", "time")}
    wall = time.time()
    report_every = max(1, config.n_steps // 25)
    for i in range(config.n_steps + 1):
        if i % config.save_every == 0:
            frames["pos"].append(state["pos"].astype(np.float32))
            frames["vel"].append(state["vel"].astype(np.float32))
            frames["bank"].append(state["bank"].astype(np.float32))
            frames["bstate"].append(state["bstate"].astype(np.uint8))
            frames["time"].append(state["time"])
        if i % report_every == 0:
            bs = state["bstate"]
            rate = (i + 1) / max(time.time() - wall, 1e-3)
            counts = " ".join(f"{n[0]}={int((bs == j).sum())}" for j, n in enumerate("FTMDR"))
            print(
                f"{tag}: t={state['time']:7.0f}s local {clock.clock_h(state['time']):5.2f}h "
                f"{counts} | {rate:.1f} steps/s ETA {(config.n_steps - i) / rate / 60:.0f} min",
                flush=True,
            )
        if i < config.n_steps:
            state = step(state, config)
    arr = {k: np.array(v) for k, v in frames.items()}

    # occupancy check on every saved position: inside a solid voxel while flying = penetration
    geo = np.load(job["geometry"]["file"])
    solid, sp, origin = geo["geometry"], float(geo["grid_spacing"]), geo["grid_origin"]
    idx = np.floor((arr["pos"] - origin) / sp).astype(int)  # (F, N, 3) x, y, z cells
    inside = (
        (idx[..., 0] >= 0)
        & (idx[..., 0] < solid.shape[2])
        & (idx[..., 1] >= 0)
        & (idx[..., 1] < solid.shape[1])
        & (idx[..., 2] >= 0)
        & (idx[..., 2] < solid.shape[0])
    )
    occupied = np.zeros(inside.shape, dtype=bool)
    occupied[inside] = solid[idx[..., 2][inside], idx[..., 1][inside], idx[..., 0][inside]]
    flying = np.isin(arr["bstate"], (1, 2, 3))
    arr["checks"] = {
        "nonfinite_positions": int((~np.isfinite(arr["pos"])).sum()),
        "flying_outside_domain_samples": int((~inside & flying).sum()),
        "flying_samples": int(flying.sum()),
        "flying_inside_buildings_samples": int((occupied & flying).sum()),
        "grounded_inside_buildings_samples": int((occupied & ~flying).sum()),
    }
    arr["config"] = {
        f.name: getattr(config, f.name)
        for f in dataclasses.fields(config)
        if f.name not in ("external_fields", "day_clock", "world")
    }
    arr["wall_s"] = round(time.time() - wall, 1)
    print(f"{tag}: done in {arr['wall_s'] / 60:.1f} min {arr['checks']}", flush=True)
    return arr


def cmd_run(args):
    import multiprocessing
    import os

    import numpy as np

    from common.storage import Storage
    from urban_geometry.birds.scene.export import flock_moments, write_replay, write_viewer_config
    from urban_geometry.birds.scene.fields import SceneFields
    from urban_geometry.birds.scene.geometry import SceneGeometry, copy_metadata
    from urban_geometry.birds.scene.placement import choose_flocks
    from urban_geometry.birds.sim.config import SimConfig
    from urban_geometry.birds.sim.states import ROOST

    scene, entry = scene_entry(args.scene)
    started = time.time()
    storage = Storage.load()
    version = args.version or time.strftime("birds_%Y%m%d")
    out_dir = Path(args.out) if args.out else storage.assets(scene, "input") / version
    if (out_dir / "bird_replay.json").exists() and not args.overwrite:
        raise SystemExit(f"{out_dir} already holds a replay; use --version or --overwrite")
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "work"
    work.mkdir(exist_ok=True)

    # geometry + sites: one roost and its own forage sites per flock
    g = SceneGeometry(args.geometry)
    scene_json = json.loads((Path(args.fields) / "scene.json").read_text())
    field_box = _field_box(scene_json)
    defaults = SimConfig.__dataclass_fields__
    placed = choose_flocks(
        g,
        field_box,
        n_flocks=args.flocks,
        n_forage=defaults["world_gen_n_forage"].default,
        min_roost_area=defaults["world_gen_min_roost_area"].default,
        min_forage_area=defaults["world_gen_min_forage_area"].default,
    )
    if len(placed) < args.flocks:
        print(f"[birds] only {len(placed)} of {args.flocks} flocks fit the scene", flush=True)
    domains = []
    for k, (world, _) in enumerate(placed):
        box, roof_top = _domain(g, world, field_box)
        info = g.bird_geometry(
            box, roof_top + AIR_ABOVE_ROOFS_M, work / f"bird_geometry_{k + 1}.npz"
        )
        domains.append((box, info))
    del g
    copy_metadata(args.geometry, out_dir / "provenance")

    # shared clock: every flock runs the same span at the same dt, so frames line up
    union = [min(b[0] for b, _ in domains), min(b[1] for b, _ in domains)] + [
        max(b[2] for b, _ in domains),
        max(b[3] for b, _ in domains),
    ]
    fields = SceneFields(args.fields, union)
    duration = args.duration or (fields.span_s("wind")[1] if "wind" in fields.layers else 2500.0)
    clock = _clock(args, entry, fields, duration)
    frame_dt = args.frame_dt or max(1.0, duration / MAX_REPLAY_FRAMES)
    dt = args.dt or defaults["dt"].default
    save_every = max(1, round(frame_dt / dt))
    fields_info = fields.describe()
    del fields
    print(
        f"[birds] {scene}: {len(placed)} flocks x {args.n_birds} birds, {duration:.0f} s at "
        f"dt={dt} ({round(duration / dt)} steps each)\n[birds] clock: {json.dumps(clock.describe())}"
    )
    for k, (world, report) in enumerate(placed):
        print(
            f"[birds] flock {k + 1}: roost {report['roosts']} forage {json.dumps(report['forage'])}"
        )

    jobs = [
        {
            "args": args,
            "entry": entry,
            "flock": k,
            "world": world,
            "box": box,
            "geometry": info,
            "duration": duration,
            "dt": dt,
            "save_every": save_every,
        }
        for k, ((world, _), (box, info)) in enumerate(zip(placed, domains))
    ]
    workers = max(1, min(args.workers or min(4, os.cpu_count() or 1), len(jobs)))
    # a fresh process per flock: the sim keeps per-process caches (geometry, routing)
    with multiprocessing.get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        results = pool.map(_run_flock, jobs, chunksize=1)

    t = results[0]["time"]
    if any(len(r["time"]) != len(t) or not np.allclose(r["time"], t) for r in results):
        raise RuntimeError("flock frame times differ; cannot merge")
    arr = {
        k: np.concatenate([r[k] for r in results], axis=1) for k in ("pos", "vel", "bank", "bstate")
    }
    bs = arr["bstate"]
    light = np.array([clock.light(x) for x in t])
    local = [clock.clock_h(x) for x in (t[0], t[-1])]

    flocks, first = [], 0
    for k, (r, (world, report), (box, info)) in enumerate(zip(results, placed, domains)):
        n = r["bstate"].shape[1]
        flocks.append(
            {
                "id": k + 1,
                "first_bird": first,
                "birds": n,
                "seed": args.seed + k,
                # viewer frame (X, Y, Z) = (x, z, -y), as the replay records
                "roost": [
                    [s["center"][0], s["center"][2], -s["center"][1]] for s in world["roosts"]
                ],
                "forage_sites": [
                    [s["center"][0], s["center"][2], -s["center"][1]] for s in world["forage_sites"]
                ],
                "moments": flock_moments(r["bstate"], t),
                "sites": world,
                "site_report": report,
                "geometry": {**info, "file": f"work/{Path(info['file']).name}"},
                "checks": r["checks"],
                "wall_s": r["wall_s"],
            }
        )
        first += n
    checks = {key: int(sum(r["checks"][key] for r in results)) for key in results[0]["checks"]}
    checks.update(
        {
            "max_step_m": float(np.linalg.norm(np.diff(arr["pos"], axis=0), axis=2).max()),
            "states_first_frame": np.bincount(bs[0], minlength=5).tolist(),
            "states_last_frame": np.bincount(bs[-1], minlength=5).tolist(),
            "states_seen": sorted(int(s) for s in np.unique(bs)),
            "roosted_at_end_fraction": float((bs[-1] == ROOST).mean()),
        }
    )
    extra = {
        "scene": scene,
        "viewer_scene": entry["viewer"],
        "clock": {**clock.describe(), "date": args.date, "local_hours_first_last": local},
        "light": np.round(light, 4).tolist(),
        "flocks": flocks,
        "fields": fields_info,
        "geometry": {"source": str(args.geometry)},
        "checks": checks,
        "config": json.loads(json.dumps(results[0]["config"], default=str)),
        "wall_s": round(time.time() - started, 1),
        "claim": (
            "Illustrative bird-flock replay on the scene geometry, driven by the scene's published "
            "2-D wind / pollution / temperature slices and its sun clock; heuristic site placement, "
            "not ecological validation."
        ),
    }
    manifest = write_replay(out_dir, arr["pos"], arr["vel"], arr["bank"], bs, t, extra)
    config_path = storage.metadata(scene) / "configs" / "bird_visualization.json"
    viewer_config = write_viewer_config(
        config_path,
        out_dir / "bird_replay.json",
        f"roost-to-roost day, {len(flocks)} flocks",
        args.seed,
    )
    if args.npz:
        np.savez_compressed(work / "trajectories.npz", time=t, light=light, **arr)
    print(json.dumps({"replay": str(out_dir), "viewer_config": str(config_path), **checks}))
    print(json.dumps({k: manifest["files"][k]["bytes"] for k in manifest["files"]}), viewer_config)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare-geometry", help="bake + voxelise the scene GLB (2 m) + land cover")
    p.add_argument("--scene", required=True)
    p.add_argument("--glb", required=True, type=Path, help="the scene's city GLB (as published)")
    p.add_argument("--supplement", type=Path, action="append", help="extra GLB merged in")
    p.add_argument("--out", required=True, type=Path, help="new geometry directory")
    p.add_argument("--cell", type=int, default=2, choices=(1, 2, 4))
    p = sub.add_parser("fetch-fields", help="download the scene's published field frames")
    p.add_argument("--scene", required=True)
    p.add_argument("--dest", required=True, type=Path)
    p.add_argument(
        "--base-url", default=None, help="published site root (default: the public site)"
    )
    p = sub.add_parser("fetch-model", help="download the scene's city GLB (+ supplement)")
    p.add_argument("--scene", required=True)
    p.add_argument("--fields", required=True, type=Path, help="fetch-fields output (scene.json)")
    p.add_argument("--dest", required=True, type=Path)
    p.add_argument(
        "--base-url", default=None, help="published site root (default: the public site)"
    )
    p.add_argument("--resources-url", default=None, help="resource catalogue root override")
    p = sub.add_parser("run", help="run the birds and write the viewer replay")
    p.add_argument("--scene", required=True)
    p.add_argument("--geometry", required=True, type=Path, help="prepare-geometry output")
    p.add_argument(
        "--fields", required=True, type=Path, help="scene folder with scene.json + physics"
    )
    p.add_argument("--flocks", type=int, default=4, help="independent flocks (one roost each)")
    p.add_argument("--n-birds", type=int, default=300, help="birds per flock")
    p.add_argument(
        "--route-block-fraction",
        type=float,
        default=0.0,
        help="share of an 8 m routing cell that must be solid to block it: 0 = any voxel (default), "
        "0.5 = half (sites beside towers stay reachable)",
    )
    p.add_argument(
        "--workers", type=int, default=None, help="flocks run in parallel (default min(4, cpus))"
    )
    p.add_argument("--dt", type=float, default=None, help="default: SimConfig.dt (0.05 s)")
    p.add_argument("--duration", type=float, default=None, help="default: span of the wind frames")
    p.add_argument("--frame-dt", type=float, default=None, help="replay frame spacing (s)")
    p.add_argument("--date", default="2026-12-21", help="sun date (winter = murmuration season)")
    p.add_argument("--latitude", type=float, default=None)
    p.add_argument("--longitude", type=float, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--version", default=None, help="input folder name (default birds_YYYYMMDD)")
    p.add_argument("--out", type=Path, default=None, help="override the replay folder")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--npz", action="store_true", help="also keep full-precision trajectories")
    args = ap.parse_args(argv)
    commands = {
        "fetch-fields": cmd_fetch_fields,
        "fetch-model": cmd_fetch_model,
        "prepare-geometry": cmd_prepare_geometry,
        "run": cmd_run,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
