"""Check the files that are NOT in the repository (city model + full-hour replay) once placed, then every repository file against FILES.json."""
import hashlib, json, os, sys
LARGE = {
 "assets/city.glb": [
  "b50716ff233ee6bd929dc23ac7e10360495fd484d5c32ee5180a6f54933034bd",
  254723368
 ],
 "data/traffic/replay/traffic_flow.f32": [
  "4c62cac605b7eb307fea9527a133f1d7a2b5ee576b8dd0a885a78355e06f6b82",
  105780340
 ],
 "data/traffic/replay/tls_frames.jsonl": [
  "31e2deda347349f4056d6557f0eede1612fb5c49c26cba8246315c1eeed4009f",
  85300893
 ],
 "data/traffic/replay/frames_index.json": [
  "2d8031fcb0132a639e39284cfeaf0988eb7910433890ade6b8277bd936bae661",
  200311
 ]
}
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()
bad = 0
for rel, (digest, size) in LARGE.items():
    if not os.path.isfile(rel):
        print('MISSING:', rel); bad += 1; continue
    if os.path.getsize(rel) != size or sha(rel) != digest:
        print('NOT THE FULL-HOUR FILE (sample or damaged):' if 'replay' in rel else 'MISMATCH:', rel); bad += 1
files = json.load(open('FILES.json'))['files']
for rel, rec in files.items():
    if rel in LARGE or rel in ('finish_on_mac.sh', 'README.md'):
        continue
    if not os.path.isfile(rel):
        print('MISSING:', rel); bad += 1
    elif os.path.getsize(rel) != rec['bytes'] or sha(rel) != rec['sha256']:
        print('MISMATCH:', rel); bad += 1
print('OK: full package verified' if bad == 0 else f'{bad} problems (see above)')
sys.exit(1 if bad else 0)
