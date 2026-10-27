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


def build(export, destination, data_url=None, micro_url=None):
    destination.mkdir(parents=True, exist_ok=True)
    script = (SOURCE / "vendor/export.mjs").read_text()
    script = (
        'import {recordedSampler, advancePlayback} from "./replay.mjs";\nimport {installLighting} from "./lighting.mjs";\n'
        + script
    )
    script = (
        'import {loadTraffic} from "./traffic-data.mjs";\nconst corridorMicroURL = '
        + json.dumps(micro_url)
        + ';\nwindow.corridorTrafficMode = corridorMicroURL ? "rebuilt" : "recorded";\n'
        + script
    )
    script = (
        'import {createVehicles} from "./vehicles.mjs";\nlet corridorBuilding = true, corridorShadows = true;\n'
        + script
    )
    script = replace_once(
        script, "wa(rh.overview.c, rh.overview.d)", "wa(rh.south_ken.c, rh.south_ken.d)"
    )
    script = replace_once(
        script, "_n.target.copy(ih(...rh.overview.c))", "_n.target.copy(ih(...rh.south_ken.c))"
    )
    script = replace_once(script, "Bo.render()", "!corridorBuilding && Bo.render()")
    script = replace_once(
        script,
        '_n.addEventListener("change", () => (en = !0))',
        '_n.addEventListener("change", () => (vr.shadowMap.needsUpdate = true, en = !0))',
    )
    script = replace_once(
        script,
        "B.castShadow = a && OG.has(S)",
        'B.castShadow = (a || corridorShadows) && OG.has(S) && (a || S !== "traffic")',
    )
    script = replace_once(script, "B.receiveShadow = a", "B.receiveShadow = a || corridorShadows")
    script = replace_once(
        script,
        "i.shadowMap.type = fa",
        "i.shadowMap.autoUpdate = a, i.shadowMap.needsUpdate = true, i.shadowMap.type = fa",
    )

    script = replace_once(
        script, "i.shadowMap.enabled = a", "i.shadowMap.enabled = a || corridorShadows"
    )
    script = replace_once(script, "r.castShadow = a", "r.castShadow = a || corridorShadows")
    script = replace_once(
        script,
        "r.shadow.mapSize.set(4096, 4096)",
        "r.shadow.mapSize.set(a ? 4096 : 2048, a ? 4096 : 2048)",
    )
    script = replace_once(
        script,
        "a && p(y, S)",
        "(a || corridorShadows) && (p(y, S), i.shadowMap.needsUpdate = true)",
    )
    script = replace_once(
        script,
        "a ? (v(), s.render()) : i.render(e, n)",
        "((a || corridorShadows) && v(), a ? s.render() : i.render(e, n))",
    )

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
        "((po && Qt.t >= po.duration && (Qt.t = 0)), (Qt.last = performance.now()), (Qt.playing = !Qt.playing),",
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
    script = replace_once(script, ": NM(i, e, gs)", ": createVehicles(Jn, i, gs)")
    script = replace_once(
        script,
        "po.group.traverse((n) => n.isInstancedMesh && n.dispose())",
        "po.dispose ? po.dispose() : po.group.traverse((n) => n.isInstancedMesh && n.dispose())",
    )
    start = script.index("  async function Y(l) {")
    end = script.index("  function E(l) {", start)
    script = (
        script[:start]
        + """  async function Y(l) {
    const mode=window.corridorTrafficMode, key=mode+":"+l;
    Bt("traffic").visible=false;
    dt("t-clock").textContent="Loading traffic…";
    try {
      if(!C.has(key)) C.set(key, mode === "rebuilt"
        ? loadTraffic(corridorMicroURL+"/"+l, "traffic.wasm")
        : xm("data", `traffic-${l}.wasm`, `traffic_${l}.json`));
      const result=await C.get(key);
      if(o===l && window.corridorTrafficMode===mode) {
        Qt.t=0;mw(result,r);
        Bt("traffic").visible=document.querySelector('[data-layer="traffic"]').checked;
        en=true;
      }
    } catch(error) {
      C.delete(key);
      if(o===l && window.corridorTrafficMode===mode) dt("t-clock").textContent="Traffic unavailable — select a period to retry";
      console.warn(error);
    }
  }
"""
        + script[end:]
    )
    start = script.index("function zG(i) {")
    end = script.index("function mw(", start)
    script = (
        script[:start]
        + """function zG(i) {
  if(i.provenance?.rebuilt) return `Experimental microscopic SUMO rebuild: 25% of eligible source routes, regenerated signals and conservative junction reservations; not measured or count-calibrated traffic. ${i.vehicles.length} vehicles in this replay, 0 detected collisions and 0 teleports in validation. Vehicles use simulated elevation and class-specific dimensions. Bus service schedules are not reconstructed. Traffic-state overlays still describe the original model, not this experiment.`;
  return `Recorded SUMO mesoscopic simulation, not observed vehicle trajectories. ${i.vehicles.length.toLocaleString()} selected vehicles; ${i.frames} frames at ${i.dt} s. Exact positions at recorded times, linear interpolation only between adjacent samples. Missing samples and jumps over 55 m/s are hidden between frames. No lane reconstruction or queue compression. Traffic demand and congestion remain unvalidated; source model flow is about half the observed counts. Ground height follows the exported road surface; bridge assignment is not recorded.`;
}
"""
        + script[end:]
    )
    script += "\ninstallLighting({scene:Lo, sun:Rm, renderer:vr, direction:FG, controls:_n, setShadows:(enabled)=>{corridorShadows=enabled;Bo.setEnabled(Bo.enabled);en=true;}, redraw:()=>{en=true;}});\n"
    script += """
let vehiclePointer=null;
$o.addEventListener('pointerdown',event=>{vehiclePointer=[event.clientX,event.clientY];},{capture:true});
$o.addEventListener('pointerup',event=>{
  if(!vehiclePointer || Math.hypot(event.clientX-vehiclePointer[0],event.clientY-vehiclePointer[1])>5 || !Bt('traffic').visible) return;
  const rect=$o.getBoundingClientRect(),ray=new Jn.Raycaster();
  ray.setFromCamera(new Jn.Vector2((event.clientX-rect.left)/rect.width*2-1,1-(event.clientY-rect.top)/rect.height*2),zt);
  const vehicle=po?.pick?.(ray);if(!vehicle)return;
  event.stopImmediatePropagation();
  const title=document.createElement('h2'),body=document.createElement('p');title.textContent=vehicle.type.toUpperCase();
  body.textContent=`${vehicle.id} · ${vehicle.spec.length} × ${vehicle.spec.width} m (assumed dimensions) · ${vehicle.speed===undefined?'speed unavailable in original export':(vehicle.speed*3.6).toFixed(1)+' km/h simulated'} · ${vehicle.z===undefined?'height follows road surface':vehicle.z.toFixed(1)+' m inherited lane elevation'}`;
  dt('info').replaceChildren(title,body);
},{capture:true});
if(corridorMicroURL) {
  const label=document.createElement('label');label.className='row';label.textContent='Vehicle model ';
  const select=document.createElement('select');select.id='traffic-model';select.setAttribute('aria-label','Vehicle simulation');
  select.innerHTML='<option value="rebuilt">Rebuilt micro · experimental</option><option value="recorded">Original SUMO · recorded</option>';
  label.append(select);dt('traffic').prepend(label);
  select.addEventListener('change',()=>{window.corridorTrafficMode=select.value;document.querySelector('#periods [aria-pressed="true"]')?.click();});
}
"""
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
    for name in ("replay.mjs", "solar.mjs", "lighting.mjs", "vehicles.mjs", "traffic-data.mjs"):
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
    parser.add_argument(
        "--micro-url", help="Base URL containing validated am_peak/inter_peak/pm_peak run folders"
    )
    args = parser.parse_args()
    build(args.export, args.destination, args.data_url, args.micro_url)
