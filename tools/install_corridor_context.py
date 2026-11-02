"""Install the native-grid presentation adapter into a retained local viewer."""
from pathlib import Path
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('destination',type=Path);a=p.parse_args();out=a.destination
shutil.copy2(Path(__file__).resolve().parents[1]/'src/visualization/shared/corridor-context.js',out/'viewer/3d/corridor-context.js')
f=out/'viewer/3d/main.js';s=f.read_text();s=s.replace("import { createDetailTiles } from './complete-detail-tiles.js';", "import { createDetailTiles } from './complete-detail-tiles.js';\nimport { createCorridorContext } from './corridor-context.js';")
s=s.replace('const SCENE = await loadScene();', '''const SCENE = await loadScene();
if (new URLSearchParams(location.search).get('wind_mode') === 'history' && SCENE.wind_history) {
  SCENE.layers.wind = SCENE.wind_history;
  SCENE.masks.solid_wind.file = 'masks/wind_history_invalid.npy';
}''')
s=s.replace('for (const k of Object.keys(LAYERS)) LG[k] = gridOf(LAYERS[k].cell_m ?? CELL);', 'for (const k of Object.keys(LAYERS)) LG[k] = {...gridOf(LAYERS[k].cell_m ?? CELL), dx: LAYERS[k].offset_x_m ?? 0, dz: LAYERS[k].offset_z_m ?? 0};')
s=s.replace('mesh.position.set(CX, y, CZ);','mesh.position.set(CX + (g.dx ?? 0), y, CZ + (g.dz ?? 0));')
s=s.replace('X0 + ax * WG.cell','X0 + (WG.dx ?? 0) + ax * WG.cell').replace('X0 + bx * WG.cell','X0 + (WG.dx ?? 0) + bx * WG.cell').replace('ZS - ay * WG.cell','ZS + (WG.dz ?? 0) - ay * WG.cell').replace('ZS - by * WG.cell','ZS + (WG.dz ?? 0) - by * WG.cell')
s=s.replace('(hit.x - X0) / g.cell','(hit.x - X0 - (g.dx ?? 0)) / g.cell').replace('(ZS - hit.z) / g.cell','(ZS + (g.dz ?? 0) - hit.z) / g.cell')
s=s.replace("ui.lGround.checked = ui.lTrees.checked = phase === 'flood' || phase === 'solar';", "ui.lGround.checked = true;")
s=s.replace('ui.lGround.checked = false;', 'ui.lGround.checked = true;')
s=s.replace('let detailTiles = null;', 'let corridorContext = null;\nlet contextStarted = false;\nlet detailTiles = null;')
s=s.replace('detailTiles?.update(now);', '''detailTiles?.update(now);
  if (!contextStarted && model.children.length && SCENE.corridor_context) {
    contextStarted = true;
    createCorridorContext({scene, config:SCENE.corridor_context, url:SCENE.url, onChange:invalidate})
      .then(value => {corridorContext=value; window.corridorContext=value; invalidate();})
      .catch(error => {console.error(error); document.querySelector('#corridor-traffic-time').textContent = 'Context failed: ' + error.message;});
  }
  corridorContext?.tick(Math.min(0.25, Math.max(0, (now-last)/1000)));''')
f.write_text(s)
f=out/'viewer/3d/index.html';s=f.read_text()
# Lower field opacities expose the new ground map without changing field values.
import re
for name,val in [('wind','.55'),('temp','.55'),('solar','.5'),('poll','.6'),('flood','.7')]:
 s=re.sub(r'(<input[^>]*id="o-'+name+r'"[^>]*value=")[^"]+',r'\g<1>'+val,s)
s=s.replace('Ground / roads','Ground / roads / water');f.write_text(s)
f=out/'serve.py';s=f.read_text().replace('url = f"http://localhost:{port}/viewer/3d/"','url = f"http://localhost:{port}/viewer/3d/?scene=imperial_corridor_8km&pose=campus&fields=1&phase=wind&step=1&lite=0"');f.write_text(s)
