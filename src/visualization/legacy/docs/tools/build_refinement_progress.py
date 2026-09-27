#!/usr/bin/env python3
"""Build docs/refinement_progress.html: progress of the geometry refinement task (geometry/expansion/).

Reads only what the refinement task leaves behind (batch manifests, progress.json, remaining_frontier.json,
references/*/sources.json, output renders, reports/goal_usage_checkpoints.json) plus the OSM footprints in
geometry/completion/sources/osm_buildings.json for the base map. Re-run after new batches land:

    python3 docs/tools/build_refinement_progress.py

Coordinates: model metres, X east / Y north = EPSG:32630 minus (695238.304719173, 5709236.965026026).
"""
import datetime as dt
import glob
import json
import math
import os
import re
from collections import OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GE = os.path.join(ROOT, 'geometry', 'expansion')
OUT_HTML = os.path.join(ROOT, 'docs', 'refinement_progress.html')
THUMB_DIR = os.path.join(ROOT, 'docs', 'media', 'refined')
ORIGIN = (695238.304719173, 5709236.965026026)
CAMPUS = ((514, -324), (897, 9))          # model X range, Y range (Y = -Z of the viewer)
WINDOW = (370, -530, 1050, 190)           # x0, y0, x1, y1 of the map, model metres


# ------------------------------------------------------------------ WGS84 -> UTM zone 30 (Transverse Mercator, WGS84)
def utm30(lat, lon):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f); ep2 = e2 / (1 - e2); k0 = 0.9996; lon0 = math.radians(-3.0)
    phi, lam = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2; c = ep2 * math.cos(phi) ** 2; A = math.cos(phi) * (lam - lon0)
    e4, e6 = e2 * e2, e2 * e2 * e2
    M = a * ((1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
             + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi) - (35 * e6 / 3072) * math.sin(6 * phi))
    x = k0 * n * (A + (1 - t + c) * A ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * A ** 5 / 120) + 500000
    y = k0 * (M + n * math.tan(phi) * (A * A / 2 + (5 - t + 9 * c + 4 * c * c) * A ** 4 / 24 + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * A ** 6 / 720))
    return x - ORIGIN[0], y - ORIGIN[1]


# ------------------------------------------------------------------ inputs
def load(path):
    with open(path) as f:
        return json.load(f)


def clean_name(name):
    flags = []
    for pat, flag in ((r'\s*\(source (address|name) pending verification\)', 'name unverified'), (r'\s*\(source address\)', None), (r'\s*\(working label\)', 'working label'),
                      (r'\s*\(OSM way-\d+\)', 'no address'), (r'\s*\(historic .*?\)', None)):
        if re.search(pat, name):
            name = re.sub(pat, '', name)
            if flag: flags.append(flag)
    return name.strip(), flags


def evidence_for(batch_dir, slug):
    """Counts from references/<slug>/sources.json: inspected photos, text/listing sources."""
    cands = glob.glob(os.path.join(batch_dir, 'references', slug, 'sources.json')) or glob.glob(os.path.join(batch_dir, 'references', slug + '*', 'sources.json'))
    if not cands:
        return {'photos': 0, 'texts': 0, 'sources': 0}
    items = load(cands[0])
    if isinstance(items, dict):
        items = items.get('sources') or items.get('items') or []
    photos = sum(1 for s in items if isinstance(s, dict) and 'photo' in str(s.get('kind', '')) and s.get('actually_inspected', True) is not False)
    texts = sum(1 for s in items if isinstance(s, dict) and str(s.get('kind', '')) in ('text', 'listing', 'description'))
    return {'photos': photos, 'texts': texts, 'sources': len(items)}


def mtime(path):
    return dt.datetime.fromtimestamp(os.path.getmtime(path))


progress = load(os.path.join(GE, 'progress.json'))
frontier = load(os.path.join(GE, 'remaining_frontier.json'))
completed_ids = set(frontier['completed_ids'])
pending = frontier['pending']
checkpoints = load(os.path.join(GE, 'reports', 'goal_usage_checkpoints.json')) if os.path.exists(os.path.join(GE, 'reports', 'goal_usage_checkpoints.json')) else []

