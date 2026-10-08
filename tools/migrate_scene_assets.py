"""Move local scene assets into project ownership, retaining a verifiable file ledger."""

from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "south_kensington": ("south_ken", "legacy_web"),
    "white_city": ("white_city", "legacy_web"),
    "region": ("windfarm", "region"),
    "windfarm_2m": ("windfarm", "mac_2m"),
    "windfarm_crop": ("windfarm", "crop"),
    "actuator_lab": ("actuator_lab", "fullgradient"),
    "actuator_lab_halfgradient": ("actuator_lab", "halfgradient"),
}


def main():
    ledger = ROOT / "docs/framework/scene-migration.json"
    if ledger.exists():
        raise SystemExit("Scene migration already recorded")
    moves = []
    files = []

    def move(old, new):
        source, target = ROOT / old, ROOT / new
        if target.exists():
            raise ValueError(f"Destination exists: {new}")
        entries = []
        paths = sorted(source.rglob("*")) if source.is_dir() else [source]
        for p in paths:
            if p.is_symlink():
                entries.append(
                    {
                        "old": str(p.relative_to(ROOT)),
                        "new": str(
                            (
                                target / p.relative_to(source) if source.is_dir() else target
                            ).relative_to(ROOT)
                        ),
                        "link": str(p.readlink()),
                    }
                )
            elif p.is_file():
                entries.append(
                    {
                        "old": str(p.relative_to(ROOT)),
                        "new": str(
                            (
                                target / p.relative_to(source) if source.is_dir() else target
                            ).relative_to(ROOT)
                        ),
                        "bytes": p.stat().st_size,
                        "inode": p.stat().st_ino,
                        "device": p.stat().st_dev,
                    }
                )
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        for record in entries:
            p = ROOT / record["new"]
            if "link" in record:
                assert p.is_symlink() and str(p.readlink()) == record["link"]
            else:
                assert (p.stat().st_ino, p.stat().st_dev, p.stat().st_size) == (
                    record["inode"],
                    record["device"],
                    record["bytes"],
                )
        moves.append({"old": old, "new": new})
        files.extend(entries)
        ledger.write_text(
            json.dumps({"moves": moves, "files": files, "state": "in progress"}, indent=2) + "\n"
        )

    # Export scripts belong to code even when the old tree put them next to data.
    for path in sorted((ROOT / "visualizer/scenes").glob("*/tools")):
        move(str(path.relative_to(ROOT)), f"src/visualization/adapters/legacy/{path.parent.name}")
    if (ROOT / "visualizer/scenes/tools").exists():
        move("visualizer/scenes/tools", "src/visualization/adapters/legacy/shared")
    for source in sorted((ROOT / "visualizer/scenes").iterdir()):
        if not source.is_dir():
            continue
        name = source.name
        scene, run = ALIASES.get(
            name,
            ("windfarm", name.removeprefix("windfarm_"))
            if name.startswith("windfarm_")
            else (name, "legacy_web"),
        )
        move(str(source.relative_to(ROOT)), f"project/{scene}/runs/{run}")
    for source in sorted((ROOT / "input").iterdir()):
        if not source.is_dir():
            continue
        scene = source.name
        if (source / "config.json").exists():
            move(
                str((source / "config.json").relative_to(ROOT)),
                f"project/{scene}/configs/pipeline.json",
            )
        if any(source.iterdir()):
            move(str(source.relative_to(ROOT)), f"project/{scene}/input")
        else:
            source.rmdir()
    for source in sorted((ROOT / "configs").iterdir()):
        scene = "south_ken" if source.name == "core008" else source.name
        move(str(source.relative_to(ROOT)), f"project/{scene}/configs/legacy")
    (ROOT / "configs").rmdir()
    if (ROOT / "input/README.md").exists():
        move("input/README.md", "docs/framework/legacy-input.md")
    (ROOT / "input").rmdir()
    for name in ("white_city_9km2_compressed.glb", "white_city_9km2_compressed_162MB.glb"):
        move(name, f"project/white_city/input/original_root/{name}")
    ledger.write_text(
        json.dumps(
            {"moves": moves, "files": files, "state": "moved; same filesystem identity verified"},
            indent=2,
        )
        + "\n"
    )
    print(f"Moved {len(moves)} groups, preserved {len(files)} file identities.")


if __name__ == "__main__":
    main()
