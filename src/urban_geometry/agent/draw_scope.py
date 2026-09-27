"""Standalone vector inventory map from licensed footprint data."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root, agent_src, authoring_path
import json,html
from pathlib import Path
root=authoring_path();d=json.loads((root/'geometry.json').read_text());c=json.loads((root/'coordinate_contract.json').read_text())['source_xy_to_campus_affine'];camp=json.loads((root.parent/'references/campus/campus_geometry.json').read_text());land=json.loads((root/'docs/inventory.json').read_text())['landmarks']
W=1100;H=1200;scale=.93;x0=-395;ymax=530
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="#f7f6f1"/>','<style>text{font-family:Arial,sans-serif;fill:#20323b}.label{font-size:16px;font-weight:600;paint-order:stroke;stroke:#f7f6f1;stroke-width:5;stroke-linejoin:round}</style>','<text x="40" y="40" font-size="28" font-weight="700">South Kensington · campus + museums</text>','<text x="40" y="69" font-size="16">Scope inventory — whole intersecting buildings retained</text>']
def xy(p,source=True):
 x,y=p
 if source:x,y=c[0][0]*x+c[0][1]*y+c[0][2],c[1][0]*x+c[1][1]*y+c[1][2]
 return (x-x0)*scale+50,(ymax-y)*scale+105

def draw(gs,color,source=True,stroke='#f7f6f1'):
 for g in gs:
  path=' '.join('M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(p,source) for p in r])+' Z' for r in [g['outer']]+g.get('holes',[]))
  svg.append(f'<path d="{path}" fill="{color}" fill-rule="evenodd" stroke="{stroke}" stroke-width=".6"/>')
for f in json.loads((root/'context.json').read_text())['features']:draw(f['geometry'],{'road':'#d3d7d7','path':'#e3e0d6','park':'#e1e9d6','water':'#bed6dc'}[f['kind']])
for f in d['buildings']:draw(f['geometry'],'#407e96' if f['id'] in land else '#b8b9b4')
for f in camp['buildings']:draw(f['geometry'],'#c5a361',False)
labels={'way-372860405':('Royal Albert Hall',-135,345),'way-27765400':('Royal College of Music',-150,100),'way-27765411':('Science Museum',-195,-202),'way-24436446':('Natural History Museum',-150,-324),'relation-29795':('Victoria and Albert Museum',220,-300)}
for oid,(text,x,y) in labels.items():
 f=next(f for f in d['buildings'] if f['id']==oid);pts=[xy(p) for g in f['geometry'] for p in g['outer']];cx=sum(v[0] for v in pts)/len(pts);cy=sum(v[1] for v in pts)/len(pts);tx,ty=xy((x,y),False)
 svg.append(f'<path d="M {cx:.1f},{cy:.1f} L {tx:.1f},{ty-6:.1f}" stroke="#407e96" fill="none"/>');svg.append(f'<text x="{tx:.1f}" y="{ty:.1f}" class="label">{html.escape(text)}</text>')
tx,ty=xy((-100,30),False);svg.append(f'<text x="{tx}" y="{ty}" class="label">Imperial campus (inherited)</text>')
svg.extend(['<path d="M 1030,150 L 1030,110 L 1024,123 M 1030,110 L 1036,123" stroke="#20323b" fill="none" stroke-width="2"/>','<text x="1023" y="100" font-size="17">N</text>'])
for i,(color,label) in enumerate([('#c5a361','42 inherited campus records'),('#407e96','5 landmark modules'),('#b8b9b4','Surrounding mapped buildings / parts; individual refinement pending')]):
 y=1100+i*27;svg.append(f'<rect x="40" y="{y-13}" width="18" height="18" fill="{color}"/><text x="70" y="{y}" font-size="16">{label}</text>')
svg.append('<text x="40" y="1190" font-size="12">© OpenStreetMap contributors · ODbL · Estimated local frame, not a surveyed boundary. 2026-09-09</text></svg>')
(root/'docs/expansion_scope.svg').write_text('\n'.join(svg))