batches = OrderedDict()   # key -> {label, delivered(dt|None), features[]}
# pilot
pilot = load(os.path.join(GE, 'feature.json'))
pilot_out = os.path.join(GE, 'output', 'kensington_gore_23_v1')
batches['pilot'] = {'label': 'Pilot', 'delivered': mtime(os.path.join(pilot_out, 'replacement.glb')) if os.path.exists(pilot_out) else None,
                    'features': [{'id': pilot['id'], 'slug': 'kensington_gore_23', 'name': pilot['name'], 'ring': pilot['ring'], 'area': None,
                                  'levels': pilot['levels'], 'height': pilot['height_m'], 'height_basis': pilot['height_basis'],
                                  'evidence': evidence_for(GE, 'kensington_gore_23'), 'render': os.path.join(pilot_out, 'front.png'),
                                  'flags': ['same-building photo not verified'], 'revised': False}]}
for mpath in sorted(glob.glob(os.path.join(GE, 'batch*', 'manifest.json'))) + sorted(glob.glob(os.path.join(GE, 'revision*', 'manifest.json'))):
    bdir = os.path.dirname(mpath); key = os.path.basename(bdir); man = load(mpath)
    outs = sorted(glob.glob(os.path.join(GE, 'output', key + '_v*')))
    glb = [g for o in outs for g in glob.glob(os.path.join(o, 'replacement.glb'))]
    delivered = mtime(glb[-1]) if glb else None
    revised = set(man.get('revised_ids', []))
    feats = []
    for f in man['features']:
        name, flags = clean_name(f['name'])
        renders = [r for o in outs for r in glob.glob(os.path.join(o, f['slug'] + '_front.png'))]
        feats.append({'id': f['id'], 'slug': f['slug'], 'name': name, 'ring': f['ring'], 'area': f.get('area_m2'), 'levels': f.get('levels'),
                      'height': f.get('height_m'), 'height_basis': f.get('height_basis', ''), 'evidence': evidence_for(bdir, f['slug']),
                      'render': renders[-1] if renders else None, 'flags': flags, 'revised': f['id'] in revised or key.startswith('revision')})
    label = 'Revision 27 Princes Gate' if key.startswith('revision') else 'Batch ' + key.replace('batch', '').lstrip('0')
    batches[key] = {'label': label, 'delivered': delivered, 'features': feats, 'scope': man.get('scope', '')}

# per-building record: first delivery wins for the map colour, later revisions noted
buildings = OrderedDict()
for key, b in batches.items():
    for f in b['features']:
        if f['id'] in buildings:
            buildings[f['id']]['revisions'].append(key)
            if f['render']: buildings[f['id']]['render'] = f['render']
            buildings[f['id']].update({k: f[k] for k in ('levels', 'height', 'height_basis') if f.get(k) is not None})
            continue
        rec = dict(f); rec['batch'] = key; rec['revisions'] = []
        rec['state'] = 'delivered' if (f['id'] in completed_ids and b['delivered']) else 'in_progress'
        buildings[f['id']] = rec
delivered = [r for r in buildings.values() if r['state'] == 'delivered']
in_progress = [r for r in buildings.values() if r['state'] == 'in_progress']

# pending buildings (frontier) that are not in a manifest yet: polygons from OSM
osm = load(os.path.join(ROOT, 'geometry', 'completion', 'sources', 'osm_buildings.json'))
osm_by_id = {}
for e in osm['elements']:
    if e['type'] == 'way' and 'geometry' in e:
        osm_by_id['way-%d' % e['id']] = [utm30(p['lat'], p['lon']) for p in e['geometry']]
    elif e['type'] == 'relation':
        outer = [m for m in e.get('members', []) if m.get('role') == 'outer' and 'geometry' in m]
        if outer: osm_by_id['relation-%d' % e['id']] = [utm30(p['lat'], p['lon']) for p in outer[0]['geometry']]
