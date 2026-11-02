"""Add quantitative colour-scale controls to an existing native corridor viewer."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('viewer_root',type=Path)
a=p.parse_args()
source=Path(__file__).resolve().parents[1]/'src/visualization/shared/field-colorbar.mjs'
main=a.viewer_root/'viewer/3d/main.js'
s=main.read_text()
if "import { installColorbars }" not in s:
    changes={'const layerInvalid = {};':'let colorbars = null;\nconst layerInvalid = {};',
             'function repaint() {':'function repaint() {\n  colorbars?.resetLegends();',
             'window.viewer = {':"if (SCENE.corridor_context) { colorbars = installColorbars({layers:LAYERS,repaint}); window.fieldColorbars=colorbars; }\nwindow.viewer = {"}
    for fn,key,plane in [('paintWind','wind','windPlane'),('paintTemperature','temp','tempPlane'),('paintFlood','flood','floodPlane'),('paintSolar','solar','solarPlane'),('paintPollution','poll','pollPlane')]:
        arg='uv' if key=='wind' else 'vals'
        value='i => Math.hypot(uv[i],uv[count+i],uv[2*count+i])' if key=='wind' else 'i => vals[i]'
        valid={'wind':'i => !solidWind?.[i]','temp':'i => !fpFor(LG.temp)?.[i] && (!studyArea || studyArea[i])','flood':'i => !layerInvalid.flood?.[i] && !fpFor(LG.flood)?.[i]','solar':'i => !layerInvalid.solar?.[i]','poll':'i => !layerInvalid.poll?.[i]'}[key]
        needle=f'function {fn}({arg}) {{'
        changes[needle]=needle+f"\n  const count = LG.{key}.w * LG.{key}.h;\n  if (colorbars?.paint('{key}', {arg}, {plane}, count, {value}, {valid})) return;"
    for old,new in changes.items():
        if s.count(old)!=1:raise SystemExit(f'Expected one integration point: {old}')
        s=s.replace(old,new)
    s="import { installColorbars } from './field-colorbar.mjs';\n"+s
    main.write_text(s)
(main.parent/'field-colorbar.mjs').write_text(source.read_text())
print('Colour-scale controls installed:',main)
