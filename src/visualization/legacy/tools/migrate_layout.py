#!/usr/bin/env python3
"""One-off restructuring of the repository from task-named folders to content-named folders (2026-09-14).

    python3 tools/migrate_layout.py            # apply (idempotent: skips moves already done)
    python3 tools/migrate_layout.py --dry-run  # only report

Moves (all plain renames, logged to tools/migration_log.json):
    south_kensington_*.glb                      -> models/
    building_completion/                        -> geometry/completion/   (its output/buildings_supplement.glb -> models/)
    geometry_expansion/                         -> geometry/expansion/
    physics_assert/                             -> physics/
    demo_rev02/                                 -> agents/demo_rev02/     (its vendor/ -> vendor/, symlink left behind)
    web/                                        -> viewer/                (its vendor/jsm/lines -> vendor/three/examples/jsm/lines)
    docs/assets/                                -> docs/media/
Then every text file (code, html, css, json, md, sh) gets the old path tokens rewritten, and the demo package's relative
three.js imports become bare 'three' / 'three/addons/' specifiers so both pages share one copy through their import maps.
This script never rewrites itself (tools/ is skipped), so it can be copied to a mirror and run there.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DRY = '--dry-run' in sys.argv
log = {'moves': [], 'symlinks': [], 'edited': {}, 'skipped': []}


def p(*a): return os.path.join(ROOT, *a)


def move(src, dst):
    s, d = p(src), p(dst)
    if not os.path.lexists(s):
        log['skipped'].append(f'{src} (missing)'); return
    if os.path.lexists(d):
        log['skipped'].append(f'{src} -> {dst} (target exists)'); return
    print('move', src, '->', dst)
    if not DRY:
        os.makedirs(os.path.dirname(d), exist_ok=True); os.rename(s, d)
    log['moves'].append([src, dst])


def symlink(link, target):
    l = p(link)
    if os.path.lexists(l):
        log['skipped'].append(f'symlink {link} (exists)'); return
    print('symlink', link, '->', target)
    if not DRY:
        os.makedirs(os.path.dirname(l), exist_ok=True); os.symlink(target, l)
    log['symlinks'].append([link, target])


# ------------------------------------------------------------------ 1. moves
for f in ('south_kensington_core008_web.glb', 'south_kensington_current.glb', 'south_kensington_paused_20260910.glb'):
    move(f, 'models/' + f)
move('building_completion', 'geometry/completion')
move('geometry/completion/output/buildings_supplement.glb', 'models/buildings_supplement.glb')
move('geometry_expansion', 'geometry/expansion')
move('physics_assert', 'physics')
move('demo_rev02', 'agents/demo_rev02')
move('agents/demo_rev02/vendor', 'vendor')
symlink('agents/demo_rev02/vendor', '../../vendor')
move('web', 'viewer')
if os.path.isdir(p('viewer/vendor/jsm/lines')) and not os.path.isdir(p('vendor/three/examples/jsm/lines')):
    move('viewer/vendor/jsm/lines', 'vendor/three/examples/jsm/lines')
    if not DRY and os.path.isdir(p('viewer/vendor')):
        for d, _, _ in list(os.walk(p('viewer/vendor'), topdown=False)):
            try: os.rmdir(d)
            except OSError: pass
move('docs/assets', 'docs/media')
# the demo package's symlink to the city model
city = p('agents/demo_rev02/assets/city.glb')
if os.path.islink(city) and not DRY and os.readlink(city) != '../../../models/south_kensington_core008_web.glb':
    os.unlink(city); os.symlink('../../../models/south_kensington_core008_web.glb', city); log['symlinks'].append(['agents/demo_rev02/assets/city.glb', '../../../models/south_kensington_core008_web.glb'])

# ------------------------------------------------------------------ 2. text rewrites
RULES = [
    # explicit code paths first
    ("'../../south_kensington_core008_web.glb'", "'../../models/south_kensington_core008_web.glb'"),
    ("'../../south_kensington_current.glb'", "'../../models/south_kensington_current.glb'"),
    ("'../../building_completion/output/buildings_supplement.glb'", "'../../models/buildings_supplement.glb'"),
    ("'building_completion', 'output', 'buildings_supplement.glb'", "'models', 'buildings_supplement.glb'"),
    ("path.join(ROOT, 'south_kensington_core008_web.glb')", "path.join(ROOT, 'models', 'south_kensington_core008_web.glb')"),
    ("'../../demo_rev02/vendor/three/build/three.module.js'", "'../../vendor/three/build/three.module.js'"),
    ('"../../demo_rev02/vendor/three/build/three.module.js"', '"../../vendor/three/build/three.module.js"'),
    ('"../../demo_rev02/vendor/three/examples/jsm/"', '"../../vendor/three/examples/jsm/"'),
    ('"../vendor/jsm/lines/"', '"../../vendor/three/examples/jsm/lines/"'),
    ("pathResolve('demo_rev02/vendor/three/build/three.module.js')", "pathResolve('vendor/three/build/three.module.js')"),
    ("pathResolve('demo_rev02/vendor/three/examples/jsm',", "pathResolve('vendor/three/examples/jsm',"),
    # folder tokens
    ('geometry_expansion/', 'geometry/expansion/'),
    ('building_completion/', 'geometry/completion/'),
    ('physics_assert/', 'physics/'),
    (re.compile(r'(?<!agents/)(?<![\w-])demo_rev02/'), 'agents/demo_rev02/'),
    ('web/3d', 'viewer/3d'),
    ('web/npy.js', 'viewer/npy.js'),
    ('web/index.html', 'viewer/index.html'),
    ('web/vendor/jsm/lines', 'vendor/three/examples/jsm/lines'),
    ('`web/`', '`viewer/`'),
    ('docs/assets', 'docs/media'),
    ("`physics_assert`", "`physics`"),
]
DOCS_RULES = [('src="assets/', 'src="media/'), ("'assets/refined/'", "'media/refined/'"), ("'docs', 'assets', 'refined'", "'docs', 'media', 'refined'")]
DEMO_IMPORT_RULES = [
    (re.compile(r"from\s+'(\./|\.\./)vendor/three/build/three\.module\.js'"), "from 'three'"),
    (re.compile(r"from\s+'(\./|\.\./)vendor/three/examples/jsm/([^']+)'"), r"from 'three/addons/\2'"),
    (re.compile(r"import\s*\(\s*'(\./|\.\./)vendor/three/examples/jsm/([^']+)'\s*\)"), r"import('three/addons/\2')"),
]
TEXT_EXT = {'.py', '.mjs', '.js', '.html', '.css', '.md', '.json', '.sh', '.command', '.txt'}
SKIP_DIRS = {'vendor', '.deps', 'node_modules', '__pycache__', '.git', 'tools'}


def rewrite(path, rules):
    try:
        with open(path, encoding='utf-8') as f: s = f.read()
    except (UnicodeDecodeError, OSError):
        return 0
    t = s
    for old, new in rules:
        t = old.sub(new, t) if hasattr(old, 'sub') else t.replace(old, new)
    if t != s:
        if not DRY:
            with open(path, 'w', encoding='utf-8') as f: f.write(t)
        return 1
    return 0


for dirpath, dirnames, filenames in os.walk(ROOT):
    rel = os.path.relpath(dirpath, ROOT)
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('chrome-')]
    if rel == '.': dirnames[:] = [d for d in dirnames if d != 'tools']
    for fn in filenames:
        if os.path.splitext(fn)[1] not in TEXT_EXT: continue
        path = os.path.join(dirpath, fn)
        if os.path.islink(path): continue
        rules = list(RULES)
        if rel.startswith('docs'): rules += DOCS_RULES
        if rel.startswith('agents/demo_rev02') and fn.endswith('.js'): rules += DEMO_IMPORT_RULES
        if rewrite(path, rules): log['edited'][os.path.relpath(path, ROOT)] = True
# the demo's own import map keeps './vendor/...' (symlink) so its standalone page still runs

if not DRY:
    os.makedirs(p('tools'), exist_ok=True)
    with open(p('tools', 'migration_log.json'), 'w') as f: json.dump(log, f, indent=1)
print(f"{'DRY RUN: ' if DRY else ''}{len(log['moves'])} moves, {len(log['symlinks'])} symlinks, {len(log['edited'])} files edited, {len(log['skipped'])} skipped")
for s in log['skipped']: print('  skipped:', s)