pending_recs = []
for p in pending:
    if p['id'] in buildings: continue
    pending_recs.append({'id': p['id'], 'name': ', '.join(p.get('names', [])) or p['id'], 'ring': osm_by_id.get(p['id']), 'status': p.get('status', ''), 'reason': p.get('reason', '')})

# projection check: a refined ring against its OSM footprint
check = None
for rec in delivered:
    if rec['id'] in osm_by_id:
        a = rec['ring']; b = osm_by_id[rec['id']]
        ca = (sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a)); cb = (sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b))
        check = (rec['name'], math.hypot(ca[0] - cb[0], ca[1] - cb[1])); break

# base map: OSM footprints in the window
x0, y0, x1, y1 = WINDOW
base = []
for oid, ring in osm_by_id.items():
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
    base.append(ring)

# ------------------------------------------------------------------ thumbnails
os.makedirs(THUMB_DIR, exist_ok=True)
try:
    from PIL import Image
    for rec in buildings.values():
        if rec['render'] and os.path.exists(rec['render']):
            out = os.path.join(THUMB_DIR, rec['slug'] + '.jpg')
            if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(rec['render']):
                im = Image.open(rec['render']).convert('RGB'); w = 360; im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                im.save(out, quality=80, optimize=True)
            rec['thumb'] = 'media/refined/' + rec['slug'] + '.jpg'
except ImportError:
    pass

# ------------------------------------------------------------------ numbers
times = sorted(b['delivered'] for k, b in batches.items() if b['delivered'] and k != 'pilot')
first, last = times[0], times[-1]
hours = (last - first).total_seconds() / 3600
n_run = sum(1 for r in delivered if r['batch'] != 'pilot')
n_batches = sum(1 for k in batches if k != 'pilot' and not k.startswith('revision') and batches[k]['delivered'])
area_total = sum(r['area'] or 0 for r in delivered)
cp = checkpoints[-1] if checkpoints else None
tok_per = (cp['goal_tokens_used'] / cp['completed_refinement_ids']) if cp else None
min_per = (cp['goal_elapsed_seconds'] / 60 / cp['completed_refinement_ids']) if cp else None
ev_photos = sum(1 for r in delivered if r['evidence']['photos'] > 0)
ev_texts = sum(1 for r in delivered if r['evidence']['texts'] > 0)
ev_none = sum(1 for r in delivered if r['evidence']['sources'] == 0)
now = dt.datetime.now()

# ------------------------------------------------------------------ SVG helpers
W, H = 660, 720
sx = W / (x1 - x0); sy = H / (y1 - y0)
def px(p): return (round((p[0] - x0) * sx, 1), round((y1 - p[1]) * sy, 1))
def poly(ring): return ' '.join('%g,%g' % px(p) for p in ring)

order = sorted(delivered, key=lambda r: batches[r['batch']]['delivered'])
rank = {r['id']: i for i, r in enumerate(order)}
STEPS = ['#c7dcf3', '#9dc0e6', '#6f9fd6', '#4a7fc4', '#2f62a8', '#1c4585']   # one hue, light -> dark by delivery order
def step_color(i):
    k = int(i / max(1, len(order)) * len(STEPS)); return STEPS[min(k, len(STEPS) - 1)]

