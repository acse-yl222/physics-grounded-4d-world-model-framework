"""Package the selected legacy corridor presentation without altering other scenes."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/visualization/corridor"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Export patch anchor changed: {old[:70]}")
    return text.replace(old, new)


def build(export, destination, data_url=None):
    destination.mkdir(parents=True, exist_ok=True)
    script = (SOURCE / "vendor/export.mjs").read_text()
    script = (
        'import {recordedSampler, advancePlayback} from "./replay.mjs";\nimport {installLighting} from "./lighting.mjs";\n'
        + script
    )
    script = "let corridorBuilding = true;\n" + script
    script = replace_once(
        script, "wa(rh.overview.c, rh.overview.d)", "wa(rh.south_ken.c, rh.south_ken.d)"
    )
    script = replace_once(
        script, "_n.target.copy(ih(...rh.overview.c))", "_n.target.copy(ih(...rh.south_ken.c))"
    )
    script = replace_once(script, "Bo.render()", "!corridorBuilding && Bo.render()")
    script = replace_once(
        script,
        '((dt("progress").hidden = !0), kG());',
        '((corridorBuilding = false), (en = true), (dt("progress").hidden = !0), kG());',
    )
    script = replace_once(script, "S = _G(t, o.length, r.dt);", "S = recordedSampler(t, r.dt);")
    start = script.index("    for (let A = 0; A < S.length; A++) {", script.index("function NM("))
    end = script.index("      ((j -= Math.cos(E) * C.half),", start)
    script = (
        script[:start]
        + """    for (const sample of S(U)) {
      const A = sample.id, C = s[o[A]];
      if (!C) continue;
      let j = sample.x, Y = sample.y, E = sample.heading;
"""
        + script[end:]
    )
    script = replace_once(
        script,
        '(Qt.t = (Qt.t + e * Number(dt("t-speed").value)) % po.duration)',
        """(Qt.t = advancePlayback(Qt.t, e, Number(dt("t-speed").value), po.duration),
       Qt.dirty = true,
       Qt.t >= po.duration && (Qt.playing = false, dt("t-play").textContent = "Replay", dt("t-play").setAttribute("aria-pressed", "false")))""",
    )
    script = replace_once(
        script,
        "((Qt.playing = !Qt.playing),",
        "((Qt.t >= po.duration && (Qt.t = 0)), (Qt.last = performance.now()), (Qt.playing = !Qt.playing),",
    )
    start = script.index("            if (gi) {", script.index("  async function Y(l)"))
    end = script.index("            return xm(", start)
    script = script[:start] + script[end:]
    script = replace_once(
        script,
        "  async function Y(l) {\n    try {",
        """  async function Y(l) {
    Bt("traffic").visible = false;
    dt("t-clock").textContent = "Loading recorded traffic…";
    try {""",
    )
    script = replace_once(
        script,
        "o === l && mw(M, r);",
        """if (o === l) {
        Qt.t = 0;
        mw(M, r);
        Bt("traffic").visible = document.querySelector('[data-layer="traffic"]').checked;
        en = true;
      }""",
    )
    script = replace_once(
        script,
        "console.warn(`playback ${l}: ${M.message}`);",
        """C.delete(l);
      if (o === l) dt("t-clock").textContent = "Traffic unavailable — select a period to retry";
      console.warn(`playback ${l}: ${M.message}`);""",
    )
    start = script.index("function zG(i) {")
    end = script.index("function mw(", start)
    script = (
        script[:start]
        + """function zG(i) {
  return `Recorded SUMO mesoscopic simulation, not observed vehicle trajectories. ${i.vehicles.length.toLocaleString()} selected vehicles; ${i.frames} frames at ${i.dt} s. Exact positions at recorded times, linear interpolation only between adjacent samples. Missing samples and jumps over 55 m/s are hidden between frames. No lane reconstruction or queue compression. Traffic demand and congestion remain unvalidated; source model flow is about half the observed counts. Ground height follows the exported road surface; bridge assignment is not recorded.`;
}
"""
        + script[end:]
    )
    script += "\ninstallLighting({scene:Lo, sun:Rm, renderer:vr, direction:FG, controls:_n, redraw:()=>{en=true;}});\n"
    if data_url:
        if not re.fullmatch(
            r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/[^?#]+", data_url
        ):
            raise ValueError("Use an immutable GitHub resource URL")
        script = (
            "const corridorDataURL = "
            + json.dumps(data_url.rstrip("/") + "/")
            + ";\n"
            + "const fetch = (url, options) => globalThis.fetch(typeof url === 'string' && url.startsWith('data/') ? corridorDataURL + url.slice(5) : url, options);\n"
            + script
        )
    (destination / "app.mjs").write_text(script)
    for name in ("replay.mjs", "solar.mjs", "lighting.mjs"):
        shutil.copy2(SOURCE / name, destination / name)
    shell = (SOURCE / "vendor/shell.html").read_text()
    shell = shell.replace("</body>", '<script type="module" src="./app.mjs"></script></body>')
    shell = shell.replace('value="1">1×', 'value="1" selected>1×').replace(
        'value="4" selected', 'value="4"'
    )
    shell = shell.replace(
        '<div class="credit">', '<div class="credit"><a href="../../">All scenes</a> · '
    )
    (destination / "index.html").write_text(shell)
    # Explicitly selected export only; no workspace/cache/history directories copied.
    selected = []
    for path in sorted((export / "data").iterdir()):
        if path.is_file():
            target = destination / "data" / path.name
            if not data_url:
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(path, target)
            selected.append(
                {
                    "path": "data/" + path.name,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    (destination / "resources.json").write_text(
        json.dumps(
            {
                "scene_id": "imperial_corridor",
                "representation": "legacy presentation export; not a protocol simulation run",
                "source": "Imperial Corridor 3D (Copy).zip, supplied by user",
                "data_url": data_url,
                "assets": selected,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Packaged {len(selected)} source assets into {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--data-url", help="Immutable raw GitHub revision data directory; omit for local data"
    )
    args = parser.parse_args()
    build(args.export, args.destination, args.data_url)
