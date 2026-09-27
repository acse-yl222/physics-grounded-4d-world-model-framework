"""One-time, recorded local source migration. Refuses to overwrite destinations."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MOVES = [
    ('pipelines/geometry/.git', '.history/repositories/geometry/original.git'),
    ('pipelines/physics/environment-integration/.git', '.history/repositories/environment/original.git'),
    ('pipelines/geometry/traffic', 'src/traffic'),
    ('pipelines/geometry', 'src/urban_geometry'),
    ('pipelines/physics', 'src/urban_flow/physics'),
    ('pipelines', 'src/common/pipeline'),
    ('expansion/src', 'src/urban_geometry/agent'),
    ('expansion', 'project/south_ken/geometry/authoring'),
]
for name in ('actuator_lab','windfarm_2m','windfarm_crop','windfarm_neural'):
    MOVES.append((f'input/{name}',f'src/urban_flow/scenarios/{name}'))


def mapped(path):
    path = Path(path)
    for old, new in sorted(MOVES, key=lambda p: -len(p[0])):
        source = ROOT/old
        if path == source or path.is_relative_to(source):
            return ROOT/new/path.relative_to(source)
    return path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def main():
    ledger=ROOT/'docs/framework/layout-migration.json'
    if ledger.exists():raise SystemExit('Migration already recorded; inspect the ledger instead of rerunning.')
    records=[]
    for old,new in MOVES:
        source,target=ROOT/old,ROOT/new
        if not source.is_dir():raise SystemExit(f'Missing source: {old}')
        if target.exists():raise SystemExit(f'Destination exists: {new}')
        entries=[]
        # Nested repositories have their own verified bundles; record their directory move.
        if source.name != '.git':
            for p in sorted(source.rglob('*')):
                if p.is_file() and not p.is_symlink() and '.git' not in p.parts:
                    entries.append({'old':str(p.relative_to(ROOT)), 'new':str((target/p.relative_to(source)).relative_to(ROOT)), 'bytes':p.stat().st_size,'before':sha(p)})
        target.parent.mkdir(parents=True,exist_ok=True)
        source.rename(target)
        records.extend(entries)
        ledger.write_text(json.dumps({'moves':MOVES,'files':records,'state':'moving'},indent=2)+'\n')
    # Original source path is retained per file for relative-root repair.
    source_records={r['new']:r for r in records if r['new'].endswith('.py')}
    replacements=[('pipelines.geometry.traffic','traffic'),('pipelines.geometry','urban_geometry'),('pipelines.physics','urban_flow.physics'),('pipelines.paths','common.pipeline.paths'),('pipelines.','common.pipeline.'),
                  ('pipelines/geometry/traffic/','src/traffic/'),('pipelines/geometry/','src/urban_geometry/'),('pipelines/physics/','src/urban_flow/physics/'),('pipelines/','src/common/pipeline/')]
    for rel,record in source_records.items():
        path=ROOT/rel
        if not path.is_file():continue
        text=path.read_text();old_path=ROOT/record['old'];needs_root=False
        pattern=r'Path\(__file__\)\.resolve\(\)\.(?:parents\[(\d+)\]|(parent))'
        def ancestor(match):
            nonlocal needs_root
            index=int(match[1]) if match[1] else 0
            original=old_path.parents[index]
            destination=mapped(original)
            if destination == path.parents[index]:return match[0]
            if not destination.is_relative_to(ROOT):return match[0]
            needs_root=True
            suffix=destination.relative_to(ROOT)
            return 'repo_root()' if str(suffix)=='.' else f'(repo_root() / {str(suffix)!r})'
        text=re.sub(pattern,ancestor,text)
        for old,new in replacements:text=text.replace(old,new)
        if needs_root:
            # Insert after module docstring and __future__ imports using AST line locations.
            import ast
            tree=ast.parse(text)
            start=0
            for node in tree.body:
                if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str) and start==0:start=node.end_lineno
                elif isinstance(node,ast.ImportFrom) and node.module=='__future__':start=node.end_lineno
                else:break
            lines=text.splitlines(keepends=True)
            bootstrap="from pathlib import Path as _UwmPath\nimport sys as _uwm_sys\n_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))\nfrom common.layout import repo_root\n"
            lines.insert(start,bootstrap);text=''.join(lines)
        path.write_text(text)
    for record in records:
        path=ROOT/record['new']
        # Parent source moves can include already-moved files only once by construction.
        record['after']=sha(path)
    ledger.write_text(json.dumps({'moves':MOVES,'files':records,'state':'source-moved; callers under verification'},indent=2)+'\n')
    print(f'Moved {len(MOVES)} directories; recorded {len(records)} files.')

if __name__=='__main__':main()