svg = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Map of the refined buildings around the Imperial College campus, coloured by delivery order, with in-progress and pending buildings marked" xmlns="http://www.w3.org/2000/svg">']
svg.append('<defs><pattern id="hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--prog)" stroke-width="2"/></pattern></defs>')
svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="var(--map-bg)"/>')
svg.append('<g fill="var(--base-fill)" stroke="var(--base-stroke)" stroke-width="0.5">' + ''.join(f'<polygon points="{poly(r)}"/>' for r in base) + '</g>')
c0, c1 = px((CAMPUS[0][0], CAMPUS[1][1])), px((CAMPUS[0][1], CAMPUS[1][0]))
svg.append(f'<rect x="{c0[0]}" y="{c0[1]}" width="{c1[0]-c0[0]}" height="{c1[1]-c0[1]}" fill="none" stroke="var(--text-2)" stroke-dasharray="5 4" stroke-width="1"/>')
svg.append(f'<text x="{c0[0]+6}" y="{c0[1]+14}" font-size="11" fill="var(--text-2)" font-family="IBM Plex Mono, monospace" letter-spacing="1">CAMPUS RECTANGLE</text>')
svg.append('<g class="pending">' + ''.join(f'<polygon points="{poly(r["ring"])}" fill="none" stroke="var(--text-2)" stroke-width="1.4" stroke-dasharray="3 2"><title>{r["name"]} · pending: {r["status"].replace("_", " ")}</title></polygon>' for r in pending_recs if r['ring']) + '</g>')
svg.append('<g class="prog">' + ''.join(f'<polygon points="{poly(r["ring"])}" fill="url(#hatch)" stroke="var(--prog)" stroke-width="1.4"><title>{r["name"]} · in progress ({batches[r["batch"]]["label"]})</title></polygon>' for r in in_progress) + '</g>')
svg.append('<g class="done">' + ''.join(f'<polygon points="{poly(r["ring"])}" fill="{step_color(rank[r["id"]])}" stroke="var(--map-bg)" stroke-width="0.8" data-i="{rank[r["id"]]}"><title>{r["name"]} · {batches[r["batch"]]["label"]} · {batches[r["batch"]]["delivered"].strftime("%H:%M")}</title></polygon>' for r in order) + '</g>')
labels = [('Kensington Gore', 640, 150), ("Queen's Gate", 400, 40), ('Princes Gate', 930, 175), ('Princes Gardens', 900, -215), ('Princes Gate Mews', 930, -300), ("Queen's Gate Place Mews", 560, -505), ('Jay Mews', 560, -30), ('Imperial College campus', 700, -200)]
for t, x, y in labels:
    p = px((x, y)); svg.append(f'<text x="{p[0]}" y="{p[1]}" font-size="11" fill="var(--text-2)" text-anchor="middle" font-family="IBM Plex Sans, sans-serif">{t}</text>')
# scale bar 200 m
sb = px((x0 + 30, y0 + 30)); svg.append(f'<line x1="{sb[0]}" y1="{sb[1]}" x2="{sb[0] + 200 * sx:.1f}" y2="{sb[1]}" stroke="var(--text-1)" stroke-width="2"/><text x="{sb[0]}" y="{sb[1]-6}" font-size="11" fill="var(--text-2)" font-family="IBM Plex Mono, monospace">200 m</text>')
svg.append('</svg>')
map_svg = '\n'.join(svg)

# timeline: cumulative delivered vs time of day (step), batch markers
TW, TH, PL, PR, PT, PB = 900, 260, 46, 16, 16, 40
t_start = first.replace(minute=0, second=0, microsecond=0)
t_end = (max(last, now)).replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
def tx(t): return PL + (t - t_start).total_seconds() / (t_end - t_start).total_seconds() * (TW - PL - PR)
n_max = len(order) + len(in_progress) + len(pending_recs)
def ty(n): return PT + (TH - PT - PB) * (1 - n / n_max)
cum = sum(1 for r in delivered if r['batch'] == 'pilot')
pts = [(tx(t_start), ty(cum))]
events = []
for key, b in batches.items():
    if not b['delivered'] or key == 'pilot': continue
    new = [f for f in b['features'] if buildings[f['id']]['batch'] == key and buildings[f['id']]['state'] == 'delivered']
    pts.append((tx(b['delivered']), ty(cum))); cum += len(new); pts.append((tx(b['delivered']), ty(cum)))
    events.append((key, b, len(new), cum))
pts.append((tx(now), ty(cum)))
tl = [f'<svg viewBox="0 0 {TW} {TH}" role="img" aria-label="Cumulative refined buildings through the day, one step per delivered batch" xmlns="http://www.w3.org/2000/svg">']
for n in range(0, n_max + 1, 10):
    tl.append(f'<line x1="{PL}" y1="{ty(n):.1f}" x2="{TW-PR}" y2="{ty(n):.1f}" stroke="var(--grid)" stroke-width="1"/><text x="{PL-8}" y="{ty(n)+4:.1f}" font-size="11" text-anchor="end" fill="var(--text-2)" font-family="IBM Plex Mono, monospace">{n}</text>')
