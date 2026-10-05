"""`img2city` command-line entry point.

One front door over the pipeline stages.  Every subcommand is a thin alias
for a module's own argparse `main()`, so ``img2city make-city --out X`` and
``python -m img2city.city.make_city --out X`` are the same thing; the module
keeps the detailed `--help`.

    img2city make-city --query "South Kensington" --span 400 --out data/city_sk
    img2city generate  --data data/queens_tower --backend sdk --max-iters 6
    img2city webapp
    img2city demo      --max-iters 40
"""
from __future__ import annotations
import importlib
import sys

# subcommand -> (module, one-line help)
COMMANDS = {
    # end-to-end
    "make-city":      ("img2city.city.make_city",
                       "bbox/place -> verified 3D city model (the one-command pipeline)"),
    "district":       ("img2city.city.district", "agent recovery, generation, district assembly and review"),
    # single building
    "generate":       ("img2city.building.generate",
                       "image(s) -> editable parametric building in live Blender"),
    "typology":       ("img2city.building.typology", "per-building typology card selection"),
    "facade-colors":  ("img2city.building.facade_colors", "photo-sampled part colours"),
    "glass-agent":    ("img2city.building.glass_agent", "curtain-wall appearance from the photo"),
    "courtyards":     ("img2city.building.courtyard_agent", "recover courtyards OSM lacks"),
    # imagery
    "fetch":          ("img2city.imagery.maps_fetch", "satellite + street view for one building"),
    "acquire-view":   ("img2city.imagery.acquire_view", "ring-sample Street View, agent picks the shot"),
    "rescue-imagery": ("img2city.imagery.rescue_imagery", "replace placeholder photos with real ones"),
    "facade-clean":   ("img2city.imagery.facade_clean", "select + clean facade references"),
    "facade-facts":   ("img2city.imagery.facade_facts", "OWLv2 window/door facts from the photo"),
    "synth-views":    ("img2city.imagery.synth_views", "synthetic auxiliary views (weak refs)"),
    # city block
    "lod1":           ("img2city.city.lod1", "OSM footprints -> LoD1 Blender scene"),
    "city-generate":  ("img2city.city.generate", "agent spec per building + block assembly / refine"),
    "quality":        ("img2city.city.quality", "agent acceptance with current scene evidence"),
    "heights":        ("img2city.city.height_check", "LiDAR height check (--apply writes back)"),
    "functions":      ("img2city.city.building_function", "Places POI -> building function"),
    "regress":        ("img2city.city.render_regress", "no-regression fingerprint gate"),
    "compare-top":    ("img2city.city.compare_top", "aligned satellite vs top-render figure"),
    # scene layers
    "scene-assets":   ("img2city.scene.assets", "trees / roads / green / furniture layer"),
    "road-graph":     ("img2city.scene.road_graph", "directed carriageway graph + restrictions"),
    "vehicles":       ("img2city.scene.vehicles", "detect + place vehicles (torch)"),
    "traffic-sim":    ("img2city.scene.traffic_sim", "deterministic traffic animation"),
    "traffic-audit":  ("img2city.scene.traffic_audit", "vehicle collision audit"),
    "shops":          ("img2city.scene.shops", "street-side shop units from Places"),
    "shop-agent":     ("img2city.scene.shop_agent", "agent reads shopfront appearance"),
    # library growth
    "lib-learn":      ("img2city.library.learn", "mine unmet demands -> missing vocabulary"),
    "lib-grow":       ("img2city.library.grow", "agent authors a part, three gates"),
    "lib-audit":      ("img2city.library.audit", "parts-library manifest"),
    # learned prior
    "prior-dataset":  ("img2city.prior.gen_dataset", "synthetic (image, params) dataset via MCP"),
    "prior-train":    ("img2city.prior.train", "train the image -> params regressor"),
    "prior-predict":  ("img2city.prior.predict", "image -> params -> build description"),
    # demo / harness / web
    "demo":           ("img2city.agent.harness", "offline render->evaluate->refine demo (--demo)"),
    "webapp":         ("img2city.webapp.server", "local demo web app (http://localhost:8000)"),
    "doctor":         ("img2city.doctor", "what is installed / present / reachable on this machine"),
}


def _usage() -> str:
    w = max(len(k) for k in COMMANDS)
    lines = ["usage: img2city <command> [args...]", "",
             "commands (each has its own --help):"]
    for k, (_, h) in COMMANDS.items():
        lines.append(f"  {k:<{w}}  {h}")
    lines += ["", "python -m img2city.<module> ... is always equivalent."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_usage())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd not in COMMANDS:
        print(f"img2city: unknown command '{cmd}'\n\n{_usage()}", file=sys.stderr)
        return 2
    modname = COMMANDS[cmd][0]
    if cmd == "demo" and "--demo" not in rest and "--live" not in rest:
        rest = ["--demo", *rest]
    mod = importlib.import_module(modname)
    # the module's argparse reads sys.argv; present it as if run via -m
    sys.argv = [modname.rsplit(".", 1)[-1] + ".py", *rest]
    if hasattr(mod, "main"):
        r = mod.main()
        return int(r or 0)
    # module-level script (no main()): re-exec as `python -m`
    import runpy
    runpy.run_module(modname, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