t = t_start
while t <= t_end:
    tl.append(f'<text x="{tx(t):.1f}" y="{TH-PB+18}" font-size="11" text-anchor="middle" fill="var(--text-2)" font-family="IBM Plex Mono, monospace">{t.strftime("%H:%M")}</text>')
    t += dt.timedelta(hours=2)
tl.append(f'<line x1="{PL}" y1="{ty(n_max):.1f}" x2="{TW-PR}" y2="{ty(n_max):.1f}" stroke="var(--text-2)" stroke-dasharray="4 3" stroke-width="1"/><text x="{TW-PR}" y="{ty(n_max)-6:.1f}" font-size="11" text-anchor="end" fill="var(--text-2)" font-family="IBM Plex Sans, sans-serif">curated inventory · {n_max}</text>')
tl.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + '" fill="none" stroke="var(--series)" stroke-width="2" stroke-linejoin="round"/>')
for key, b, new, cumv in events:
    x, y = tx(b['delivered']), ty(cumv)
    tl.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--series)" stroke="var(--surface)" stroke-width="2"><title>{b["label"]} · {b["delivered"].strftime("%H:%M")} · +{new} → {cumv}</title></circle>')
tl.append(f'<line x1="{tx(now):.1f}" y1="{PT}" x2="{tx(now):.1f}" y2="{TH-PB}" stroke="var(--prog)" stroke-dasharray="2 3"/><text x="{tx(now)+4:.1f}" y="{PT+12}" font-size="11" fill="var(--prog)" font-family="IBM Plex Mono, monospace">now</text>')
tl.append('</svg>')
timeline_svg = '\n'.join(tl)

# ------------------------------------------------------------------ tables
def fmt_ev(e):
    parts = []
    if e['photos']: parts.append(f'{e["photos"]} photo{"s" if e["photos"] > 1 else ""}')
    if e['texts']: parts.append(f'{e["texts"]} listing/text')
    return ' · '.join(parts) if parts else 'no source record'

batch_rows = []
for key, b in batches.items():
    if key == 'pilot' or key.startswith('revision'): continue
    feats = b['features']
    names = ', '.join(f['name'] + (' (rev.)' if f['revised'] else '') for f in feats)
    area = sum(f['area'] or 0 for f in feats); hts = [f['height'] for f in feats if f['height']]
    ev = sum(f['evidence']['photos'] for f in feats), sum(f['evidence']['texts'] for f in feats)
    state = b['delivered'].strftime('%H:%M') if b['delivered'] else '<span class="prog-pill">in progress</span>'
    batch_rows.append(f'<tr><td>{b["label"]}</td><td class="num">{state}</td><td class="num">{len(feats)}</td><td>{names}</td><td class="num">{area:,.0f}</td><td class="num">{(sum(hts)/len(hts)) if hts else 0:.1f}</td><td class="num">{ev[0]} / {ev[1]}</td></tr>')

cards = []
for key, b in batches.items():
    for f in b['features']:
        r = buildings[f['id']]
        if r['batch'] != key: continue
        img = f'<img src="{r["thumb"]}" alt="Front render of {r["name"]}" loading="lazy">' if r.get('thumb') else '<div class="noimg">no render yet</div>'
        badges = ''.join(f'<span class="badge">{t}</span>' for t in r['flags']) + (f'<span class="badge">revised in {", ".join(batches[k]["label"] for k in r["revisions"])}</span>' if r['revisions'] else '')
        meta = f'{r["levels"]} lv · {r["height"]:.1f} m' + (f' · {r["area"]:,.0f} m²' if r.get('area') else '')
        when = b['delivered'].strftime('%H:%M') if b['delivered'] else 'in progress'
        cards.append(f'<figure class="card{" prog" if r["state"] == "in_progress" else ""}">{img}<figcaption><span class="tag">{b["label"]} · {when}</span><b>{r["name"]}</b><span class="meta">{meta}</span><span class="meta">{fmt_ev(r["evidence"])}</span>{badges}</figcaption></figure>')
gallery = ['<div class="cards">' + ''.join(cards) + '</div>']

pending_rows = ''.join(f'<tr><td>{r["name"]}</td><td><code>{r["id"]}</code></td><td>{r["status"].replace("_", " ")}</td><td>{r["reason"]}</td></tr>' for r in pending_recs)
prog_rows = ''.join(f'<tr><td>{r["name"]}</td><td><code>{r["id"]}</code></td><td>{batches[r["batch"]]["label"]}</td><td>manifest written, no export yet</td></tr>' for r in in_progress)

# ------------------------------------------------------------------ html
html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Refinement Frontier</title>
<meta name="description" content="Progress of the building-by-building geometry refinement around the Imperial College campus: map, timeline, batches, evidence and renders.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--paper:#f3f4f1;--surface:#ffffff;--text-1:#171c22;--text-2:#5c6570;--rule:#d3d8d2;--rule-soft:#e6e9e4;--code-bg:#eceee9;
  --series:#2f62a8;--prog:#d95926;--map-bg:#ffffff;--base-fill:#e4e7e2;--base-stroke:#d0d5cf;--grid:#e6e9e4;--accent:#2b63b0;
  --display:"Barlow Condensed","Arial Narrow",sans-serif;--body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--paper:#0f1419;--surface:#161c23;--text-1:#e4e8ea;--text-2:#9aa4ae;--rule:#2b333c;--rule-soft:#222a32;--code-bg:#1b222a;
  --series:#4a8fe0;--prog:#ec9556;--map-bg:#161c23;--base-fill:#232a31;--base-stroke:#2f3841;--grid:#222a32;--accent:#6e9fe0}}}}
:root[data-theme="dark"]{{--paper:#0f1419;--surface:#161c23;--text-1:#e4e8ea;--text-2:#9aa4ae;--rule:#2b333c;--rule-soft:#222a32;--code-bg:#1b222a;
  --series:#4a8fe0;--prog:#ec9556;--map-bg:#161c23;--base-fill:#232a31;--base-stroke:#2f3841;--grid:#222a32;--accent:#6e9fe0}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--text-1);font-family:var(--body);font-size:15px;line-height:1.5}}
a{{color:var(--accent)}}
code{{font-family:var(--mono);font-size:.85em;background:var(--code-bg);padding:.1em .3em;border-radius:3px}}
h1,h2,h3{{font-family:var(--display);font-weight:600;line-height:1.05;margin:0;text-wrap:balance}}
h1{{font-size:clamp(40px,6vw,64px)}} h2{{font-size:clamp(26px,3.4vw,36px)}} h3{{font-size:22px;margin-top:22px;display:flex;align-items:baseline;gap:12px}}
h3 .when{{font-family:var(--mono);font-size:12px;color:var(--text-2);letter-spacing:.06em}}
.wrap{{max-width:1180px;margin:0 auto;padding-inline:clamp(16px,4vw,40px);padding-block:40px 60px}}
.eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2)}}
.lede{{max-width:66ch;color:var(--text-2);margin-top:12px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border:1px solid var(--rule);background:var(--surface);margin-top:28px}}
.tiles div{{padding:14px 16px;border-right:1px solid var(--rule-soft)}} .tiles div:last-child{{border-right:0}}
.tiles .n{{font-family:var(--display);font-size:34px;font-weight:600;line-height:1}} .tiles .l{{font-size:12.5px;color:var(--text-2);margin-top:4px}}
.tiles .n.prog{{color:var(--prog)}}
.tiles.small{{grid-template-columns:repeat(4,1fr)}} .tiles.small .n{{font-size:26px}} @media (max-width:600px){{.tiles.small{{grid-template-columns:repeat(2,1fr)}}}}
section{{margin-top:48px}}
.two{{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:28px;align-items:start}}
@media (max-width:900px){{.two{{grid-template-columns:1fr}}}}
figure{{margin:0}}
.mapbox{{border:1px solid var(--rule);background:var(--map-bg)}} .mapbox svg{{display:block;width:100%;height:auto}}
figcaption{{font-size:13px;color:var(--text-2);margin-top:8px;max-width:70ch}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--text-2);margin-top:10px;align-items:center}}
.legend span{{display:inline-flex;align-items:center;gap:6px}}
.sw{{width:14px;height:14px;display:inline-block;border:1px solid var(--rule)}}
.ramp{{width:90px;height:12px;background:linear-gradient(90deg,{','.join(STEPS)});display:inline-block}}
.sw.prog{{background:repeating-linear-gradient(45deg,var(--prog) 0 2px,transparent 2px 5px);border-color:var(--prog)}}
.sw.pend{{border:1.5px dashed var(--text-2);background:transparent}}
.chart{{border:1px solid var(--rule);background:var(--surface);padding:12px 8px 4px}} .chart svg{{display:block;width:100%;height:auto}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums;background:var(--surface)}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--rule-soft);vertical-align:top}}
th{{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);font-weight:500}}
td.num,th.num{{text-align:right;white-space:nowrap}}
.tscroll{{overflow-x:auto;border:1px solid var(--rule)}}
.prog-pill{{color:var(--prog);font-family:var(--mono);font-size:12px}}
.gates{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}}
.gate{{border:1px solid var(--rule);background:var(--surface);padding:10px 12px;font-size:13.5px}} .gate b{{display:block;font-family:var(--display);font-size:18px;font-weight:600}}
.gate.no b{{color:var(--text-2)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:10px}}
.card{{background:var(--surface);border:1px solid var(--rule)}} .card img{{display:block;width:100%;aspect-ratio:6/5;object-fit:cover}}
.card.prog{{border-color:var(--prog)}} .noimg{{aspect-ratio:6/5;display:grid;place-items:center;color:var(--text-2);font-size:12px;background:var(--code-bg)}}
.card figcaption{{padding:8px 10px 10px;margin:0;font-size:12.5px;color:var(--text-1)}} .card .tag{{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;color:var(--text-2);margin-bottom:2px}} .card b{{display:block;font-weight:600}} .card .meta{{display:block;color:var(--text-2)}}
.badge{{display:inline-block;font-family:var(--mono);font-size:10.5px;color:var(--text-2);border:1px solid var(--rule);padding:0 5px;border-radius:2px;margin-top:5px;margin-right:4px}}
.note{{border-left:3px solid var(--rule);padding:8px 14px;background:var(--surface);font-size:13.5px;max-width:78ch;color:var(--text-2)}}
footer{{margin-top:48px;font-size:12.5px;color:var(--text-2)}}
</style>
</head>
<body><div class="wrap">
<div class="eyebrow">geometry/expansion · South Kensington core008 · generated {now.strftime('%Y-%m-%d %H:%M')}</div>
<h1>Refinement Frontier</h1>
<p class="lede">Building-by-building refinement of the core008 city model, spreading outward from the Imperial College campus. Each refined building keeps its mapped footprint and entrance, gets a facade built from listings and photographs, and stays reversible in the viewer under <b>Building refinements</b>. Everything below is read from what the refinement task writes to disk.</p>

<div class="tiles">
  <div><div class="n">{len(delivered)}</div><div class="l">buildings delivered</div></div>
  <div><div class="n prog">{len(in_progress)}</div><div class="l">in progress ({batches[in_progress[0]['batch']]['label'] if in_progress else '–'})</div></div>
  <div><div class="n">{len(pending_recs)}</div><div class="l">pending in the frontier</div></div>
  <div><div class="n">{n_batches}</div><div class="l">batches delivered, plus pilot and 1 revision</div></div>
  <div><div class="n">{hours:.1f} h</div><div class="l">batch run {first.strftime('%H:%M')} → {last.strftime('%H:%M')} today, {n_run/hours:.1f} buildings per hour (pilot the evening before)</div></div>
  <div><div class="n">{area_total/1000:.1f} k</div><div class="l">m² of footprint refined</div></div>
</div>

<section class="two">
  <figure>
    <div class="mapbox">{map_svg}</div>
    <div class="legend"><span><i class="ramp"></i> delivered, first → latest</span><span><i class="sw prog"></i> in progress</span><span><i class="sw pend"></i> pending</span><span><i class="sw" style="background:var(--base-fill)"></i> other OSM footprints</span></div>
    <figcaption>Model metres, X east and Y north. Hover a building for its name and batch. {'Projection check: ' + check[0] + ' footprint centre matches OSM within ' + format(check[1], '.1f') + ' m.' if check else ''}</figcaption>
  </figure>
  <div>
    <h2>Where the frontier is</h2>
    <p style="max-width:52ch">The task works ring by ring from the campus: Kensington Gore and Jay Mews first, then Queen's Gate, Princes Gate and its mews, Princes Gardens, and Queen's Gate Place Mews. The map's colour order is delivery order, so the darkest buildings are the most recent.</p>
    <figure class="chart" style="margin-top:18px">{timeline_svg}<figcaption>Cumulative buildings delivered through the day. Each dot is a batch; hover for its size.</figcaption></figure>
    <div class="tiles small" style="margin-top:18px">
      <div><div class="n">{f'{tok_per/1000:.0f} k' if tok_per else '–'}</div><div class="l">tokens per building (cumulative goal usage at {cp['checkpoint'] if cp else '–'})</div></div>
      <div><div class="n">{f'{min_per:.1f}' if min_per else '–'}</div><div class="l">minutes per building, wall clock</div></div>
      <div><div class="n">{ev_photos}</div><div class="l">of {len(delivered)} with an inspected photograph</div></div>
      <div><div class="n">{ev_texts}</div><div class="l">with a listing or text description</div></div>
    </div>
  </div>
</section>

<section>
  <h2>What every delivered batch has and has not passed</h2>
  <div class="gates">
    <div class="gate"><b>✓ numerical checks</b>export reimport, triangle counts, entrance rays, shared walls</div>
    <div class="gate"><b>✓ render review</b>front, entrance, roof, rear and context renders inspected</div>
    <div class="gate no"><b>✗ live browser review</b>no full-scene visual sign-off in the running viewer</div>
    <div class="gate no"><b>✗ geographic accuracy</b>heights and facades are estimates; nothing is certified against survey</div>
  </div>
  <p class="note" style="margin-top:14px">The same four flags hold for all {n_batches} batches in <code>progress.json</code>, so they are shown once. Physics fields are not recomputed for refined geometry; the viewer's physics still describe the original model.</p>
</section>

<section>
  <h2>Batches</h2>
  <div class="tscroll" style="margin-top:14px"><table>
    <thead><tr><th>Batch</th><th class="num">Delivered</th><th class="num">Buildings</th><th>Names</th><th class="num">Footprint m²</th><th class="num">Mean height m</th><th class="num">Photos / texts</th></tr></thead>
    <tbody>{''.join(batch_rows)}</tbody>
  </table></div>
</section>

<section>
  <h2>In progress and pending</h2>
  <div class="tscroll" style="margin-top:14px"><table>
    <thead><tr><th>Building</th><th>OSM id</th><th>State</th><th>Note</th></tr></thead>
    <tbody>{prog_rows}{pending_rows}</tbody>
  </table></div>
</section>

<section>
  <h2>Delivered buildings</h2>
  <p class="lede" style="margin-top:6px">Front renders from the reopened Blender masters, in delivery order. Badges mark names the task could not verify and buildings revised in a later batch.</p>
  {''.join(gallery)}
</section>

<footer>Sources: <code>geometry/expansion/batch*/manifest.json</code>, <code>progress.json</code>, <code>remaining_frontier.json</code>, <code>references/*/sources.json</code>, <code>reports/goal_usage_checkpoints.json</code>, output renders; base map from <code>geometry/completion/sources/osm_buildings.json</code> (© OpenStreetMap contributors, ODbL). Rebuild with <code>python3 docs/tools/build_refinement_progress.py</code>.</footer>
</div></body>
</html>
'''
with open(OUT_HTML, 'w') as f:
    f.write(html)
print(f'wrote {OUT_HTML}: {len(delivered)} delivered, {len(in_progress)} in progress, {len(pending_recs)} pending, {len(base)} base footprints, check={check}')
